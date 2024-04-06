from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.domains.question import schemas
from src.domains.question.models import Question

router = APIRouter(
    prefix="/api/question",
)


@router.get("/list", response_model=list[schemas.Question])
def question_list(db: Session = Depends(get_db)):
    _question_list = db.query(Question).order_by(Question.create_date.desc()).all()
    return _question_list
