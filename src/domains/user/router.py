from datetime import datetime, timedelta

from fastapi import Depends, APIRouter, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from sqlalchemy.orm import Session
from starlette import status

from src.database import get_db
from src.domains.user.schemas import UserCreate, Token
from src.domains.user import service as user_service
from src.domains.user.service import pwd_context

router = APIRouter(
    prefix="/api/user",
)

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
SECRET_KEY = "d6bb5677104d5fe5259db4a9988f5243c4e77ecd577a7bc340c25c477e62418f"
ALGORITHM = "HS256"


@router.post("/create", status_code=status.HTTP_204_NO_CONTENT)
def user_create(_user_create: UserCreate, db: Session = Depends(get_db)):
    user = user_service.get_existing_user(db, user_create=_user_create)
    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user already exists. Please try another one.",
        )
    user_service.create_user(db=db, user_create=_user_create)


@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):

    # check user and password
    user = user_service.get_user(db, form_data.username)
    if not user or not pwd_context.verify(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # make access token
    data = {
        "sub": user.username,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    access_token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
    }
