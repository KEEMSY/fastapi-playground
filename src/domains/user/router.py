from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from starlette import status

from src.database import get_db
from src.domains.user.schemas import UserCreate
from src.domains.user import service as user_service

router = APIRouter(
    prefix="/api/user",
)


@router.post("/create", status_code=status.HTTP_204_NO_CONTENT)
def user_create(_user_create: UserCreate, db: Session = Depends(get_db)):
    user_service.create_user(db=db, user_create=_user_create)
