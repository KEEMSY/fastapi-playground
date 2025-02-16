from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.domains.sync_example.business import service as example_service
from src.domains.sync_example.business.schemas import SyncExampleListSchema
from src.domains.sync_example.presentation.schemas import SyncExampleListResponse

router = APIRouter(
    prefix="/api/asyncPL/syncDL",
)


@router.get("/example/list",
            response_model=SyncExampleListResponse,
            tags=["sync vs async"],
            summary="asyncPL_syncDL 테스트 API")
async def read_sync_example_list(db: Session = Depends(get_db), limit: int = 10, offset: int = 0):
    sync_example_list_schema: SyncExampleListSchema = example_service.get_sync_example_list(db, limit=limit,
                                                                                            offset=limit * offset)

    return SyncExampleListResponse(
        total=sync_example_list_schema.total,
        example_list=sync_example_list_schema.example_list
    )
