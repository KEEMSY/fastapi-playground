"""BROKER=rabbitmq 경로. docker compose 의 RabbitMQ(localhost:55672)가 필요하다 — make test 가 띄운다."""

import asyncio
import json

import aio_pika
import pytest
from sqlalchemy import func, select

from app import relay
from app.db import Base, SessionLocal, engine, settings
from app.models import Outbox
from settlement import main as settlement

URL = settings.rabbitmq_url


@pytest.fixture
async def clean():
    # 앱 코드는 브로커가 뜰 때까지 끝없이 재시도한다. 테스트는 그러면 멈춰 버리니 먼저 짧게 확인하고 실패시킨다
    try:
        await (await asyncio.wait_for(aio_pika.connect(URL), 5)).close()
    except Exception as e:
        pytest.fail(f"RabbitMQ({URL})에 붙지 못함 — docker compose up -d --wait 먼저: {e!r}")
    for eng, base in ((engine, Base), (settlement.engine, settlement.Base)):
        async with eng.begin() as conn:
            await conn.run_sync(base.metadata.drop_all)
            await conn.run_sync(base.metadata.create_all)
    yield
    await engine.dispose()
    await settlement.engine.dispose()


async def test_relay_publishes_outbox_to_exchange(clean):
    connection, exchange = await relay.connect_exchange(URL)
    async with connection:
        channel = await connection.channel()
        probe = await channel.declare_queue(exclusive=True)  # 테스트용 임시 큐로 exchange 에 나간 것을 받아 본다
        await probe.bind(exchange, routing_key="sale.completed")
        async with SessionLocal() as s, s.begin():
            s.add(Outbox(topic="sale.completed", payload={"sale_id": 1, "seller_id": 1, "settlement_amount": 700}))

        assert await relay.publish_batch(None, exchange=exchange) == 1
        message = await probe.get(timeout=5)
        await message.ack()
        assert json.loads(message.body)["sale_id"] == 1
        async with SessionLocal() as s:  # 발행했으면 다시 집지 않는다
            assert await s.scalar(select(func.count()).where(Outbox.published_at.is_(None))) == 0


async def test_duplicate_message_settles_once(clean):
    connection = await aio_pika.connect_robust(URL)
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(settlement.QUEUE, durable=True)
        await queue.purge()
        consumer = asyncio.create_task(settlement.consume_rabbitmq(None, URL, prefetch=10))
        try:
            exchange = await channel.declare_exchange(settlement.EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
            await asyncio.sleep(0.5)  # 소비자가 큐를 bind 할 때까지
            body = json.dumps({"sale_id": 42, "seller_id": 7, "settlement_amount": 70_000}).encode()
            for _ in range(2):  # relay 는 at-least-once — 같은 이벤트가 두 번 올 수 있다
                await exchange.publish(aio_pika.Message(body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                                       routing_key="sale.completed")
            for _ in range(50):  # 두 메시지 모두 ack 되어 큐가 빌 때까지
                await asyncio.sleep(0.1)
                declared = await channel.declare_queue(settlement.QUEUE, durable=True, passive=True)
                if declared.declaration_result.message_count == 0:
                    break
            await asyncio.sleep(0.3)
        finally:
            consumer.cancel()
            await asyncio.gather(consumer, return_exceptions=True)

    async with settlement.SessionLocal() as s:
        rows = (await s.execute(select(func.count(), func.sum(settlement.Ledger.settlement_amount)))).one()
    assert tuple(rows) == (1, 70_000)
