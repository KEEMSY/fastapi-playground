import logging
from typing import Union

from pydantic import ValidationError
from sqlalchemy import select, or_, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domains.async_example.business.schemas import AsyncExampleSchema, ASyncExampleSchemaList
from src.domains.async_example.constants import DLErrorCode, ErrorCode
from src.domains.async_example.database.models import AsyncExample
from src.domains.async_example.presentation.schemas import CreateAsyncExample, UpdateAsyncExampleV1, \
    UpdateAsyncExampleV2
from src.exceptions import DLException, handle_exceptions

logger = logging.getLogger(__name__)


@handle_exceptions
async def create_async_example(db: AsyncSession, async_example: AsyncExampleSchema) -> AsyncExampleSchema:
    async_example = AsyncExample(
        name=async_example.name,
        description=async_example.description
    )
    db.add(async_example)
    await db.commit()
    await db.refresh(async_example)

    return AsyncExampleSchema.model_validate(async_example)


async def read_async_example(db: AsyncSession, async_example_id: int) -> AsyncExampleSchema:
    """
    단순한 조회로, 특정 ID에 대한 직접 조회만 수행한다. 만약 연관관계가 있는 경우 다른 방법(read_fetch_async_example_with_user)을 사용한다.
    """
    result = await db.get(AsyncExample, async_example_id)
    if result is None:
        logger.error(f"No AsyncExample found with id {async_example_id}")
        raise DLException(detail=f"No AsyncExample found with id {async_example_id}")

    try:
        result_into_schema = AsyncExampleSchema.model_validate(result)
        logger.info(f"Retrieved AsyncExample {async_example_id}")
        return result_into_schema
    except Exception as e:
        logger.error(f"Error while retrieving AsyncExample {async_example_id}")
        raise DLException(code="D0000", detail=f"Error while retrieving AsyncExample {async_example_id}")


async def read_async_example_list(db, limit, offset, keyword):
    try:
        # 조건을 설정합니다. 기본적으로 모든 데이터를 대상으로 합니다.
        search_condition = True  # 모든 데이터를 반환하는 기본 조건

        if keyword:
            # 키워드가 주어진 경우 검색 조건을 추가합니다.
            search_condition = or_(
                AsyncExample.name.ilike(f'%{keyword}%'),
                AsyncExample.description.ilike(f'%{keyword}%')
            )

        # 검색 조건을 기반으로 쿼리를 구성합니다.
        query = select(AsyncExample).where(search_condition).order_by(AsyncExample.create_date.desc())

        # 쿼리 실행
        results = await db.execute(query.offset(offset).limit(limit))
        async_example_list = results.scalars().all()
        async_example_schema_list = [AsyncExampleSchema.model_validate(async_example) for async_example in
                                     async_example_list]

        # 전체 개수를 계산하는 쿼리를 생성합니다.
        total_count_query = select(func.count()).select_from(
            select(AsyncExample).where(search_condition).subquery()
        )

        # 전체 개수 실행
        total_count = await db.execute(total_count_query)
        total = total_count.scalar_one()

        return ASyncExampleSchemaList(total=total, example_list=async_example_schema_list)

    except ValidationError as ve:
        logger.error(f"Validation error while retrieving ASyncExample: {ve}")
        raise DLException(code=DLErrorCode.VALIDATION_ERROR, detail="Validation error on data input.")

    except SQLAlchemyError as e:
        logger.error(f"Database error while retrieving SyncExample: {e}")
        raise DLException(code=DLErrorCode.DATABASE_ERROR,
                          detail="Database error occurred while retrieving ASyncExample.")

    except Exception as e:
        logger.error(f"Unexpected error while retrieving SyncExample: {e}")
        raise DLException(code=DLErrorCode.UNKNOWN_ERROR,
                          detail=f"An unexpected error occurred while retrieving ASyncExample.: {e}")


async def read_fetch_async_example_with_user(db: AsyncSession, async_example_id: int) -> AsyncExampleSchema:
    """
    연관 관계가 있는 경우, 한번에 모두 가져오는 쿼리를 발생시킨다.
    """
    try:
        stmt = (
            select(AsyncExample)
            .options(selectinload(AsyncExample.user))
            .where(AsyncExample.id == async_example_id)
        )
        result = await db.execute(stmt)
        async_example = result.scalars().first()

        if async_example is None:
            logger.error(f"No AsyncExample found with id {async_example_id}")
            raise DLException(code=ErrorCode.NOT_FOUND, detail=f"No AsyncExample found with id {async_example_id}")

        return AsyncExampleSchema.model_validate(async_example)

    except DLException as de:
        logger.error(f"Failed to retrieve AsyncExample {async_example_id}: {de.detail}")
        raise DLException(code=de.code, detail=de.detail)

    except Exception as e:
        logger.error(f"Error while retrieving AsyncExample {async_example_id}: {str(e)}")
        raise DLException(detail=f"Error while retrieving AsyncExample {async_example_id}")


async def update_async_example(db: AsyncSession, async_example_id: int,
                               request: Union[UpdateAsyncExampleV1, UpdateAsyncExampleV2]) -> AsyncExampleSchema:
    try:
        async_example = await db.get(AsyncExample, async_example_id)
        if async_example is None:
            logger.error(f"No AsyncExample found with id {async_example_id}")
            raise DLException(code=ErrorCode.NOT_FOUND, detail=f"No AsyncExample found with id {async_example_id}")

        async_example.name = request.name
        async_example.description = request.description
        await db.commit()
        await db.refresh(async_example)

        return AsyncExampleSchema.model_validate(async_example)

    except DLException as de:
        logger.error(f"Failed to update AsyncExample: {de.detail}")
        raise

    except ValidationError as ve:
        logger.error(f"Validation error while updating SyncExample: {ve}")
        await db.rollback()
        raise DLException(code=ErrorCode.VALIDATION_ERROR, detail="Validation error on data input.")

    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error while updating SyncExample: {e}")
        raise DLException(code=ErrorCode.DATABASE_ERROR, detail="Database error occurred while updating SyncExample.")

    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while updating SyncExample: {e}")
        raise DLException(code=ErrorCode.UNKNOWN_ERROR,
                          detail="An unexpected error occurred while updating SyncExample.")


async def delete_async_example(db: AsyncSession, async_example_id: int):
    async_example = await db.get(AsyncExample, async_example_id)
    if async_example is None:
        logger.error(f"No AsyncExample found with id {async_example_id}")
        raise DLException(code=ErrorCode.NOT_FOUND, detail=f"No AsyncExample found with id {async_example_id}")
    try:
        await db.delete(async_example)
        await db.commit()
        logger.info(f"Deleted AsyncExample with ID {async_example_id}")

    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error while deleting ASyncExample: {e}")
        raise DLException(code=DLErrorCode.DATABASE_ERROR, detail="Database error occurred while deleting SyncExample.")

    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while deleting SyncExample: {e}")
        raise DLException(code=DLErrorCode.UNKNOWN_ERROR,
                          detail="An unexpected error occurred while deleting ASyncExample.")
