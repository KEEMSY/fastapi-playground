from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.domains.question import schemas as question_schema, service as question_service

router = APIRouter(
    prefix="/api/question",
)


@router.get("/list", response_model=list[question_schema.Question])
def question_list(db: Session = Depends(get_db)):
    _question_list = question_service.get_question_list(db)
    return _question_list
