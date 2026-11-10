"""정산 서비스. 판매 서비스의 DB 를 직접 읽지 않고, 이벤트로만 판매를 안다(서비스별 DB).

Redis Stream 소비자 그룹으로 받는다. 같은 그룹의 Pod 여러 개가 메시지를 나눠 받고,
처리 뒤 XACK 하지 않은 메시지는 pending 에 남아 다시 처리할 수 있다.
BROKER=rabbitmq 면 durable 큐 하나를 Pod 들이 나눠 받는다(competing consumers). ack 안 한 메시지는
채널이 끊기면 다른 소비자에게 다시 간다 — Redis 의 pending 회수를 브로커가 대신 해 준다.
"""

import asyncio
import json
import logging
import socket
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

import aio_pika
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from redis.asyncio import Redis
from redis.exceptions import ResponseError
from sqlalchemy import DateTime, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

logging.basicConfig(level=logging.INFO)  # 로그는 stdout 으로 — k8s 가 수집한다
log = logging.getLogger("settlement")
STREAM, GROUP = "sales", "settlement"
EXCHANGE, QUEUE = "sales", "settlement.sales"  # RabbitMQ 일 때. exchange 이름은 consign 의 relay 와 같아야 한다
TRACE = "trace"  # consign 의 app/trace.py 와 같은 스트림. 서비스 경계라 코드를 가져오지 않고 같은 형식으로 쓴다
HOST = socket.gethostname()


async def trace(redis, kind: str, what: str, **extra) -> None:
    try:
        await redis.xadd(TRACE, {"svc": "settlement", "pod": HOST, "kind": kind, "what": what,
                                 **{k: str(v) for k, v in extra.items()}}, maxlen=2000, approximate=True)
    except Exception:
        pass  # 기록 실패가 소비를 깨면 안 된다


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://consign:consign@localhost:55432/settlement"
    redis_url: str = "redis://localhost:56379"
    broker: str = "redis"  # redis | rabbitmq. trace 는 어느 쪽이든 Redis
    rabbitmq_url: str = "amqp://guest:guest@localhost:55672/"
    prefetch: int = 10  # ack 안 한 채로 이 소비자가 쥐고 있을 수 있는 최대 메시지 수


settings = Settings()
engine = create_async_engine(settings.database_url)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Ledger(Base):
    """정산 원장. sale_id 가 PK 라서 같은 이벤트가 두 번 와도 한 줄만 남는다 — 멱등성의 근거."""

    __tablename__ = "ledger"

    sale_id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(index=True)
    settlement_amount: Mapped[int]
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


async def handle(payload: dict) -> bool:
    """원장에 기록. 이미 있으면 아무것도 안 한다. 새로 기록했으면 True."""
    async with SessionLocal() as session, session.begin():
        result = await session.execute(
            insert(Ledger)
            .values(sale_id=payload["sale_id"], seller_id=payload["seller_id"],
                    settlement_amount=payload["settlement_amount"])
            .on_conflict_do_nothing(index_elements=["sale_id"])
        )
        return result.rowcount == 1


async def consume(redis: Redis) -> None:
    consumer = socket.gethostname()  # k8s 에서는 Pod 이름
    try:
        await redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except ResponseError:
        pass  # 그룹이 이미 있다 — 다른 Pod 가 먼저 만들었다
    while True:
        try:
            # ">" = 이 그룹에 아직 아무에게도 안 간 새 메시지. 5초 기다려도 없으면 빈 결과
            batches = await redis.xreadgroup(GROUP, consumer, {STREAM: ">"}, count=50, block=5000)
            for _, messages in batches:
                t, new = time.perf_counter(), 0
                for msg_id, fields in messages:
                    created = await handle(json.loads(fields[b"payload"]))
                    new += created
                    log.info("sale %s %s", msg_id, "기록" if created else "중복 무시")
                    # DB 커밋 뒤에 ACK. 순서가 반대면 ACK 뒤 커밋 전에 죽을 때 이벤트를 잃는다
                    await redis.xack(STREAM, GROUP, msg_id)
                await trace(redis, "consume", f"XREADGROUP ×{len(messages)} → 원장 {new} · 중복 {len(messages) - new}",
                            n=len(messages), ms=round((time.perf_counter() - t) * 1000))
            # ponytail: 죽은 Pod 의 pending 메시지 회수(XAUTOCLAIM)는 없다 — 연습 과제로 남김
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("소비 실패, 재시도")
            await asyncio.sleep(1)


