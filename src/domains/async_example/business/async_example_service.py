import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.async_example.business.schemas import AsyncExampleSchema, ASyncExampleSchemaList
from src.domains.async_example.constants import BLErrorCode
from src.domains.async_example.database import async_example_crud
from src.domains.async_example.presentation.schemas import CreateAsyncExample, UpdateAsyncExampleV1, \
    UpdateAsyncExampleV2
from src.exceptions import DLException, BLException

logger = logging.getLogger(__name__)


async def create_async_example_with_no_user(db: AsyncSession, example_create: CreateAsyncExample):
    try:
        async_example: AsyncExampleSchema = AsyncExampleSchema(
            name=example_create.name,
            description=example_create.description
        )

        created_async_example: AsyncExampleSchema = await async_example_crud \
            .create_async_example(db, async_example)
        return created_async_example

    except ExceptionResponse as er:
        logger.error(f"Failed to create SyncExample: {er.message}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error while creating SyncExample: {str(e)}")
        raise BLException(detail="An unexpected error occurred during the creation process")


async def read_async_example(db: AsyncSession, async_example_id: int) -> AsyncExampleSchema:
    try:
        async_example: AsyncExampleSchema = await async_example_crud \
            .read_fetch_async_example_with_user(db, async_example_id)
        return async_example

    except DLException as de:
        logger.error(f"Failed to retrieve AsyncExample: {de.detail}")
        raise BLException(code=de.code, detail=de.detail)

    except Exception as e:
        logger.error(f"Unexpected error while retrieving AsyncExample: {str(e)}")
        raise BLException(detail="An unexpected error occurred while retrieving AsyncExample")


async def get_async_example_list(db: AsyncSession, keyword: str, limit: int = 10,
                                 offset: int = 0) -> ASyncExampleSchemaList:
    try:
        async_example_list: ASyncExampleSchemaList \
            = await async_example_crud.read_async_example_list(db, limit=limit, offset=offset, keyword=keyword)
    except DLException as de:
        logger.error(f"Error in retrieving AsyncExamples: {de.detail}")
        raise BLException(code=de.code, detail=de.detail)

    except Exception as e:
        logger.error(f"Unexpected error while fetching AsyncExamples: {e}")
        raise BLException(code=BLErrorCode.UNKNOWN_ERROR,
                          detail=f"An unexpected error occurred while fetching AsyncExamples.: {e}")

    return async_example_list


async def fetch_async_example_with_user_v1(db: AsyncSession, async_example_id: int,
                                           request: UpdateAsyncExampleV1) -> AsyncExampleSchema:
    try:
        async_example: AsyncExampleSchema = await async_example_crud \
            .update_async_example(db, async_example_id, request)
        return async_example

    except DLException as de:
        logger.error(f"Failed to retrieve AsyncExample: {de.detail}")
        raise BLException(code=de.code, detail=de.detail)

    except Exception as e:
        logger.error(f"Unexpected error while retrieving AsyncExample: {str(e)}")
        raise BLException(code=BLErrorCode.UNKNOWN_ERROR,
                          detail="An unexpected error occurred while retrieving AsyncExample")


async def fetch_async_example_with_user_v2(db: AsyncSession, request: UpdateAsyncExampleV2) -> AsyncExampleSchema:
    try:
        example_id = request.async_example_id
        async_example: AsyncExampleSchema = await async_example_crud \
            .update_async_example(db, example_id, request)
        return async_example

    except DLException as de:
        logger.error(f"Failed to retrieve AsyncExample: {de.detail}")
        raise BLException(code=de.code, detail=de.detail)

    except Exception as e:
        logger.error(f"Unexpected error while retrieving AsyncExample: {str(e)}")
        raise BLException(code=BLErrorCode.UNKNOWN_ERROR,
                          detail=f"An unexpected error occurred while retrieving AsyncExample: {e}")


async def delete_async_example(db, example_id: int):
    try:
        await async_example_crud.delete_async_example(db, example_id)
        logger.info(f"Deleted AsyncExample with ID {example_id}")

    except DLException as de:
        logger.error(f"Failed to delete AsyncExample: {de.detail}")
        raise BLException(code=de.code, detail=de.detail)

    except Exception as e:
        logger.error(f"Unexpected error while deleting AsyncExample: {str(e)}")
        raise BLException(code=BLErrorCode.UNKNOWN_ERROR,
                          detail="An unexpected error occurred while deleting AsyncExample.")
