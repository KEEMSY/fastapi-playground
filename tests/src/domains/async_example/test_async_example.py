import pytest

from src.domains.async_example.constants import ErrorCode
from src.domains.async_example.presentation.schemas import AsyncExampleResponse
from tests.src.domains.async_example.async_example_steps import AsyncExampleSteps

from tests.conftest import async_client, async_session, event_loop


@pytest.mark.asyncio
async def test_async_example_정상_생성(async_client):
    # given
    create_async_example = await AsyncExampleSteps.AsyncExample_생성요청(
        name="test1",
        description="test"
    )

    # when
    res = await async_client.post(url="/api/async/no-login/example", data=create_async_example.model_dump_json())
    async_example_res = AsyncExampleResponse.model_validate(res.json())

    # then
    assert res.status_code == 201
    assert async_example_res.name == "test1"


@pytest.mark.asyncio
async def test_async_example_리스트_조회(async_client):
    # given, when
    res = await async_client.get("/api/async/no-login/example/list")

    # then
    assert res.status_code == 200
    assert len(res.json()["example_list"]) == 0


@pytest.mark.asyncio
async def test_async_example_단일_조회(async_client):
    # given
    create_async_example = await AsyncExampleSteps.AsyncExample_생성요청(
        name="test1",
        description="test"
    )
    create_res = await async_client.post(url="/api/async/no-login/example", data=create_async_example.model_dump_json())
    create_async_example_res = AsyncExampleResponse.model_validate(create_res.json())

    # when
    read_res = await async_client.get(f"/api/async/no-login/example/{create_async_example_res.id}")
    read_async_example_res = AsyncExampleResponse(**read_res.json())

    assert read_res.status_code == 200
    assert create_async_example_res.id == read_async_example_res.id


@pytest.mark.asyncio
async def test_async_example_단일_조회_실패(async_client):
    # given, when
    not_existed_example_id = "999999"
    res = await async_client.get("/api/async/no-login/example/%s" % not_existed_example_id)

    # then
    assert res.status_code == 404
    assert res.json()["code"] == ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_async_example_수정(async_client):
    res = await async_client.post("/api/async/no-login/example", json={"name": "test1", "description": "test"})
    new_async_example = AsyncExampleResponse(**res.json())

    res = await async_client.put(f"/api/async/no-login/example", json={"name": "test2", "description": "test",
                                                                       "async_example_id": new_async_example.id})
    updated_async_example = AsyncExampleResponse(**res.json())

    assert res.status_code == 200
    assert updated_async_example.name == "test2"


@pytest.mark.asyncio
async def test_async_example_수정_실패_NOT_FOUND(async_client):
    res = await async_client.put("/api/async/no-login/example", json={"name": "test2", "description": "test",
                                                                      "async_example_id": 999999})
    assert res.status_code == 404
    assert res.json()["code"] == ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_async_example_삭제(async_client):
    res = await async_client.post("/api/async/no-login/example", json={"name": "test1", "description": "test"})
    new_async_example = AsyncExampleResponse(**res.json())

    res = await async_client.delete(f"/api/async/no-login/example/{new_async_example.id}")
    assert res.status_code == 204

    deleted_res = await async_client.get(f"/api/async/no-login/example/{new_async_example.id}")
    assert deleted_res.status_code == 404


@pytest.mark.asyncio
async def test_async_example_삭제_실패_NOT_FOUND(async_client):
    not_exist_id = 999999
    res = await async_client.delete(f"/api/async/no-login/example/{not_exist_id}")
    assert res.status_code == 404
    assert res.json()["code"] == ErrorCode.NOT_FOUND
