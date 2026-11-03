from abc import ABC, abstractmethod

from src.domains.async_example.business.schemas import AsyncExampleSchema


class AsyncExampleRepository(ABC):
    @abstractmethod
    async def create_async_example(self, async_example: AsyncExampleSchema) -> AsyncExampleSchema:
        pass

    @abstractmethod
    async def get_async_example(self, async_example_id: int) -> AsyncExampleSchema:
        pass

    @abstractmethod
    async def get_async_example_list(self, limit, offset, keyword):
        pass

    @abstractmethod
    async def update_async_example(self, example_id: str, async_example: AsyncExampleSchema) -> AsyncExampleSchema:
        pass

    @abstractmethod
    async def delete_async_example(self, example_id: str) -> bool:
        pass
