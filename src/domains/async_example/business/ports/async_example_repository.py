from abc import ABC, abstractmethod

from src.domains.async_example.business.schemas import AsyncExampleSchema


class AsyncExampleRepository(ABC):
    @abstractmethod
    async def get_async_example(self, example_id: str) -> AsyncExampleSchema:
        pass
    @abstractmethod