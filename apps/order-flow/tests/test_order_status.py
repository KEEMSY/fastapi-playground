import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from order_flow.api import app, get_session
from order_flow.models import Base, Order, OrderReceipt, OutboxEvent, ProcessedMessage, TaskDispatchOutbox


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
async def test_order_status_returns_not_found_for_unknown_order(client):
    client, _ = client

    response = await client.get("/orders/missing-order")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_order_status_reports_progress_from_related_records(client):
    client, sessions = client
    async with sessions() as session, session.begin():
        session.add(Order(id="order-1", sku="book-1", quantity=1, status="created"))
        session.add(OutboxEvent(
            id="event-1", aggregate_id="order-1", event_type="order.created",
            payload={"message_id": "event-1", "order_id": "order-1"}, status="pending",
        ))

    response = await client.get("/orders/order-1")
    assert response.status_code == 200
    assert response.json() == {
        "order_id": "order-1",
        "order_status": "created",
        "event_status": "pending",
        "processed_consumers": [],
        "receipt_task_status": None,
        "receipt_recorded": False,
    }

    async with sessions() as session, session.begin():
        event = await session.get(OutboxEvent, "event-1")
        event.status = "published"
        session.add_all([
            ProcessedMessage(consumer_name="orders.audit", message_id="event-1"),
            ProcessedMessage(consumer_name="orders.receipts", message_id="event-1"),
            TaskDispatchOutbox(id="event-1", order_id="order-1", status="dispatched"),
            OrderReceipt(order_id="order-1"),
        ])

    response = await client.get("/orders/order-1")
    assert response.json() == {
        "order_id": "order-1",
        "order_status": "created",
        "event_status": "published",
        "processed_consumers": ["orders.audit", "orders.receipts"],
        "receipt_task_status": "dispatched",
        "receipt_recorded": True,
    }
