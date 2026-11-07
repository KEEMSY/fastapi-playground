import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from order_flow.dispatch import record_and_enqueue
from order_flow.models import Base, ProcessedMessage, TaskDispatchOutbox


@pytest.mark.asyncio
async def test_receipt_queue_enqueues_task_only_for_first_delivery():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    event = {"message_id": "message-1", "order_id": "order-1"}

    first = await record_and_enqueue("orders.receipts", event, sessions)
    duplicate = await record_and_enqueue("orders.receipts", event, sessions)

    assert first is True
    assert duplicate is False
    async with sessions() as session:
        inbox_rows = (await session.scalars(select(ProcessedMessage))).all()
        task_rows = (await session.scalars(select(TaskDispatchOutbox))).all()
    assert [(row.consumer_name, row.message_id) for row in inbox_rows] == [
        ("orders.receipts", "message-1")
    ]
    assert [(row.id, row.order_id, row.status) for row in task_rows] == [
        ("message-1", "order-1", "pending")
    ]
    await engine.dispose()


@pytest.mark.asyncio
async def test_audit_queue_records_event_without_sending_receipt_task():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    await record_and_enqueue(
        "orders.audit",
        {"message_id": "message-2", "order_id": "order-2"},
        sessions,
    )

    async with sessions() as session:
        task_rows = (await session.scalars(select(TaskDispatchOutbox))).all()
    assert task_rows == []
    await engine.dispose()
