import asyncio
import logging
import time

from sqlalchemy import create_engine, MetaData
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import SYNC_SQLALCHEMY_DATABASE_URL, ASYNC_SQLALCHEMY_DATABASE_URL

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

engine = create_engine(SYNC_SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


async_engine = create_async_engine(ASYNC_SQLALCHEMY_DATABASE_URL, echo=True)

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

async def get_async_db():
    retry_count = 0
    while retry_count <= 5:
        async with AsyncSession(bind=async_engine) as db:
            try:
                yield db
                break  # If the session was successful, exit the loop
            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"Async database error: {e}, retrying...")
                await asyncio.sleep(1.5)  # Wait before retrying
                retry_count += 1
    if retry_count > 5:
        logger.error("Maximum retry attempts reached, failing.")


def get_db():
    retry_count = 0
    while retry_count <= 5:
        db = SessionLocal()
        try:
            yield db
            break  # If the session was successful, exit the loop
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error: {e}, retrying...")
            time.sleep(1.5)  # Wait before retrying
            retry_count += 1
        finally:
            db.close()
    if retry_count > 5:
        logger.error("Maximum retry attempts reached, failing.")
