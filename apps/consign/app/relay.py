"""Outbox → Redis Stream(기본) 또는 RabbitMQ exchange(BROKER=rabbitmq) 중계.

Pod 가 여러 개면 relay 도 여러 개 돈다. FOR UPDATE SKIP LOCKED 로 서로 다른 행을 집게 해서
같은 행을 동시에 보내지 않는다. 그래도 XADD 성공 뒤 커밋 전에 Pod 가 죽으면 같은 이벤트가 다시 나간다
→ 보장은 at-least-once 이고, 중복은 소비자(settlement)가 멱등 처리로 흡수한다.
"""

import asyncio
import json
import logging
import time

import aio_pika
from redis.asyncio import Redis
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Outbox
from app.trace import trace

logging.basicConfig(level=logging.INFO)  # 로그는 stdout 으로 — k8s 가 수집한다
log = logging.getLogger("relay")
STREAM = "sales"
EXCHANGE = "sales"  # RabbitMQ 일 때. topic exchange, routing key = outbox topic(sale.completed)


async def connect_exchange(rabbitmq_url: str):
    """RabbitMQ 의 판매 이벤트 exchange. 소비자 쪽 큐 선언은 settlement 가 한다(누가 받는지는 소비자 몫)."""
    # connect_robust 는 붙은 뒤 끊긴 연결만 복구한다. 첫 연결 실패는 직접 재시도해야 한다(앱이 브로커보다 먼저 뜰 때)
    while True:
        try:
            connection = await aio_pika.connect_robust(rabbitmq_url)
            break
        except Exception:
            log.exception("RabbitMQ 연결 실패, 재시도")
            await asyncio.sleep(1)
    # aio-pika 채널은 publisher confirm 이 기본으로 켜져 있다 → publish 는 브로커가 받았다고 답할 때까지 기다린다
    channel = await connection.channel()
    exchange = await channel.declare_exchange(EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
    return connection, exchange


async def publish_batch(redis: Redis, limit: int = 100, exchange=None) -> int:
    async with SessionLocal() as session, session.begin():
        rows = (
            await session.scalars(
                select(Outbox)
                .where(Outbox.published_at.is_(None))
                .order_by(Outbox.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for row in rows:
            if exchange is None:
                await redis.xadd(STREAM, {"topic": row.topic, "payload": json.dumps(row.payload)})
            else:
                # PERSISTENT + durable 큐여야 브로커 재시작 뒤에도 남는다. routing key 는 토픽 이름 그대로
                await exchange.publish(
                    aio_pika.Message(json.dumps(row.payload).encode(), message_id=str(row.id),
                                     content_type="application/json",
                                     delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                    routing_key=row.topic,
                )
            row.published_at = func.now()
        return len(rows)


async def run(redis_url: str, rabbitmq_url: str | None = None, interval: float = 1.0) -> None:
    redis = Redis.from_url(redis_url)
    connection, exchange = await connect_exchange(rabbitmq_url) if rabbitmq_url else (None, None)
    target = "exchange sales" if exchange else "sales XADD"
    try:
        while True:
            try:
                t = time.perf_counter()
                n = await publish_batch(redis, exchange=exchange)
                if n == 0:
                    await asyncio.sleep(interval)
                else:
                    await trace(redis, "consign", "relay", f"outbox → {target} ×{n}",
                                n=n, ms=round((time.perf_counter() - t) * 1000))  # ponytail: 폴링. 지연이 문제되면 LISTEN/NOTIFY 나 CDC(Debezium)
            except asyncio.CancelledError:
                raise
            except Exception:
                # Redis·DB 가 잠깐 끊겨도 relay 가 죽지 않게. 다음 회차에 다시 집는다
                log.exception("relay 실패, 재시도")
                await asyncio.sleep(interval)
    finally:
        await redis.aclose()
        if connection:
            await connection.close()