async def consume_rabbitmq(redis, rabbitmq_url: str, prefetch: int) -> None:
    # connect_robust 는 붙은 뒤 끊긴 연결만 복구한다. 첫 연결 실패는 직접 재시도해야 한다(앱이 브로커보다 먼저 뜰 때)
    while True:
        try:
            connection = await aio_pika.connect_robust(rabbitmq_url)
            break
        except Exception:
            log.exception("RabbitMQ 연결 실패, 재시도")
            await asyncio.sleep(1)
    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=prefetch)
        exchange = await channel.declare_exchange(EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue(QUEUE, durable=True)
        await queue.bind(exchange, routing_key="sale.completed")
        async with queue.iterator() as messages:
            async for message in messages:
                t = time.perf_counter()
                try:
                    created = await handle(json.loads(message.body))
                except Exception:
                    log.exception("소비 실패 %s, 다시 큐로", message.message_id)
                    await asyncio.sleep(1)
                    # shortcut: 실패하면 1초 뒤 바로 requeue — 깨진 메시지는 끝없이 돈다. 3단계(카탈로그 #18)에서 TTL+DLX 지연 재시도와 DLQ 로 바꾼다
                    await message.nack(requeue=True)
                    continue
                # DB 커밋 뒤에 ack. 순서가 반대면 ack 뒤 커밋 전에 죽을 때 이벤트를 잃는다(Redis 의 XACK 와 같은 이유)
                await message.ack()
                log.info("sale msg %s %s", message.message_id, "기록" if created else "중복 무시")
                await trace(redis, "consume", f"{QUEUE} ack → 원장 {int(created)} · 중복 {int(not created)}",
                            n=1, ms=round((time.perf_counter() - t) * 1000))
    finally:
        await connection.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    redis = app.state.redis = Redis.from_url(settings.redis_url)
    if settings.broker == "rabbitmq":
        task = asyncio.create_task(consume_rabbitmq(redis, settings.rabbitmq_url, settings.prefetch))
    else:
        task = asyncio.create_task(consume(redis))
    yield
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    if settings.broker != "rabbitmq":
        # 소비자는 Pod 가 사라져도 그룹에 이름이 남는다. 맡은 pending 이 없을 때만 지운다 — 있으면 남겨서 회수(XAUTOCLAIM) 대상이 되게
        consumer = socket.gethostname()
        mine = [c for c in await redis.xinfo_consumers(STREAM, GROUP) if c["name"].decode() == consumer]
        if mine and mine[0]["pending"] == 0:
            await redis.xgroup_delconsumer(STREAM, GROUP, consumer)
    await redis.aclose()
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def served_by(request: Request, call_next):
    t = time.perf_counter()
    response = await call_next(request)
    response.headers["x-served-by"] = HOST
    redis = getattr(request.app.state, "redis", None)
    if redis is not None and "x-poll" not in request.headers:
        q = f"?{request.url.query}" if request.url.query else ""
        await trace(redis, "probe" if request.url.path in ("/healthz", "/readyz") else "http",
                    f"{request.method} {request.url.path}{q}", status=response.status_code,
                    ms=round((time.perf_counter() - t) * 1000))
    return response


async def get_session():
    async with SessionLocal() as session:
        yield session


Session = Annotated[AsyncSession, Depends(get_session)]


class SettlementOut(BaseModel):
    seller_id: int
    sold_count: int
    total_settlement: int


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/readyz")
async def readyz(session: Session):
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "db unavailable")
    return {"ok": True}


@app.get("/sellers/{seller_id}/settlement", response_model=SettlementOut)
async def get_settlement(seller_id: int, session: Session):
    count, total = (
        await session.execute(
            select(func.count(), func.coalesce(func.sum(Ledger.settlement_amount), 0))
            .where(Ledger.seller_id == seller_id)
        )
    ).one()
    return SettlementOut(seller_id=seller_id, sold_count=count, total_settlement=total)


@app.get("/ledger")
async def ledger(session: Session, limit: int = 15):
    rows = (await session.scalars(select(Ledger).order_by(Ledger.received_at.desc()).limit(limit))).all()
    return [{"sale_id": r.sale_id, "seller_id": r.seller_id, "amount": r.settlement_amount,
             "received_at": r.received_at} for r in rows]


@app.get("/sellers")
async def sellers(session: Session):
    rows = await session.execute(
        select(Ledger.seller_id, func.count(), func.sum(Ledger.settlement_amount)).group_by(Ledger.seller_id)
    )
    return [{"seller_id": s, "sold_count": c, "total_settlement": t} for s, c, t in rows]
