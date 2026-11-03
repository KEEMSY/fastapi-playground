import logging

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependecies import get_async_example_repository
from src.domains.async_example.business.ports.async_example_repository import AsyncExampleRepository
from src.domains.async_example.business.schemas import AsyncExampleSchema, ASyncExampleSchemaList
from src.domains.async_example.constants import BLErrorCode
from src.domains.async_example.database import async_example_crud
from src.domains.async_example.presentation.schemas import CreateAsyncExample, UpdateAsyncExampleV1, \
    UpdateAsyncExampleV2
from src.exceptions import DLException, BLException, ExceptionResponse

logger = logging.getLogger(__name__)

"""
[ 해야할 일 ]

1. Port 추가(완료)
현재 BL -> DL로 향하는 의존성을 뒤집기 위해 Port(인터페이스)를 추가한다.
- 추가된 Port는 BL 내 Service에서 사용한다.
- Port는 Input/Output 두종류로 나뉘지만, 가정 기초적으로 Ouput(DB 등)를 먼저 작성한다.
- BL에서는 DB Port를 호출하여 유스케이스에 필요한 데이터 상호작용을 진행한다. 

2. Port를 사용하도록 개선
"""


class AsyncExampleService:
    def __init__(self,
                 async_db: AsyncSession,
                 async_repository: AsyncExampleRepository = Depends(get_async_example_repository)):
        self.async_db = async_db
        self.async_repository = async_repository

    async def create_async_example_with_no_user(self, example_create: CreateAsyncExample):
        try:
            async_example: AsyncExampleSchema = AsyncExampleSchema(
                name=example_create.name,
                description=example_create.description
            )
            created_async_example: AsyncExampleSchema = await async_example_crud \
                .create_async_example(self.async_db, async_example)
            return created_async_example

        except ExceptionResponse as er:
            logger.error(f"Failed to create SyncExample: {er.message}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error while creating SyncExample: {str(e)}")
            raise BLException(detail="An unexpected error occurred during the creation process")

    async def get_async_example(self, async_example_id: int) -> AsyncExampleSchema:
        try:
            async_example: AsyncExampleSchema = await self.async_repository.get_async_example(async_example_id)
            return async_example

        except ExceptionResponse as er:
            logger.error(f"Failed to retrieve AsyncExample: {er.message}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error while retrieving AsyncExample: {str(e)}")
            raise BLException(detail="An unexpected error occurred while retrieving AsyncExample")

    async def get_async_example_list(self, keyword: str, limit: int = 10,
                                     offset: int = 0) -> ASyncExampleSchemaList:
        try:
            async_example_list: ASyncExampleSchemaList \
                = await async_example_crud.read_async_example_list(self.async_db, limit=limit, offset=offset,
                                                                   keyword=keyword)
        except ExceptionResponse as er:
            logger.error(f"Error in retrieving AsyncExamples: {er.message}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error while fetching AsyncExamples: {e}")
            raise BLException(code=BLErrorCode.UNKNOWN_ERROR,
                              detail=f"An unexpected error occurred while fetching AsyncExamples.: {e}")

        return async_example_list

    async def fetch_async_example_with_user_v2(self, request: UpdateAsyncExampleV2) -> AsyncExampleSchema:
        try:
            async_example_schema: AsyncExampleSchema = AsyncExampleSchema(
                name=request.name,
                description=request.description,
                id=request.async_example_id,
            )

            async_example: AsyncExampleSchema = await async_example_crud \
                .update_async_example_v2(self.async_db, async_example_schema)
            return async_example

        except ExceptionResponse as er:
            logger.error(f"Failed to retrieve AsyncExample: {er.message}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error while retrieving AsyncExample: {str(e)}")
            raise BLException(code=BLErrorCode.UNKNOWN_ERROR,
                              detail=f"An unexpected error occurred while retrieving AsyncExample: {e}")

    async def delete_async_example(self, example_id: int):
        try:
            await async_example_crud.delete_async_example(self.async_db, example_id)
            logger.info(f"Deleted AsyncExample with ID {example_id}")

        except ExceptionResponse as er:
            logger.error(f"Failed to delete AsyncExample: {er.message}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error while deleting AsyncExample: {str(e)}")
            raise BLException(code=BLErrorCode.UNKNOWN_ERROR,
                              detail="An unexpected error occurred while deleting AsyncExample.")


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

    except ExceptionResponse as er:
        logger.error(f"Failed to retrieve AsyncExample: {er.message}")
        raise

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
            .update_async_example_v1(db, async_example_id, request)
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
        async_example_schema: AsyncExampleSchema = AsyncExampleSchema(
            name=request.name,
            description=request.description,
            id=request.async_example_id,
        )

        async_example: AsyncExampleSchema = await async_example_crud \
            .update_async_example_v2(db, async_example_schema)
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

    except ExceptionResponse as er:
        logger.error(f"Failed to delete AsyncExample: {er.message}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error while deleting AsyncExample: {str(e)}")
        raise BLException(code=BLErrorCode.UNKNOWN_ERROR,
                          detail="An unexpected error occurred while deleting AsyncExample.")
