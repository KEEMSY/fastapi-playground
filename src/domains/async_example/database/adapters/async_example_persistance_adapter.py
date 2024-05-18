from abc import ABC

from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.async_example.business.ports.async_example_repository import AsyncExampleRepository
from src.domains.async_example.business.schemas import AsyncExampleSchema
from src.domains.async_example.database.async_example_rdb import AsyncExampleCRUD


class AsyncExamplePersistenceAdapter(AsyncExampleRepository, ABC):

    def __init__(self, async_db: AsyncSession):
        self.async_rdb_crud = AsyncExampleCRUD(async_db)

    async def create_async_example(self, async_example: AsyncExampleSchema) -> AsyncExampleSchema:
        return await self.async_rdb_crud.create_async_example(async_example)

    async def get_async_example(self, async_example_id: int) -> AsyncExampleSchema:
        return await self.async_rdb_crud.read_fetch_async_example(async_example_id)

    async def get_async_example_list(self, limit, offset, keyword):
        return await self.async_rdb_crud.read_async_example_list(limit, offset, keyword)

    async def update_async_example(self, example_id: str, async_example: AsyncExampleSchema) -> AsyncExampleSchema:
        return await self.async_rdb_crud.update_async_example_v2(example_id, async_example)

    async def delete_async_example(self, async_example_id: int) -> bool:
        return await self.async_rdb_crud.delete_async_example(async_example_id)
