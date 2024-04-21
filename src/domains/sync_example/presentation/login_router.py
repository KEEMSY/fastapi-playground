from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette import status
from starlette.exceptions import HTTPException

from src.database import get_db
from src.domains.sync_example.business import service as example_service
from src.domains.sync_example.business.schemas import SyncExampleSchema, SyncExampleListSchema
from src.domains.sync_example.presentation.schemas import SyncExampleResponse, CreateSyncExample, \
    SyncExampleListResponse, UpdateSyncExampleV1, UpdateSyncExampleV2
from src.domains.user.router import get_current_user_with_sync

router = APIRouter(
    prefix="/api/sync/login",
)


@router.get("/sync/example/list", response_model=SyncExampleListResponse, tags=["with_login_sync_example"])
def read_sync_example_list(db: Session = Depends(get_db), current_user=Depends(get_current_user_with_sync),
                           limit: int = 10, offset: int = 0):
    sync_example_list_schema: SyncExampleListSchema = example_service.get_sync_example_list(db, limit=limit,
                                                                                            offset=limit * offset)

    return SyncExampleListResponse(
        total=sync_example_list_schema.total,
        example_list=sync_example_list_schema.example_list
    )


@router.get("/sync/example/{example_id}", response_model=SyncExampleResponse, tags=["with_login_sync_example"])
def read_sync_example(example_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user_with_sync)):
    example: SyncExampleSchema = example_service.get_sync_example(db, example_id)
    if not example:
        raise HTTPException(status_code=404, detail="SyncExample not found")

    return SyncExampleResponse.model_validate(example)


@router.post("/sync/example", response_model=SyncExampleResponse, status_code=status.HTTP_201_CREATED,
             tags=["with_login_sync_example"])
def create_sync_example(request: CreateSyncExample, db: Session = Depends(get_db),
                        current_user=Depends(get_current_user_with_sync)):
    try:
        saved_sync_example = example_service.save_sync_example(db=db, create_example_data=request)
        return SyncExampleResponse.model_validate(saved_sync_example)

    except SQLAlchemyError as e:  # BL 내 에러로 변경 해야 함
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sync/example/{example_id}", response_model=SyncExampleResponse, status_code=status.HTTP_200_OK,
            tags=["with_login_sync_example"])
def update_sync_example(example_id: int, request: UpdateSyncExampleV1, db: Session = Depends(get_db),
                        current_user=Depends(get_current_user_with_sync)):
    """
    Update V1: Path parameter로 example_id를 받아서 해당 Example을 업데이트 한다.
    """
    try:
        updated_sync_example = example_service.update_sync_example_v1(db=db, example_id=example_id, request=request)
        return SyncExampleResponse.model_validate(updated_sync_example)

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sync/example", response_model=SyncExampleResponse, status_code=status.HTTP_200_OK,
            tags=["with_login_sync_example"])
def update_sync_example(request: UpdateSyncExampleV2, db: Session = Depends(get_db),
                        current_user=Depends(get_current_user_with_sync)):
    """
    Update V2: Body parameter로 example_id를 받아서 해당 Example을 업데이트 한다.
    """
    try:
        updated_sync_example = example_service.update_sync_example_v2(db=db, request=request)
        return SyncExampleResponse.model_validate(updated_sync_example)

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sync/example/{example_id}", status_code=status.HTTP_204_NO_CONTENT,
               tags=["with_no_login_sync_example"])
def delete_sync_example(example_id: int, db: Session = Depends(get_db),
                        current_user=Depends(get_current_user_with_sync)):
    try:
        example_service.delete_sync_example(db, example_id)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))
