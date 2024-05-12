import pytest

from src.domains.async_example.constants import ErrorCode
from src.domains.async_example.presentation.schemas import AsyncExampleResponse
from tests.src.domains.async_example.async_example_steps import AsyncExampleSteps

from tests.conftest import async_client, async_session, event_loop, setup_database


@pytest.mark.asyncio
async def test_async_example_정상_생성(async_client):
    # given
    create_async_example = await AsyncExampleSteps.AsyncExample_생성요청(
        name="test1",
        description="test"
    )

    # when
    res = await async_client.post(url="/api/async/no-login/example", content=create_async_example.model_dump_json())
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
    create_res = await async_client.post(url="/api/async/no-login/example", content=create_async_example.model_dump_json())
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
    # given
    create_async_example_request = await AsyncExampleSteps.AsyncExample_생성요청(
        name="test1",
        description="test"
    )
    create_res = await async_client.post(url="/api/async/no-login/example",
                                         content=create_async_example_request.model_dump_json())
    create_res_schema = AsyncExampleResponse.model_validate(create_res.json())

    # when
    update_async_example = await AsyncExampleSteps.AsyncExample_수정요청_v2(
        async_example_id=create_res_schema.id,
        name="test_update_name",
        description="test_update_description"
    )
    update_res = await async_client.put(f"/api/async/no-login/example", content=update_async_example.model_dump_json())
    update_res_schema = AsyncExampleResponse.model_validate(update_res.json())

    # then
    assert update_res.status_code == 200
    assert update_res_schema.name == "test_update_name"


@pytest.mark.asyncio
async def test_async_example_수정_실패_NOT_FOUND(async_client):
    # given
    not_existed_example_id = 99999999
    update_async_example = await AsyncExampleSteps.AsyncExample_수정요청_v2(
        async_example_id=not_existed_example_id,
        name="test_update_name",
        description="test_update_description"
    )

    # when
    update_res = await async_client.put(f"/api/async/no-login/example", content=update_async_example.model_dump_json())

    # then
    assert update_res.status_code == 404
    assert update_res.json()["code"] == ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_async_example_삭제(async_client):
    # given
    create_async_example_request = await AsyncExampleSteps.AsyncExample_생성요청(
        name="test1",
        description="test"
    )
    create_res = await async_client.post(url="/api/async/no-login/example",
                                         content=create_async_example_request.model_dump_json())
    create_res_schema = AsyncExampleResponse.model_validate(create_res.json())

    # when
    res = await async_client.delete(f"/api/async/no-login/example/{create_res_schema.id}")

    # then
    assert res.status_code == 204


@pytest.mark.asyncio
async def test_async_example_삭제_실패_NOT_FOUND(async_client):
    # given, when
    not_existed_example_id = "999999"
    res = await async_client.delete(f"/api/async/no-login/example/{not_existed_example_id}")

    # then
    assert res.status_code == 404
    assert res.json()["code"] == ErrorCode.NOT_FOUND
