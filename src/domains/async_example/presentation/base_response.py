from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.database.database import get_async_db
from src.domains.async_example.business import async_example_service
from src.domains.async_example.business.schemas import ASyncExampleSchemaList
from src.domains.async_example.constants import ErrorCode
from src.domains.async_example.presentation.schemas import ASyncExampleListResponse, AsyncExampleResponse
from src.domains.sync_example.presentation.schemas import BaseResponse
from src.exceptions import BLException, PLException
from src.utils import Logging

router = APIRouter(
    prefix="/api/base-response/async",
)
logger = Logging.__call__().get_logger(name=__name__, path="no_login_router.py", isThread=True)


@router.get("/example/list",
            response_model=BaseResponse[ASyncExampleListResponse],
            status_code=status.HTTP_200_OK,
            tags=["base_response_async_example"],
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
        return BaseResponse(data=ASyncExampleListResponse.model_validate(async_example_schema_list))
    except BLException as e:
        logger.error(f"Error getting AsyncExample list: {e}")
        raise PLException(status_code=400, detail=e.detail, code=e.code)

    except Exception as e:
        raise PLException(status_code=500, detail=str(e))


@router.get("/example/{example_id}",
            response_model=BaseResponse[AsyncExampleResponse],
            status_code=status.HTTP_200_OK,
            tags=["base_response_async_example"],
            summary="AsyncExample 단일 조회")
async def get_async_example(example_id: int, db: AsyncSession = Depends(get_async_db)):
    try:
        async_example = await async_example_service.read_async_example(db, example_id)
        return BaseResponse(data=AsyncExampleResponse.model_validate(async_example))
    except BLException as e:
        if e.code == ErrorCode.NOT_FOUND:
            logger.error(f"AsyncExample not found: {e}")
            raise PLException(status_code=404, detail=e.detail, code=e.code)

        logger.error(f"Error getting AsyncExample: {e}")
        raise PLException(status_code=400, detail=e.detail, code=e.code)

    except Exception as e:
        logger.error(f"UnExpected Error is occurred when getting AsyncExample: {e}")
        raise PLException(status_code=500, detail=str(e))
