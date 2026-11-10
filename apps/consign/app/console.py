"""관찰용 콘솔. 브라우저는 consign 하나에만 붙고, 나머지는 consign 이 대신 모아 준다.

- Outbox: consign 자기 DB
- Redis Stream: XINFO 로 길이·소비자 그룹·소비자(=settlement Pod)별 pending
- 정산: settlement 서비스를 HTTP 로 호출 — 상대 DB 를 직접 읽지 않는다(서비스 경계)
"""

import asyncio
import socket
import time
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from sqlalchemy import func, insert, make_url, select, text

from app.db import SessionLocal, engine, settings
from app.models import Item, Outbox, Sale
from app.relay import STREAM
from app.trace import TRACE

router = APIRouter()
INDEX = Path(__file__).parent / "static" / "index.html"


@router.get("/", include_in_schema=False)
async def index():
    return FileResponse(INDEX)


@router.get("/ops/topology")
async def topology():
    # 구성도에 그릴 실제 접속 대상. 비밀번호가 섞이지 않게 호스트·포트만 꺼낸다
    db = make_url(settings.database_url)
    rd = urlparse(settings.redis_url) if settings.redis_url else None
    return {
        "pod": socket.gethostname(),
        "database": f"{db.host}:{db.port}/{db.database}",
        "redis": f"{rd.hostname}:{rd.port}" if rd else None,
        "settlement": settings.settlement_url,
    }


@router.get("/ops/trace")
async def trace_feed(request: Request, after: str = ""):
    """after 이후 기록. 처음(after 없음)엔 최근 100건."""
    redis = request.app.state.redis
    if redis is None:
        return []
    rows = (await redis.xrange(TRACE, f"({after}", "+", count=500) if after
            else (await redis.xrevrange(TRACE, count=100))[::-1])
    return [{"id": i.decode(), "at": int(i.split(b"-")[0]), **{k.decode(): v.decode() for k, v in f.items()}}
            for i, f in rows]


@router.get("/ops/items")
async def items(limit: int = 30):
    async with SessionLocal() as s:
        rows = (await s.scalars(select(Item).order_by(Item.id.desc()).limit(limit))).all()
    return [{"id": i.id, "seller_id": i.seller_id, "name": i.name, "price": i.price,
             "commission_rate": i.commission_rate, "status": i.status} for i in rows]


@router.get("/ops/outbox")
async def outbox(limit: int = 15):
    async with SessionLocal() as s:
        rows = (await s.scalars(select(Outbox).order_by(Outbox.id.desc()).limit(limit))).all()
    return [{"id": o.id, "sale_id": o.payload["sale_id"], "item_id": o.payload["item_id"], "seller_id": o.payload["seller_id"],
             "amount": o.payload["settlement_amount"], "created_at": o.created_at,
             "published_at": o.published_at} for o in rows]


@router.get("/ops/stream")
async def stream(request: Request):
    redis = request.app.state.redis
    if redis is None:
        return {"enabled": False}
    if not await redis.exists(STREAM):
        return {"enabled": True, "length": 0, "groups": []}
    groups = []
    for g in await redis.xinfo_groups(STREAM):
        name = g["name"].decode()
        consumers = await redis.xinfo_consumers(STREAM, name)
        groups.append({
            "name": name, "pending": g["pending"], "lag": g.get("lag"),
            "last_delivered": g["last-delivered-id"].decode(),
            "consumers": [{"name": c["name"].decode(), "pending": c["pending"], "idle_ms": c["idle"]}
                          for c in consumers],
        })
    return {"enabled": True, "length": await redis.xlen(STREAM), "groups": groups}


