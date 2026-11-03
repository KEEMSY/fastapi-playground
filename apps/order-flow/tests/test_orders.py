import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from order_flow.api import app, get_session
from order_flow.models import Base, OutboxEvent


@pytest.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def session_override():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client, sessions
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_order_persists_order_and_outbox(client):
    client, sessions = client
    response = await client.post(
        "/orders",
        headers={"Idempotency-Key": "checkout-001"},
        json={"sku": "book-1", "quantity": 2},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "created"
    assert response.json()["sku"] == "book-1"
    async with sessions() as session:
        event_count = await session.scalar(select(func.count()).select_from(OutboxEvent))
    assert event_count == 1


@pytest.mark.asyncio
async def test_replaying_same_key_and_body_returns_same_order(client):
    client, _ = client
    headers = {"Idempotency-Key": "checkout-002"}
    payload = {"sku": "book-2", "quantity": 1}

    first = await client.post("/orders", headers=headers, json=payload)
    second = await client.post("/orders", headers=headers, json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json() == first.json()


@pytest.mark.asyncio
async def test_reusing_key_with_different_body_returns_conflict(client):
    client, _ = client
    headers = {"Idempotency-Key": "checkout-003"}
    await client.post("/orders", headers=headers, json={"sku": "book-3", "quantity": 1})

    response = await client.post("/orders", headers=headers, json={"sku": "book-4", "quantity": 1})

    assert response.status_code == 409
