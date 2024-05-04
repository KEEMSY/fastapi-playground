import pytest

from src.domains.async_example.constants import ErrorCode
from src.domains.async_example.presentation.schemas import AsyncExampleResponse
from tests.conftest import async_client, async_session, event_loop


@pytest.mark.asyncio
async def test_async_example_creation(async_client):
    res = await async_client.post("/api/async/no-login/example", json={"name": "test1", "description": "test"})
    new_async_example = AsyncExampleResponse(**res.json())

    assert res.status_code == 201
    assert new_async_example.name == "test1"


@pytest.mark.asyncio
async def test_async_example_list(async_client):
    res = await async_client.get("/api/async/no-login/example/list")
    assert res.status_code == 200
    assert len(res.json()["example_list"]) == 0


@pytest.mark.asyncio
async def test_async_example_단일_조회(async_client):
    res = await async_client.post("/api/async/no-login/example", json={"name": "test1", "description": "test"})
    new_async_example = AsyncExampleResponse(**res.json())

    res = await async_client.get(f"/api/async/no-login/example/{new_async_example.id}")
    retrieved_async_example = AsyncExampleResponse(**res.json())

    assert res.status_code == 200
    assert new_async_example == retrieved_async_example


@pytest.mark.asyncio
async def test_async_example_단일_조회_실패(async_client):
    res = await async_client.get("/api/async/no-login/example/999999")
    assert res.status_code == 404
    assert res.json()["code"] == ErrorCode.NOT_FOUND


