import asyncio
import socket
import time
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from redis.asyncio import Redis
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import console, relay
from app.trace import http_kind, trace
from app.db import Base, engine, get_session, settings
from app.models import Item, Outbox, Sale


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작: 테이블 생성. ponytail: 1단계라 create_all, 롤링 배포를 다루는 4단계에서 Alembic 으로 바꾼다
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 백그라운드 작업은 lifespan 에서 띄우고 종료 때 취소한다. 띄워 놓고 잊으면 종료 때 고아가 된다
    rabbitmq_url = settings.rabbitmq_url if settings.broker == "rabbitmq" else None
    task = asyncio.create_task(relay.run(settings.redis_url, rabbitmq_url)) if settings.redis_url else None
    # 외부 호출 클라이언트는 프로세스당 하나 만들어 재사용한다(요청마다 만들면 커넥션 재사용이 안 된다)
    app.state.http = httpx.AsyncClient(base_url=settings.settlement_url)
    app.state.redis = Redis.from_url(settings.redis_url) if settings.redis_url else None
    yield
    await app.state.http.aclose()
    if app.state.redis:
        await app.state.redis.aclose()
    # 종료(k8s 에선 SIGTERM 뒤): relay 를 멈추고 풀의 커넥션을 정리한다
    if task:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(console.router)
HOST = socket.gethostname()  # k8s 에선 Pod 이름


@app.middleware("http")
async def served_by(request: Request, call_next):
    # 어느 Pod 가 응답했는지. replica 2개 사이에 요청이 어떻게 나뉘는지 화면에서 보인다
    t = time.perf_counter()
    response = await call_next(request)
    response.headers["x-served-by"] = HOST
    # 콘솔의 1초 갱신(x-poll)만 빼고 모든 요청을 기록한다 — 콘솔·curl·k8s probe 구분 없이
    if "x-poll" not in request.headers:
        q = f"?{request.url.query}" if request.url.query else ""
        await trace(getattr(request.app.state, "redis", None), "consign", http_kind(request.url.path),
                    f"{request.method} {request.url.path}{q}", status=response.status_code,
                    ms=round((time.perf_counter() - t) * 1000))
    return response
Session = Annotated[AsyncSession, Depends(get_session)]


# --- 스키마 (Pydantic v2) ---

class ItemIn(BaseModel):
    seller_id: int
    name: str = Field(min_length=1)
    price: int = Field(gt=0)
    commission_rate: int = Field(ge=0, le=100)


class ItemOut(ItemIn):
    # v1 의 orm_mode=True 자리. ORM 객체에서 바로 model_validate 할 수 있게 한다
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str


class SaleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    item_id: int
    sold_price: int
    settlement_amount: int


class SettlementOut(BaseModel):
    seller_id: int
    sold_count: int
    total_settlement: int


# --- k8s probe ---
# liveness 는 프로세스가 살아 있는지만 본다. 여기서 DB 를 보면 DB 장애 하나로 모든 Pod 가 재시작된다
@app.get("/healthz")
async def healthz():
    return {"ok": True}


# readiness 는 요청을 받아도 되는지. 실패하면 Service 가 이 Pod 로 트래픽을 보내지 않는다(재시작은 안 함)
@app.get("/readyz")
async def readyz(session: Session):
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "db unavailable")
    return {"ok": True}


# --- 엔드포인트 ---
# 전부 async def 다. 안에서 부르는 것이 모두 await 가능한 I/O(asyncpg)라서 이벤트 루프를 막지 않는다.
# 여기에 requests.get 이나 time.sleep 을 넣으면 이 프로세스의 모든 요청이 같이 멈춘다 — 2단계에서 직접 잰다.

@app.post("/items", response_model=ItemOut, status_code=201)
async def register_item(body: ItemIn, session: Session):
    item = Item(**body.model_dump())
    session.add(item)
    await session.commit()
    return item


@app.get("/items/{item_id}", response_model=ItemOut)
async def get_item(item_id: int, session: Session):
    item = await session.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "상품이 없습니다")
    return item


@app.post("/items/{item_id}/sell", response_model=SaleOut, status_code=201)
async def sell_item(item_id: int, session: Session):
    # 조건부 UPDATE 로 판매 가능 상태를 "확인하면서 바꾼다".
    # SELECT 로 status 를 본 뒤 UPDATE 하면, 두 요청이 동시에 ON_SALE 을 보고 둘 다 판매할 수 있다(경쟁 조건).
    # 이 UPDATE 는 행 잠금을 잡으므로 동시에 와도 한 요청만 1행을 바꾸고, 나머지는 0행이 된다.
    result = await session.execute(
        update(Item)
        .where(Item.id == item_id, Item.status == "ON_SALE")
        .values(status="SOLD")
        .returning(Item.seller_id, Item.price, Item.commission_rate)
    )
    row = result.one_or_none()
    if row is None:
        await session.rollback()
        exists = await session.get(Item, item_id)
        raise HTTPException(409 if exists else 404, "이미 팔렸습니다" if exists else "상품이 없습니다")

    seller_id, price, rate = row
    # 수수료의 원 미만은 버린다 → 끝전은 판매자 몫. 반올림 정책은 실제 서비스에선 기획이 정할 일
    sale = Sale(item_id=item_id, sold_price=price, settlement_amount=price - price * rate // 100)
    session.add(sale)
    await session.flush()  # sale.id 를 받기 위해 INSERT 만 먼저 보낸다(커밋은 아직)
    session.add(Outbox(topic="sale.completed", payload={
        "sale_id": sale.id, "item_id": item_id, "seller_id": seller_id,
        "sold_price": price, "settlement_amount": sale.settlement_amount,
    }))
    await session.commit()  # 상태 변경·판매 기록·이벤트가 한 트랜잭션으로 같이 커밋된다
    return sale


@app.get("/sellers/{seller_id}/settlement", response_model=SettlementOut)
async def get_settlement(seller_id: int, session: Session):
    count, total = (
        await session.execute(
            select(func.count(Sale.id), func.coalesce(func.sum(Sale.settlement_amount), 0))
            .join(Item, Item.id == Sale.item_id)
            .where(Item.seller_id == seller_id)
        )
    ).one()
    return SettlementOut(seller_id=seller_id, sold_count=count, total_settlement=total)
