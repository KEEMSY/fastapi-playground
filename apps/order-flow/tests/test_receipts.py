import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from order_flow.models import Base, OrderReceipt
from order_flow.receipts import mark_receipt_sent


@pytest.mark.asyncio
async def test_receipt_side_effect_is_idempotent():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    assert await mark_receipt_sent("order-1", sessions) is True
    assert await mark_receipt_sent("order-1", sessions) is False
    async with sessions() as session:
        assert await session.get(OrderReceipt, "order-1") is not None
    await engine.dispose()
