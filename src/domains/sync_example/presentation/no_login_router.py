from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette import status
from starlette.exceptions import HTTPException

from src.database import get_db
from src.domains.sync_example.bussiness import service as example_service
from src.domains.sync_example.bussiness.schemas import SyncExampleSchema
from src.domains.sync_example.presentation.schemas import SyncExampleResponse, CreateSyncExample

router = APIRouter(
    prefix="/api/sync/no-login",
)


@router.get("/sync/example/{example_id}", response_model=SyncExampleResponse, tags=["with_no_login_sync_example"])
def read_sync_example(example_id: int, db: Session = Depends(get_db)):
    example: SyncExampleSchema = example_service.get_sync_example(db, example_id)
    if not example:
        raise HTTPException(status_code=404, detail="SyncExample not found")

    return SyncExampleResponse.model_validate(example)


@router.post("/sync/example", response_model= SyncExampleResponse, status_code=status.HTTP_201_CREATED,
             tags=["with_no_login_sync_example"])
def create_sync_example(request: CreateSyncExample, db: Session = Depends(get_db)):
    try:
        saved_sync_example = example_service.save_sync_example(db=db, create_example_data=request)
        return SyncExampleResponse.model_validate(saved_sync_example)

    except SQLAlchemyError as e:  # BL 내 에러로 변경 해야 함
        raise HTTPException(status_code=500, detail=str(e))
