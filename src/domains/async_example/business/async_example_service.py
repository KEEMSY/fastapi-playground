import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.async_example.business.schemas import AsyncExampleSchema
from src.domains.async_example.database import async_example_crud
from src.domains.async_example.presentation.schemas import CreateAsyncExample
from src.exceptions import DLException, BLException

logger = logging.getLogger(__name__)


async def create_async_example_with_no_user(db: AsyncSession, example_create: CreateAsyncExample):
    try:
        created_async_example: AsyncExampleSchema = await async_example_crud \
            .create_async_example_with_no_user(db, example_create)
        return created_async_example

    except DLException as de:
        logger.error(f"Failed to create SyncExample: {de.detail}")
        raise BLException(code=de.code, detail=de.detail)

    except Exception as e:
        logger.error(f"Unexpected error while creating SyncExample: {str(e)}")
        raise BLException(detail="An unexpected error occurred during the creation process")
