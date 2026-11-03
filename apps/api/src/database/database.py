import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from functools import wraps
import random

import aioredis
import redis
from sqlalchemy import create_engine, MetaData, text
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

# SQLAlchemy 연결 풀 설정 (환경 변수에서 로드, 기본값 설정)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 20))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 30))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", 10))

# Primary Async DB 연결 설정
async_engine_primary = create_async_engine(
    ASYNC_SQLALCHEMY_DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False
)

# Replica Async DB 연결 설정
ASYNC_SQLALCHEMY_REPLICA_URL = ASYNC_SQLALCHEMY_DATABASE_URL.replace('db:', 'db_replica:').replace(':5432', ':5432')
async_engine_replica = create_async_engine(
    ASYNC_SQLALCHEMY_REPLICA_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False
)

# Sync Primary 엔진 설정
engine = create_engine(
    SYNC_SQLALCHEMY_DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False
)

# Sync Replica 엔진 설정
SYNC_SQLALCHEMY_REPLICA_URL = SYNC_SQLALCHEMY_DATABASE_URL.replace(':5432', ':15433')
engine_replica = create_engine(
    SYNC_SQLALCHEMY_REPLICA_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False
)

# Primary Async 세션 팩토리
AsyncSessionPrimary = sessionmaker(
    async_engine_primary,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Replica Async 세션 팩토리
AsyncSessionReplica = sessionmaker(
    async_engine_replica,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_read_engine():
    """읽기 작업을 위한 엔진 선택 (Primary or Replica)"""
    engines = [async_engine_primary, async_engine_replica]
    return random.choice(engines)

def get_sync_read_engine():
    """동기 읽기 작업을 위한 엔진 선택 (Primary or Replica)"""
    engines = [engine] + [engine_replica]
    return random.choice(engines)

async def get_async_read_db():
    """읽기 전용 DB 연결 - Primary/Replica 로드밸런싱"""
    engine = await get_read_engine()
    async with AsyncSession(bind=engine) as db:
        try:
            # 데이터베이스 연결 정보 조회
            result = await db.execute(text("SELECT current_database(), current_user, inet_server_addr(), inet_server_port()"))
            db_info = result.fetchone()
            logger.info(f"Database Connection Info - Host: {db_info[2]}, Port: {db_info[3]}, "
                       f"Database: {db_info[0]}, User: {db_info[1]}")
            
            yield db
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Async read database error: {e}")
            raise

def get_read_db():
    """동기 읽기 전용 DB 연결 - Primary/Replica 로드밸런싱"""
    retry_count = 0
    while retry_count <= 3:
        engine = get_sync_read_engine()
        db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
        try:
            yield db
            break
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Read database error: {e}, retrying...")
            time.sleep(0.5)
            retry_count += 1
        finally:
            db.close()
    if retry_count > 3:
        logger.error("Maximum retry attempts reached for read operation, failing.")

# 동기 세션 설정
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocalReplica = sessionmaker(autocommit=False, autoflush=False, bind=engine_replica)

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

async def get_async_db():
    """쓰기 전용 DB 연결 - Primary 사용"""
    async with AsyncSessionPrimary() as db:
        try:
            # 데이터베이스 연결 정보 조회
            result = await db.execute(text("SELECT current_database(), current_user, inet_server_addr(), inet_server_port()"))
            db_info = result.fetchone()
            logger.info(f"Primary Database Connection Info - Host: {db_info[2]}, Port: {db_info[3]}, "
                       f"Database: {db_info[0]}, User: {db_info[1]}")
            
            yield db
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Primary database error: {e}")
            raise

# 기존 get_db()는 쓰기 전용으로 사용
def get_db():
    """Primary DB 연결용 (쓰기 전용)"""
    retry_count = 0
    while retry_count <= 3:
        db = SessionLocal()
        try:
            yield db
            break
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Write database error: {e}, retrying...")
            time.sleep(0.5)
            retry_count += 1
        finally:
            db.close()
    if retry_count > 3:
        logger.error("Maximum retry attempts reached for write operation, failing.")
