# import pytest

# from tests.conftest import async_session as async_db, event_loop, async_example_redis, redis_client

# @pytest.mark.asyncio
# class TestAsyncExampleRedis:
#     @pytest.fixture(autouse=True)
#     def setup(self, async_example_redis):
#         self.async_example_redis = async_example_redis

#     async def test_async_example_set_get_테스트(self):
#         # given
#         key = "test_key"
#         value = "test_value"

#         # when
#         await self.async_example_redis.set(key, value)

#         # then
#         assert await self.async_example_redis.get(key) == value