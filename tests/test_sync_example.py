import pytest

from src.domains.async_example.presentation.schemas import AsyncExampleResponse
from src.domains.sync_example.database.models import SyncExample


def test_sync_example_생성(sync_client):
    res = sync_client.post("/api/sync/no-login/sync/example", json={"name": "test1", "description": "test"})
    new_sync_example = SyncExample(**res.json())

    assert res.status_code == 201
    assert new_sync_example.name == "test1"


@pytest.mark.asyncio
async def test_async_example_creation(async_client):
    res = await async_client.post("/api/async/no-login/example", json={"name": "test1", "description": "test"})
    new_async_example = AsyncExampleResponse(**res.json())

    assert res.status_code == 201
    assert new_async_example.name == "test1"