@router.get("/ops/settlement/{path:path}")
async def settlement_proxy(path: str, request: Request):
    # 서비스 간 동기 호출. k8s 에선 http://settlement:8000 — Service 이름이 DNS 다.
    # 상대가 죽어도 화면 전체가 멈추지 않게 짧은 타임아웃 + 실패를 값으로 돌려준다
    try:
        # 콘솔 갱신이 부른 것이면 정산 쪽에서도 기록하지 않게 표시를 넘긴다
        poll = {"x-poll": "1"} if "x-poll" in request.headers else None
        r = await request.app.state.http.get(f"/{path}", params=request.query_params, headers=poll, timeout=2)
        return {"ok": True, "served_by": r.headers.get("x-served-by"), "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}


@router.get("/ops/sellers")
async def sellers():
    # consign 이 아는 판매자별 정산 합계. settlement 쪽 값과 나란히 놓아 최종 일관성을 본다
    async with SessionLocal() as s:
        rows = await s.execute(
            select(Item.seller_id, func.count(Sale.id), func.sum(Sale.settlement_amount))
            .join(Sale, Sale.item_id == Item.id).group_by(Item.seller_id)
        )
    return [{"seller_id": sid, "sold_count": c, "total_settlement": t} for sid, c, t in rows]


# ── 대용량 연습용. 브라우저는 한 주소에 동시 연결이 6개뿐이라 1000건을 화면에서 하나씩 보내면 브라우저가 병목이 된다.
#    그래서 부하는 서버 안에서 만들고, 화면은 결과와 추이만 본다


@router.get("/ops/backlog")
async def backlog():
    # 아직 Redis 로 안 나간 Outbox 행 수. /ops/outbox 는 최근 15행이라 적체 크기를 못 본다
    async with SessionLocal() as s:
        return {"waiting": await s.scalar(select(func.count()).where(Outbox.published_at.is_(None)))}


@router.post("/ops/burst")
async def burst(n: int = 1000, seller_id: int = 1, concurrency: int = 10):
    """판매 n건을 한꺼번에 일으킨다. 등록은 한 문장으로 넣고, 판매는 실제 판매 API 와 같은 함수로 한 건씩(트랜잭션 n개)."""
    from app.main import sell_item  # main 이 이 모듈을 import 하므로 여기서 늦게 가져온다

    n, concurrency = min(n, 5000), min(concurrency, 14)  # 풀(5+10) 안쪽으로 — relay 몫 1개를 남긴다
    t0 = time.perf_counter()
    async with SessionLocal() as s:
        ids = (await s.scalars(insert(Item).returning(Item.id), [
            {"seller_id": seller_id, "name": f"대량 {i}", "price": 100_000, "commission_rate": 30} for i in range(n)
        ])).all()
        await s.commit()
    t1 = time.perf_counter()

    gate = asyncio.Semaphore(concurrency)

    async def one(item_id: int):
        async with gate, SessionLocal() as s:
            await sell_item(item_id, s)

    await asyncio.gather(*(one(i) for i in ids))
    t2 = time.perf_counter()
    return {"n": n, "insert_ms": round((t1 - t0) * 1000), "sell_ms": round((t2 - t1) * 1000), "pod": socket.gethostname()}


@router.post("/ops/pool")
async def pool(n: int = 100, hold_ms: int = 300):
    """느린 쿼리 n개를 동시에 돌려 커넥션 풀을 채운다. 각 작업의 완료 시간과, 그 사이 끼어든 SELECT 1 한 건의 대기를 잰다."""
    n, hold_ms = min(n, 300), min(hold_ms, 2000)

    async def slow():
        t = time.perf_counter()
        async with SessionLocal() as s:
            await s.execute(text("SELECT pg_sleep(:t)"), {"t": hold_ms / 1000})
        return round((time.perf_counter() - t) * 1000)

    async def probe():
        await asyncio.sleep(0.05)  # 느린 쿼리들이 풀을 먼저 잡은 뒤 들어오는 "평범한 판매 요청" 역할
        t = time.perf_counter()
        async with SessionLocal() as s:
            await s.execute(text("SELECT 1"))
        return round((time.perf_counter() - t) * 1000)

    *lat, probe_ms = await asyncio.gather(*(slow() for _ in range(n)), probe())
    p = engine.pool
    return {"n": n, "hold_ms": hold_ms, "pool_size": p.size(), "max_overflow": p._max_overflow,
            "latencies": sorted(lat), "probe_ms": probe_ms, "pod": socket.gethostname()}
