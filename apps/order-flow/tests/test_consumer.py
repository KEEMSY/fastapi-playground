import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sqlalchemy import select

from order_flow.processing import record_event
from order_flow.models import Base, ProcessedMessage


@pytest.mark.asyncio
async def test_each_queue_records_the_same_message_once_independently():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    event = {"message_id": "m-2", "order_id": "o-2", "sku": "book", "quantity": 1}

    async with sessions() as session:
        first = await record_event(session, "orders.audit", event)
    async with sessions() as session:
        duplicate = await record_event(session, "orders.audit", event)
    async with sessions() as session:
        other_queue = await record_event(session, "orders.receipts", event)

    async with sessions() as session:
        records = (await session.scalars(select(ProcessedMessage))).all()

    assert first is True
    assert duplicate is False
    assert other_queue is True
    assert {(row.consumer_name, row.message_id) for row in records} == {
        ("orders.audit", "m-2"),
        ("orders.receipts", "m-2"),
    }
    await engine.dispose()
