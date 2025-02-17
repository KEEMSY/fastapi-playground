import pytest
import pytest_asyncio
import aioredis
from tests.config import get_test_settings
from tests.utils.docker_utils import start_redis_container

@pytest.fixture(scope="session")
def redis_container():
    """Redis 컨테이너 관리 fixture"""
    container = start_redis_container()
    yield container
    container.stop()
    container.remove()

@pytest_asyncio.fixture
async def redis_client(redis_container):
    """Redis 클라이언트 fixture"""
    settings = get_test_settings()
    redis = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        encoding="utf-8",
        socket_timeout=5.0,
        socket_connect_timeout=5.0
    )
    
    try:
        await redis.ping()
        await redis.flushdb()
        yield redis
    finally:
        await redis.close()
