import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from order_flow.dispatch import record_and_dispatch
from order_flow.models import Base


class TaskRecorder:
    def __init__(self):
        self.order_ids = []

    def delay(self, order_id):
        self.order_ids.append(order_id)


@pytest.mark.asyncio
async def test_receipt_queue_sends_task_only_for_first_delivery():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    task = TaskRecorder()
    event = {"message_id": "message-1", "order_id": "order-1"}

    first = await record_and_dispatch("orders.receipts", event, sessions, task)
    duplicate = await record_and_dispatch("orders.receipts", event, sessions, task)

    assert first is True
    assert duplicate is False
    assert task.order_ids == ["order-1"]
    await engine.dispose()


@pytest.mark.asyncio
async def test_audit_queue_records_event_without_sending_receipt_task():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    task = TaskRecorder()

    await record_and_dispatch(
        "orders.audit",
        {"message_id": "message-2", "order_id": "order-2"},
        sessions,
        task,
    )

    assert task.order_ids == []
    await engine.dispose()
