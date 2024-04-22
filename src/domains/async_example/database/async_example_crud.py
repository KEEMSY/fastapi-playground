import logging

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.async_example.business.schemas import AsyncExampleSchema
from src.domains.async_example.database.models import AsyncExample
from src.domains.async_example.presentation.schemas import CreateAsyncExample
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
