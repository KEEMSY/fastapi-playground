import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from order_flow.models import Base, TaskDispatchOutbox
from order_flow.task_relay import relay_once


@pytest.fixture
async def sessions():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_relay_publishes_pending_command_with_deterministic_task_id(sessions):
    async with sessions() as session, session.begin():
        session.add(TaskDispatchOutbox(id="event-1", order_id="order-1", status="pending"))
    published = []

    count = await relay_once(sessions, lambda order_id, task_id: published.append((order_id, task_id)))

    assert count == 1
    assert published == [("order-1", "receipt-event-1")]
    async with sessions() as session:
        row = await session.get(TaskDispatchOutbox, "event-1")
    assert row.status == "dispatched"
    assert row.attempts == 1
    assert row.dispatched_at is not None


@pytest.mark.asyncio
async def test_publish_timeout_leaves_command_pending_for_same_task_id_retry(sessions):
    async with sessions() as session, session.begin():
        session.add(TaskDispatchOutbox(id="event-2", order_id="order-2", status="pending"))
    accepted_task_ids = []

    def broker_accepts_then_times_out(order_id, task_id):
        accepted_task_ids.append(task_id)
        raise TimeoutError("publish confirmation was lost")

    count = await relay_once(sessions, broker_accepts_then_times_out)

    assert count == 0
    async with sessions() as session:
        row = await session.get(TaskDispatchOutbox, "event-2")
    assert row.status == "pending"
    assert row.attempts == 1

    await relay_once(sessions, lambda order_id, task_id: accepted_task_ids.append(task_id))

    assert accepted_task_ids == ["receipt-event-2", "receipt-event-2"]
    async with sessions() as session:
        row = await session.get(TaskDispatchOutbox, "event-2")
    assert row.status == "dispatched"
    assert row.attempts == 2
