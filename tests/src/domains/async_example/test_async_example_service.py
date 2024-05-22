import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.async_example.business.async_example_service import create_async_example_with_no_user, \
    read_async_example, AsyncExampleService
from src.domains.async_example.business.ports.async_example_repository import AsyncExampleRepository
from src.domains.async_example.business.schemas import AsyncExampleSchema, ASyncExampleSchemaList
from src.domains.async_example.constants import ErrorCode
from src.domains.async_example.database.models import AsyncExample
from src.exceptions import ExceptionResponse
from tests.src.domains.async_example.async_example_steps import AsyncExampleSteps

from tests.conftest import async_session as async_db, event_loop, setup_database, async_example_repository, \
    get_async_example_repository, get_async_example_repository, async_session


@pytest.mark.asyncio
class TestAsyncExampleByFunctionalTest:

    @pytest.fixture(autouse=True)
    def setup(self, async_db: AsyncSession, get_async_example_repository: AsyncExampleRepository):
        self.async_db = async_db
        self.async_example_repository = get_async_example_repository
        self.async_example_service = AsyncExampleService(async_db=async_db,
                                                         async_repository=self.async_example_repository)

    async def test_async_example_생성_테스트(self):
        # given
        create_async_example_schema = await AsyncExampleSteps.AsyncExample_스키마_생성(
            name="test1", description="test"
        )
        # when
        async_example_schema = await self.async_example_repository.create_async_example(create_async_example_schema)
        async_example = AsyncExample(
            name=async_example_schema.name, description=async_example_schema.description
        )
        # then
        assert async_example_schema.name == async_example.name
        assert async_example_schema.description == async_example.description

    async def test_async_example_조회_테스트(self):
        # given
        async_example_schema = await self._save_async_example(self.async_db)

        # When
        expected_async_example = await self.async_example_service.get_async_example(async_example_schema.id)

        # Then
        assert expected_async_example.id == async_example_schema.id
        assert expected_async_example.name == async_example_schema.name
        assert expected_async_example.description == async_example_schema.description

    async def test_async_example_조회_실패_테스트(self):
        # given
        not_existed_example_id = 999999
        # when, then
        with pytest.raises(ExceptionResponse) as exc_info:
            await self.async_example_service.get_async_example(not_existed_example_id)
        assert exc_info.value.error_code == ErrorCode.NOT_FOUND
        assert str(exc_info.value.message) == f"No AsyncExample found with id {not_existed_example_id}"

    async def test_async_example_리스트_조회_테스트(self, async_db):
        # given
        n = 10
        for _ in range(n):
            await self._save_async_example(async_db)
        # when
        async_example_schema_list: ASyncExampleSchemaList = await self.async_example_service.get_async_example_list(
            keyword="test")
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
        async_example_schema_list = await self.async_example_service.get_async_example_list(keyword="not_exist")
        # then
        assert len(async_example_schema_list.example_list) == 0

    async def test_async_example_수정_테스트(self, async_db):
        # given
        async_example_schema = await self._save_async_example(async_db=async_db)
        update_async_example = await AsyncExampleSteps.AsyncExample_수정요청_v2(
            async_example_id=async_example_schema.id,
            name="updated_test",
            description="updated_test"
        )

        # when
        updated_async_example = await self.async_example_service.fetch_async_example_with_user_v2(
            request=update_async_example)

        # then
        assert updated_async_example.name == "updated_test"
        assert updated_async_example.description == "updated_test"

    async def test_async_example_삭제_테스트(self, async_db):
        # given
        async_example_schema = await self._save_async_example(async_db=async_db)

        # when
        await self.async_example_service.delete_async_example(async_example_schema.id)

        # then
        with pytest.raises(ExceptionResponse) as exc_info:
            await read_async_example(async_db, async_example_schema.id)

    async def test_async_example_삭제_실패_테스트(self, async_db):
        # given
        not_existed_example_id = 999999

        # when, then
        with pytest.raises(ExceptionResponse) as exc_info:
            await self.async_example_service.delete_async_example(example_id=not_existed_example_id)
        assert exc_info.value.error_code == ErrorCode.NOT_FOUND
        assert str(exc_info.value.message) == f"No AsyncExample found with id {not_existed_example_id}"

    ### Helper function ###
    async def _save_async_example(self, async_db: AsyncSession, name="test", description="test"):
        create_async_example = await AsyncExampleSteps.AsyncExample_생성요청(
            name=name, description=description
        )
        async_example_schema: AsyncExampleSchema = await create_async_example_with_no_user(async_db,
                                                                                           create_async_example)
        return async_example_schema

