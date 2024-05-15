import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.async_example.business.async_example_service import create_async_example_with_no_user, \
    read_async_example, get_async_example_list, fetch_async_example_with_user_v2, delete_async_example
from src.domains.async_example.business.schemas import AsyncExampleSchema, ASyncExampleSchemaList
from src.domains.async_example.constants import ErrorCode
from src.domains.async_example.database.models import AsyncExample
from src.exceptions import BLException
from tests.src.domains.async_example.async_example_steps import AsyncExampleSteps

from tests.conftest import async_session as async_db, event_loop, setup_database


@pytest.mark.asyncio
class TestAsyncExample:

    async def test_async_example_생성_테스트(self, async_db):
        # given
        create_async_example = await AsyncExampleSteps.AsyncExample_생성요청(
            name="test1", description="test"
        )
        # when
        async_example_schema = await create_async_example_with_no_user(async_db, create_async_example)
        async_example = AsyncExample(
            name=async_example_schema.name, description=async_example_schema.description
        )
        # then
        assert async_example_schema.name == async_example.name
        assert async_example_schema.description == async_example.description

    async def test_async_example_조회_테스트(self, async_db):
        # given
        async_example_schema = await self._save_async_example(async_db)
        # when
        expected_async_example = await read_async_example(async_db, async_example_schema.id)
        # then
        assert expected_async_example.id == async_example_schema.id
        assert expected_async_example.name == async_example_schema.name
        assert expected_async_example.description == async_example_schema.description

    async def test_async_example_조회_실패_테스트(self, async_db):
        # given
        not_existed_example_id = 999999
        # when, then
        with pytest.raises(BLException) as exc_info:
            await read_async_example(async_db, not_existed_example_id)
        assert exc_info.value.code == ErrorCode.NOT_FOUND
        assert str(exc_info.value.detail) == f"No AsyncExample found with id {not_existed_example_id}"

    async def test_async_example_리스트_조회_테스트(self, async_db):
        # given
        n = 10
        for _ in range(n):
            await self._save_async_example(async_db)
        # when
        async_example_schema_list: ASyncExampleSchemaList = await get_async_example_list(async_db, keyword="test")
        # then
        assert len(async_example_schema_list.example_list) == n
        assert async_example_schema_list.example_list[0].name == "test"
        assert async_example_schema_list.example_list[0].description == "test"

    async def test_async_example_리스트_조회_실패_테스트(self, async_db):
        # given
        n = 10
        for _ in range(n):
            await self._save_async_example(async_db)
        # when
        async_example_schema_list = await get_async_example_list(async_db, keyword="not_exist")
        # then
        assert len(async_example_schema_list.example_list) == 0

    # 추가 테스트 메서드는 여기에 정의...

    async def test_async_example_수정_테스트(self, async_db):
        # given
        async_example_schema = await self._save_async_example(async_db=async_db)
        update_async_example = await AsyncExampleSteps.AsyncExample_수정요청_v2(
            async_example_id=async_example_schema.id,
            name="updated_test",
            description="updated_test"
        )

        # when
        updated_async_example = await fetch_async_example_with_user_v2(async_db, update_async_example)

        # then
        assert updated_async_example.name == "updated_test"
        assert updated_async_example.description == "updated_test"

    async def test_async_example_삭제_테스트(self, async_db):
        # given
        async_example_schema = await self._save_async_example(async_db=async_db)

        # when
        await delete_async_example(async_db, async_example_schema.id)

        # then
        with pytest.raises(BLException) as exc_info:
            await read_async_example(async_db, async_example_schema.id)

    ### Helper function ###
    async def _save_async_example(self, async_db: AsyncSession, name="test", description="test"):
        create_async_example = await AsyncExampleSteps.AsyncExample_생성요청(
            name=name, description=description
        )
        async_example_schema: AsyncExampleSchema = await create_async_example_with_no_user(async_db,
                                                                                           create_async_example)
        return async_example_schema