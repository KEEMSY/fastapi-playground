from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.database.database import get_async_db
from src.domains.async_example.business import async_example_service
from src.domains.async_example.business.schemas import ASyncExampleSchemaList
from src.domains.async_example.constants import ErrorCode
from src.domains.async_example.presentation.schemas import CreateAsyncExample, AsyncExampleResponse, \
    UpdateAsyncExampleV2, UpdateAsyncExampleV1, ReadAsyncExample, ASyncExampleListResponse
from src.exceptions import PLException, BLException
from src.utils import Logging

router = APIRouter(
    prefix="/api/async/no-login",
)

logger = Logging.__call__().get_logger(name=__name__, path="no_login_router.py", isThread=True)


@router.post("/example",
             response_model=AsyncExampleResponse,
             status_code=status.HTTP_201_CREATED,
             tags=["with_no_login_async_example"],
             summary="AsyncExample 생성")
async def save_async_example(request: CreateAsyncExample, db: AsyncSession = Depends(get_async_db)):
    try:
        saved_async_example = await async_example_service.create_async_example_with_no_user(
            db=db, example_create=request
        )
        logger.info(f"AsyncExample created: {saved_async_example}")
        return AsyncExampleResponse.model_validate(saved_async_example)
    except BLException as e:
        logger.error(f"Error creating AsyncExample: {e}")
        raise PLException(status_code=400, detail=e.detail, code=e.code)

    except Exception as e:
        logger.error(f"UnExpected Error is occurred when creating AsyncExample: {e}")
        raise PLException(status_code=500, detail=str(e))


@router.get("/example/list",
            response_model=ASyncExampleListResponse,
            status_code=status.HTTP_200_OK,
            tags=["with_no_login_async_example"],
            summary="AsyncExample 리스트 조회")
async def get_async_example_list(keyword: Optional[str] = None, size: int = 10, page: int = 0,
                                 db: AsyncSession = Depends(get_async_db)):
    try:
        offset = size * page
        async_example_schema_list: ASyncExampleSchemaList = await async_example_service.get_async_example_list(db=db,
                                                                                                               keyword=keyword,
                                                                                                               limit=size,
                                                                                                               offset=offset)
        logger.info(f"AsyncExample list: {async_example_schema_list}")
        return ASyncExampleListResponse.model_validate(async_example_schema_list)
    except BLException as e:
        logger.error(f"Error getting AsyncExample list: {e}")
        raise PLException(status_code=400, detail=e.detail, code=e.code)

    except Exception as e:
        raise PLException(status_code=500, detail=str(e))


@router.get("/example/{example_id}",
            response_model=AsyncExampleResponse,
            status_code=status.HTTP_200_OK,
            tags=["with_no_login_async_example"],
            summary="AsyncExample 단일 조회")
async def get_async_example(example_id: int, db: AsyncSession = Depends(get_async_db)):
    try:
        async_example = await async_example_service.read_async_example(db, example_id)
        return AsyncExampleResponse.model_validate(async_example)
    except BLException as e:
        if e.code == ErrorCode.NOT_FOUND:
            logger.error(f"AsyncExample not found: {e}")
            raise PLException(status_code=404, detail=e.detail, code=e.code)

        logger.error(f"Error getting AsyncExample: {e}")
        raise PLException(status_code=400, detail=e.detail, code=e.code)

    except Exception as e:
        logger.error(f"UnExpected Error is occurred when getting AsyncExample: {e}")
        raise PLException(status_code=500, detail=str(e))


@router.put("/example",
            response_model=AsyncExampleResponse,
            status_code=status.HTTP_200_OK,
            tags=["with_no_login_async_example"],
            summary="AsyncExample 수정: body에 async_example_id를 넣어주세요")
async def update_async_example(request: UpdateAsyncExampleV2,
                               db: AsyncSession = Depends(get_async_db)):
    try:
        updated_async_example = await async_example_service.fetch_async_example_with_user_v2(db, request)
        return AsyncExampleResponse.model_validate(updated_async_example)
    except BLException as e:
        if e.code == ErrorCode.NOT_FOUND:
            logger.error(f"AsyncExample not found: {e}")
            raise PLException(status_code=404, detail=e.detail, code=e.code)

        logger.error(f"Error updating AsyncExample: {e}")
        raise PLException(status_code=400, detail=e.detail, code=e.code)

    except Exception as e:
        logger.error(f"UnExpected Error is occurred when updating AsyncExample: {e}")
        raise PLException(status_code=500, detail=str(e))


@router.put("/example/fetch/{example_id}",
            response_model=AsyncExampleResponse,
            status_code=status.HTTP_200_OK,
            tags=["with_no_login_async_example"],
            summary="AsyncExample 수정: path parameter에 async_example_id를 넣어주세요(사용하지 않음)")
async def update_async_example(request: UpdateAsyncExampleV1, example_id: int,
                               db: AsyncSession = Depends(get_async_db)
                               ):
    try:
        async_example = await async_example_service.fetch_async_example_with_user_v1(db=db, async_example_id=example_id,
                                                                                     request=request)
        return AsyncExampleResponse.model_validate(async_example)
    except BLException as e:
        raise PLException(status_code=400, detail=e.detail, code=e.code)

    except Exception as e:
        raise PLException(status_code=500, detail=str(e))


@router.delete("/example/{example_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               tags=["with_no_login_async_example"],
               summary="AsyncExample 삭제")
async def delete_async_example(example_id: int, db: AsyncSession = Depends(get_async_db)):
    try:
        await async_example_service.delete_async_example(db, example_id)
    except BLException as e:
        if e.code == ErrorCode.NOT_FOUND:
            logger.error(f"AsyncExample not found: {e}")
            raise PLException(status_code=404, detail=e.detail, code=e.code)

        logger.error(f"Error deleting AsyncExample: {e}")
        raise PLException(status_code=400, detail=e.detail, code=e.code)

    except Exception as e:
        logger.error(f"UnExpected Error is occurred when deleting AsyncExample: {e}")
        raise PLException(status_code=500, detail=str(e))
