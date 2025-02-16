from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.database import get_async_db
from src.domains.async_example.database.adapters.async_example_persistance_adapter import AsyncExamplePersistenceAdapter


async def get_async_example_repository(
        async_db: AsyncSession = Depends(get_async_db)) -> AsyncExamplePersistenceAdapter:
    return AsyncExamplePersistenceAdapter(async_db)
