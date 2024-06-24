import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.async_example.business.schemas import AsyncExampleSchema
from src.domains.async_example.constants import ErrorCode
from src.domains.async_example.database.async_example_rdb import AsyncExampleCRUD
from src.exceptions import ExceptionResponse
from tests.src.domains.async_example.async_example_steps import AsyncExampleSteps

from tests.conftest import async_session as async_db, event_loop, setup_database


@pytest.mark.asyncio
class TestAsyncExampleRDB:
    @pytest.fixture(autouse=True)
    def setup(self, async_db: AsyncSession):
        self.async_example_rdb = AsyncExampleCRUD(async_db)

    async def test_async_example_생성_테스트(self):
        # given
        async_example_schema = await AsyncExampleSteps.AsyncExample_스키마_생성(
            name="test_name", description="test_description"
        )

        # when
        async_example_schema = await self.async_example_rdb.create_async_example(
            async_example_schema)
        expected = await self.async_example_rdb.read_fetch_async_example(
            async_example_id=async_example_schema.id
        )

        # then
        assert async_example_schema.name == expected.name
        assert async_example_schema.description == expected.description

    async def test_async_example_조회_테스트(self):
        # given
        async_example_schema = await AsyncExampleSteps.AsyncExample_스키마_생성(
            name="test_name", description="test_description"
        )
        async_example_schema = await self.async_example_rdb.create_async_example(
            async_example_schema)

        # when
        expected: AsyncExampleSchema = await self.async_example_rdb.read_fetch_async_example(
            async_example_id=async_example_schema.id
        )

        # then
        assert async_example_schema.name == expected.name
        assert async_example_schema.description == expected.description

    async def test_async_example_list_조회_정렬_테스트(self):
        # given
        async_example_schema = await AsyncExampleSteps.AsyncExample_스키마_생성(
            name="test_name", description="test_description"
        )
        async_example_schema = await self.async_example_rdb.create_async_example(
            async_example_schema)
        async_example_schema2 = await AsyncExampleSteps.AsyncExample_스키마_생성(
            name="test_name2", description="test_description2"
        )
        async_example_schema2 = await self.async_example_rdb.create_async_example(
            async_example_schema2)

        # when
        async_example_list = await self.async_example_rdb.read_async_example_list(
            limit=10, offset=0, keyword=None, sort_by=['name'], sort_order=['asc']
        )

        # then
        assert async_example_list.example_list[0].name == async_example_schema.name
        assert async_example_list.example_list[1].name == async_example_schema2.name

    async def test_async_example_조회_실패_테스트(self):
        # given
        not_existed_example_id = 99999

        # when, then
        with pytest.raises(ExceptionResponse) as exc_info:
            await self.async_example_rdb.read_fetch_async_example(
                async_example_id=not_existed_example_id
            )
        assert exc_info.value.error_code == ErrorCode.NOT_FOUND
        assert str(exc_info.value.message) == f"No AsyncExample found with id {not_existed_example_id}"

    async def test_async_example_리스트_조회_테스트(self):
        # given
        async_example_schema = await AsyncExampleSteps.AsyncExample_스키마_생성(
            name="test_name", description="test_description"
        )

        n = 10
        for _ in range(n):
            await self.async_example_rdb.create_async_example(async_example_schema)

        # when
        async_example_list = await self.async_example_rdb.read_async_example_list(
            limit=10, offset=0, keyword=None
        )

        # then
        assert len(async_example_list.example_list) == n

    async def test_async_example_수정_테스트(self):
        # given
        async_example_schema = await AsyncExampleSteps.AsyncExample_스키마_생성(
            name="test_name", description="test_description"
        )
        async_example_schema = await self.async_example_rdb.create_async_example(
            async_example_schema)
        update_async_example_schema = await AsyncExampleSteps.AsyncExample_스키마_생성(
            name="updated_name", description="updated_description"
        )
        update_async_example_schema.id = async_example_schema.id

        # when
        updated_async_example = await self.async_example_rdb.update_async_example_v2(
            async_example_schema=update_async_example_schema
        )

        # then
        assert updated_async_example.name == update_async_example_schema.name
        assert updated_async_example.description == update_async_example_schema.description

    async def test_async_example_수정_실패_테스트(self):
        # given
        not_existed_example_id = 99999
        update_async_example_schema = await AsyncExampleSteps.AsyncExample_스키마_생성(
            name="updated_name", description="updated_description"
        )
        update_async_example_schema.id = not_existed_example_id

        # when, then
        with pytest.raises(ExceptionResponse) as exc_info:
            await self.async_example_rdb.update_async_example_v2(
                async_example_schema=update_async_example_schema
            )
        assert exc_info.value.error_code == ErrorCode.NOT_FOUND
        assert str(exc_info.value.message) == f"No AsyncExample found with id {update_async_example_schema.id}"

    async def test_async_example_삭제_테스트(self):
        # given
        async_example_schema = await AsyncExampleSteps.AsyncExample_스키마_생성(
            name="test_name", description="test_description"
        )
        async_example_schema = await self.async_example_rdb.create_async_example(
            async_example_schema)

        # when
        await self.async_example_rdb.delete_async_example(
            async_example_id=async_example_schema.id
        )

        # then
        with pytest.raises(ExceptionResponse) as exc_info:
            await self.async_example_rdb.delete_async_example(
                async_example_id=async_example_schema.id
            )

    async def test_async_example_삭제_실패_테스트(self):
        # given
        not_existed_example_id = 99999

        # when, then
        with pytest.raises(ExceptionResponse) as exc_info:
            await self.async_example_rdb.delete_async_example(
                async_example_id=not_existed_example_id
            )
        assert exc_info.value.error_code == ErrorCode.NOT_FOUND
        assert str(exc_info.value.message) == f"No AsyncExample found with id {not_existed_example_id}"
