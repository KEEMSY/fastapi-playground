import asyncio

ITEM = {"seller_id": 1, "name": "울 코트", "price": 100_000, "commission_rate": 30}


async def register(client, **override):
    r = await client.post("/items", json=ITEM | override)
    assert r.status_code == 201
    return r.json()


async def test_register_and_get(client):
    item = await register(client)
    assert item["status"] == "ON_SALE"

    r = await client.get(f"/items/{item['id']}")
    assert r.json()["name"] == "울 코트"


async def test_validation(client):
    r = await client.post("/items", json=ITEM | {"commission_rate": 101})
    assert r.status_code == 422


async def test_sell_and_settlement(client):
    a = await register(client)
    b = await register(client, price=33_333, commission_rate=15)  # 수수료 4999.95 → 4999
    await register(client, seller_id=2)  # 다른 판매자 — 합계에 섞이면 안 된다

    for item in (a, b):
        assert (await client.post(f"/items/{item['id']}/sell")).status_code == 201

    s = (await client.get("/sellers/1/settlement")).json()
    assert s == {"seller_id": 1, "sold_count": 2, "total_settlement": 70_000 + 28_334}


async def test_sell_twice_conflicts(client):
    item = await register(client)
    assert (await client.post(f"/items/{item['id']}/sell")).status_code == 201
    assert (await client.post(f"/items/{item['id']}/sell")).status_code == 409
    assert (await client.post("/items/999/sell")).status_code == 404


async def test_concurrent_sell_only_one_wins(client):
    # 같은 상품에 판매 요청 20개를 동시에 보낸다. gather 는 20개를 한 이벤트 루프에서 동시에 진행시키고,
    # 각 요청은 자기 세션·커넥션을 가지므로 DB 에서 실제로 경쟁한다
    item = await register(client)
    results = await asyncio.gather(*(client.post(f"/items/{item['id']}/sell") for _ in range(20)))

    codes = sorted(r.status_code for r in results)
    assert codes.count(201) == 1
    assert codes.count(409) == 19

    s = (await client.get("/sellers/1/settlement")).json()
    assert s["sold_count"] == 1


async def test_sell_writes_outbox_in_same_transaction(client):
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Outbox

    item = await register(client)
    await client.post(f"/items/{item['id']}/sell")
    await client.post(f"/items/{item['id']}/sell")  # 409 — 이벤트가 생기면 안 된다

    async with SessionLocal() as s:
        events = (await s.scalars(select(Outbox))).all()
    assert len(events) == 1
    assert events[0].payload["settlement_amount"] == 70_000
    assert events[0].published_at is None  # redis_url 이 없으니 relay 가 돌지 않았다


async def test_console(client):
    r = await client.get("/")
    assert r.status_code == 200 and "Consign Console" in r.text
    assert r.headers["x-served-by"]  # 어느 Pod 가 응답했는지

    item = await register(client, seller_id=5)
    await client.post(f"/items/{item['id']}/sell")
    assert (await client.get("/ops/items")).json()[0]["status"] == "SOLD"
    assert (await client.get("/ops/outbox")).json()[0]["amount"] == 70_000
    assert (await client.get("/ops/sellers")).json() == [{"seller_id": 5, "sold_count": 1, "total_settlement": 70_000}]
    assert (await client.get("/ops/stream")).json() == {"enabled": False}  # 테스트엔 Redis 가 없다
    assert (await client.get("/ops/trace")).json() == []  # 기록할 곳이 없으면 빈 목록(요청은 깨지지 않는다)
    # 정산 서비스가 없으면 화면이 깨지지 않고 실패를 값으로 받는다
    assert (await client.get("/ops/settlement/ledger")).json()["ok"] is False
    topo = (await client.get("/ops/topology")).json()
    assert topo["redis"] is None and "consign:consign" not in topo["database"]  # 비밀번호가 화면에 나가지 않는다


async def test_bulk_endpoints(client):
    # 대용량 연습 엔드포인트가 실제 판매 경로를 타는지: n건 판매 = 판매 n건 + 발행 대기 n건(테스트엔 relay 가 없다)
    r = (await client.post("/ops/burst", params={"n": 30, "seller_id": 77})).json()
    assert r["n"] == 30
    assert (await client.get("/sellers/77/settlement")).json() == {"seller_id": 77, "sold_count": 30, "total_settlement": 30 * 70_000}
    assert (await client.get("/ops/backlog")).json() == {"waiting": 30}
    pool = (await client.post("/ops/pool", params={"n": 20, "hold_ms": 100})).json()
    assert len(pool["latencies"]) == 20 and pool["pool_size"] == 5
    assert pool["latencies"][-1] >= 200  # 15개(5+10)를 넘는 5개는 앞 작업이 끝나길 기다린다 → 최소 2배

