import logging
from typing import Union

from pydantic import ValidationError
from sqlalchemy import select, or_, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domains.async_example.business.schemas import AsyncExampleSchema
from src.domains.async_example.constants import DLErrorCode
from src.domains.async_example.database.models import AsyncExample
from src.domains.async_example.presentation.schemas import CreateAsyncExample, UpdateAsyncExampleV1, \
    UpdateAsyncExampleV2, ASyncExampleListSchema
from src.exceptions import DLException

logger = logging.getLogger(__name__)


async def create_async_example_with_no_user(db: AsyncSession, example_create: CreateAsyncExample):
    try:
        async_example = AsyncExample(
            name=example_create.name,
            description=example_create.description
        )
        db.add(async_example)
        await db.commit()
        await db.refresh(async_example)

        return AsyncExampleSchema.model_validate(async_example)

    except ValidationError as ve:
        logger.error(f"Validation error while creating SyncExample: {ve}")
        await db.rollback()
        raise DLException(code="D0001", detail="Validation error on data input.")

    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error while creating SyncExample: {e}")
        raise DLException(detail="Database error occurred while creating SyncExample.")

    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while creating SyncExample: {e}")
        raise DLException(detail="An unexpected error occurred while creating SyncExample.")


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
        query = select(AsyncExample).where(
            or_(
                AsyncExample.name.ilike(f'%{keyword}%'),
                AsyncExample.description.ilike(f'%{keyword}%')
            )
        ).order_by(AsyncExample.create_date.desc())

        results = await db.execute(query.offset(offset).limit(limit))
        async_example_list = results.scalars().all()
        async_example_schema_list = [AsyncExampleSchema.model_validate(async_example) for async_example in
                                     async_example_list]

        total_count = await db.execute(
            select(func.count()).select_from(
                select(AsyncExample).where(
                    or_(
                        AsyncExample.name.ilike(f'%{keyword}%'),
                        AsyncExample.description.ilike(f'%{keyword}%')
                    )
                ).subquery()
            )
        )
        total = total_count.scalar_one()

        return ASyncExampleListSchema(total=total, example_list=async_example_schema_list)

    except ValidationError as ve:
        logger.error(f"Validation error while retrieving SyncExample: {ve}")
        raise DLException(code=DLErrorCode.VALIDATION_ERROR, detail="Validation error on data input.")

    except SQLAlchemyError as e:
        logger.error(f"Database error while retrieving SyncExample: {e}")
        raise DLException(code=DLErrorCode.DATABASE_ERROR,
                          detail="Database error occurred while retrieving SyncExample.")

    except Exception as e:
        logger.error(f"Unexpected error while retrieving SyncExample: {e}")
        raise DLException(code=DLErrorCode.UNKNOWN_ERROR,
                          detail="An unexpected error occurred while retrieving SyncExample.")


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
            raise DLException(detail=f"No AsyncExample found with id {async_example_id}")

        return AsyncExampleSchema.model_validate(async_example)

    except Exception as e:
        logger.error(f"Error while retrieving AsyncExample {async_example_id}: {str(e)}")
        raise DLException(detail=f"Error while retrieving AsyncExample {async_example_id}")


async def update_async_example(db: AsyncSession, async_example_id: int,
                               request: Union[UpdateAsyncExampleV1, UpdateAsyncExampleV2]) -> AsyncExampleSchema:
    try:
        async_example = await db.get(AsyncExample, async_example_id)
        if async_example is None:
            logger.error(f"No AsyncExample found with id {async_example_id}")
            raise DLException(code=DLErrorCode.NOT_FOUND, detail=f"No AsyncExample found with id {async_example_id}")

        async_example.name = request.name
        async_example.description = request.description
        await db.commit()
        await db.refresh(async_example)

        return AsyncExampleSchema.model_validate(async_example)

    except ValidationError as ve:
        logger.error(f"Validation error while updating SyncExample: {ve}")
        await db.rollback()
        raise DLException(code=DLErrorCode.VALIDATION_ERROR, detail="Validation error on data input.")

    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error while updating SyncExample: {e}")
        raise DLException(code=DLErrorCode.DATABASE_ERROR, detail="Database error occurred while updating SyncExample.")

    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while updating SyncExample: {e}")
        raise DLException(code=DLErrorCode.UNKNOWN_ERROR,
                          detail="An unexpected error occurred while updating SyncExample.")


async def delete_async_example(db: AsyncSession, async_example_id: int):
    async_example = await db.get(AsyncExample, async_example_id)
    if async_example is None:
        logger.error(f"No AsyncExample found with id {async_example_id}")
        raise DLException(code=DLErrorCode.NOT_FOUND, detail=f"No AsyncExample found with id {async_example_id}")
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
