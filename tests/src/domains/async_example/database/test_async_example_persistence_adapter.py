import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.async_example.business.schemas import ASyncExampleSchemaList
from src.domains.async_example.database.adapters.async_example_persistance_adapter import AsyncExamplePersistenceAdapter
from tests.src.domains.async_example.async_example_steps import AsyncExampleSteps

from tests.conftest import async_session as async_db, event_loop, setup_database


@pytest.mark.asyncio
class TestAsyncExamplePersistenceAdapter:
    @pytest.fixture(autouse=True)
    def setup(self, async_db: AsyncSession):
        self.async_example_persistence_adapter = AsyncExamplePersistenceAdapter(async_db)

    async def test_async_example_transactional_테스트(self):
        # given
        async_example_schema = await AsyncExampleSteps.AsyncExample_스키마_생성(
            name="test_name", description="test_description"
        )
        related_async_example_schema = await AsyncExampleSteps.RelatedAsyncExample_스키마_생성(
            name="related_test_name", description="test_description"
        )

        # when
        related_async_example_schema = await self.async_example_persistence_adapter.create_async_example_related(
            async_example=async_example_schema, related_async_example=related_async_example_schema)

        # then
        expected_related_async_example = await self.async_example_persistence_adapter.get_related_async_example(
            related_async_example_id=related_async_example_schema.id
        )
        expected_async_example_list: ASyncExampleSchemaList = await self.async_example_persistence_adapter.get_async_example_list(
            keyword="test_name", limit=10, offset=0
        )

        assert expected_async_example_list.total == 1
        assert expected_async_example_list.example_list[0].name == async_example_schema.name
        assert related_async_example_schema.name == expected_related_async_example.name
        assert related_async_example_schema.description == expected_related_async_example.description

    async def test_async_example_transactional_rollback_테스트1(self):
        # given
        async_example_schema = await AsyncExampleSteps.AsyncExample_스키마_생성(
            name="test_name", description="test_description"
        )
        related_async_example_schema = await AsyncExampleSteps.RelatedAsyncExample_스키마_생성(
            name="related_test_name", description="test_description"
        )

        # when, then
        with pytest.raises(Exception) as exc_info:
            await self.async_example_persistence_adapter.create_async_example_with_error1(
                async_example=async_example_schema, related_async_example=related_async_example_schema)
        assert str(exc_info.value) == "강제 오류 발생"

        expected_async_example_list: ASyncExampleSchemaList = await self.async_example_persistence_adapter.get_async_example_list(
            keyword="test_name", limit=10, offset=0
        )
        assert expected_async_example_list.total == 0

    async def test_async_example_transactional_rollback_테스트2(self):
        # given
        async_example_schema = await AsyncExampleSteps.AsyncExample_스키마_생성(
            name="test_name", description="test_description"
        )
        related_async_example_schema = await AsyncExampleSteps.RelatedAsyncExample_스키마_생성(
            name="related_test_name", description="test_description"
        )

        # when, then
        with pytest.raises(Exception) as exc_info:
            await self.async_example_persistence_adapter.create_async_example_with_error2(
                async_example=async_example_schema, related_async_example=related_async_example_schema)
        assert str(exc_info.value) == "강제 오류 발생"

        expected_related_async_example_list = await self.async_example_persistence_adapter.get_related_async_example_list(
            limit=10, offset=0, keyword=related_async_example_schema.name
        )
        assert expected_related_async_example_list.total == 0
