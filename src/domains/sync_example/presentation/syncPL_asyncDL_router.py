from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.domains.async_example.business import async_example_service
from src.domains.async_example.business.schemas import ASyncExampleSchemaList
from src.domains.async_example.presentation.schemas import ASyncExampleListResponse
from src.exceptions import BLException, PLException

router = APIRouter(
    prefix="/api/syncPL/asyncDL",
)

"""
문법 오류로 불가능
"""
# @router.get("/async/example/list", response_model=ASyncExampleListResponse, tags=["sync vs async"])
# def get_async_example_list(keyword: Optional[str] = None, size: int = 10, page: int = 0,
#                            db: AsyncSession = Depends(get_async_db)):
#     try:
#         offset = size * page
#         async_example_schema_list: ASyncExampleSchemaList = await async_example_service.get_async_example_list(db=db,
#                                                                                                                keyword=keyword,
#                                                                                                                limit=size,
#                                                                                                                offset=offset)
#         return ASyncExampleListResponse.model_validate(async_example_schema_list)
#     except BLException as e:
#         raise PLException(status_code=400, detail=e.detail, code=e.code)
#
#     except Exception as e:
#         raise PLException(status_code=500, detail=str(e))
