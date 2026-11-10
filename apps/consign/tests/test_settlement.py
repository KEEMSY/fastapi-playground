import pytest

from settlement.main import Base, engine, handle


@pytest.fixture
async def ledger():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


async def test_duplicate_event_is_ignored(ledger):
    # relay 는 at-least-once 라 같은 이벤트가 두 번 올 수 있다
    event = {"sale_id": 1, "seller_id": 1, "settlement_amount": 70_000}
    assert await handle(event) is True
    assert await handle(event) is False
