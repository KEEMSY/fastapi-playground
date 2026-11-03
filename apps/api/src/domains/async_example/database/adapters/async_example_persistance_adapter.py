from abc import ABC

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.database import AsyncTransactionManager, async_transactional
from src.domains.async_example.business.ports.async_example_repository import AsyncExampleRepository
from src.domains.async_example.business.schemas import AsyncExampleSchema, RelatedAsyncExampleSchema
from src.domains.async_example.database.async_example_rdb import AsyncExampleCRUD


class AsyncExamplePersistenceAdapter(AsyncExampleRepository, ABC):

    def __init__(self, async_db: AsyncSession):
        self.async_rdb_crud = AsyncExampleCRUD(async_db)

        self.transaction_manager = AsyncTransactionManager(async_db)

    @async_transactional
    async def create_async_example(self, async_example: AsyncExampleSchema) -> AsyncExampleSchema:
        return await self.async_rdb_crud.create_async_example(async_example)

    @async_transactional
    async def get_async_example(self, async_example_id: int) -> AsyncExampleSchema:
        return await self.async_rdb_crud.read_fetch_async_example(async_example_id)

    async def get_async_example_list(self, limit, offset, keyword):
        return await self.async_rdb_crud.read_async_example_list(limit, offset, keyword)

    @async_transactional
    async def update_async_example(self, example_id: str, async_example: AsyncExampleSchema) -> AsyncExampleSchema:
        return await self.async_rdb_crud.update_async_example_v2(example_id, async_example)

    @async_transactional
    async def delete_async_example(self, async_example_id: int) -> bool:
        return await self.async_rdb_crud.delete_async_example(async_example_id)

    @async_transactional
    async def create_async_example_related(self, async_example: AsyncExampleSchema,
                                           related_async_example: RelatedAsyncExampleSchema
                                           ) -> RelatedAsyncExampleSchema:
        created_async_example: AsyncExampleSchema = await self.async_rdb_crud.create_async_example(async_example)
        related_async_example = await self.async_rdb_crud.create_related_async_example(related_async_example)
        return related_async_example

    @async_transactional
    async def create_async_example_with_error1(self, async_example: AsyncExampleSchema,
                                               related_async_example: RelatedAsyncExampleSchema):
        await self.async_rdb_crud.create_async_example(async_example)
        raise Exception("강제 오류 발생")
        await self.async_rdb_crud.create_related_async_example(related_async_example)

    @async_transactional
    async def create_async_example_with_error2(self, async_example: AsyncExampleSchema,
                                               related_async_example: RelatedAsyncExampleSchema):
        await self.async_rdb_crud.create_async_example(async_example)
        await self.async_rdb_crud.create_related_async_example(related_async_example)
        raise Exception("강제 오류 발생")

    async def get_related_async_example(self, related_async_example_id):
        return await self.async_rdb_crud.read_fetch_related_async_example(related_async_example_id)

    async def get_related_async_example_list(self, limit, offset, keyword):
        return await self.async_rdb_crud.read_related_async_example_list(limit, offset, keyword)