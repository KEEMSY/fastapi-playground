from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.domains.user.models import User
from src.domains.user.schemas import UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_user(db: Session, user_create: UserCreate):
    db_user = User(
        username=user_create.username,
        password=pwd_context.hash(user_create.password1),
        email=user_create.email,
    )
    db.add(db_user)
    db.commit()
