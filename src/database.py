import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from functools import wraps

import aioredis
import redis
from sqlalchemy import create_engine, MetaData
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from config import SYNC_SQLALCHEMY_DATABASE_URL, ASYNC_SQLALCHEMY_DATABASE_URL
from src.exceptions import ExceptionResponse

"""
create_engine, sessionmaker 등을 사용하는것은 SQLAlchemy 데이터베이스를 사용하기 위해 따라야 할 규칙이다.

- autocommit=False
  데이터를 변경했을 때 commit 이라는 사인을 주어야만 실제 저장이 된다. 

- autocommit=True
  commit 없어도 즉시 데이터베이스에 변경사항이 적용된다. 

- autocommit=False
  데이터를 잘못 저장했을 경우 rollback 으로 되돌리는 것이 가능하다. 

- autocommit=True
  commit이 필요없는 것처럼 rollback도 동작하지 않는다.
"""

MYSQL_INDEXES_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=MYSQL_INDEXES_NAMING_CONVENTION)
Base = declarative_base(metadata=metadata)

logger = logging.getLogger(__name__)

# 비동기 엔진 설정 수정
async_engine = create_async_engine(
    ASYNC_SQLALCHEMY_DATABASE_URL,
    pool_size=20,           # 기본 풀 크기 증가
    max_overflow=30,        # 최대 초과 연결 수 증가
    pool_timeout=10,        # 타임아웃 감소
    pool_recycle=3600,      # 커넥션 재활용 시간
    pool_pre_ping=True,     # 연결 상태 확인
    echo=False
)

# 동기 엔진 설정 수정
engine = create_engine(
    SYNC_SQLALCHEMY_DATABASE_URL,
    pool_size=20,           # 기본 풀 크기 증가
    max_overflow=30,        # 최대 초과 연결 수 증가
    pool_timeout=10,        # 타임아웃 감소
    pool_recycle=3600,      # 커넥션 재활용 시간
    pool_pre_ping=True,     # 연결 상태 확인
    echo=False
)

async def get_async_db():
    retry_count = 0
    while retry_count <= 3:  # 재시도 횟수 감소
        async with AsyncSession(bind=async_engine) as db:
            try:
                yield db
                break
            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"Async database error: {e}, retrying...")
                await asyncio.sleep(0.5)  # 재시도 대기 시간 단축
                retry_count += 1
    if retry_count > 3:
        logger.error("Maximum retry attempts reached, failing.")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    retry_count = 0
    while retry_count <= 3:  # 재시도 횟수 감소
        db = SessionLocal()
        try:
            yield db
            break
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error: {e}, retrying...")
            time.sleep(0.5)  # 재시도 대기 시간 단축
            retry_count += 1
        finally:
            db.close()
    if retry_count > 3:
        logger.error("Maximum retry attempts reached, failing.")


class AsyncTransactionManager:
    def __init__(self, async_db: AsyncSession):
        self.async_db = async_db

    @asynccontextmanager
    async def transaction(self):
        try:
            await self.async_db.begin()
            yield
            await self.async_db.commit()
        except Exception as e:
            await self.async_db.rollback()
            raise e


def async_transactional(method):
    @wraps(method)
    async def wrapper(self, *args, **kwargs):
        async with self.transaction_manager.transaction():
            return await method(self, *args, **kwargs)

    return wrapper


async def get_async_redis_client():
    try:
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_password = os.getenv('REDIS_PASSWORD', '')

        redis_url = f'redis://:{redis_password}@{redis_host}:{redis_port}'
        redis_client = aioredis.from_url(redis_url, decode_responses=True)

        # Test the connection
        await redis_client.ping()

        return redis_client
    except aioredis.ConnectionError as e:
        raise ExceptionResponse(message=f"비동기 Redis 연결 간 에러가 발생 했습니다.: {str(e)}", error_code="R0000")


def get_sync_redis_client():
    try:
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_password = os.getenv('REDIS_PASSWORD', '')

        redis_client = redis.StrictRedis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            db=0,
            decode_responses=True
        )

        # Test the connection
        redis_client.ping()

        return redis_client
    except redis.ConnectionError as e:
        raise ExceptionResponse(message=f"동기 Redis 연결 간 에러가 발생 했습니다.: {str(e)}", error_code="R0000")
