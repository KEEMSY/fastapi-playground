import aioredis

from src.exceptions import handle_exceptions


class AsyncExampleRedis:
    def __init__(self, redis_url: str = 'redis://localhost'):
        self.redis_db = aioredis.from_url(redis_url, decode_responses=True)

    @handle_exceptions
    async def get(self, key: str) -> str:
        value = await self.redis_db.get(key)
        if value is None:
            raise KeyError(f"Key '{key}' does not exist.")
        return value

    @handle_exceptions
    async def set(self, key: str, value: str) -> None:
        await self.redis_db.set(key, value)
