from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from src.database import get_db
from src.domains.answer.schemas import AnswerCreate
from src.domains.answer import service as answer_service
from src.domains.question import service as question_service
from src.domains.user.router import get_current_user

router = APIRouter(
    prefix="/api/answer",
)


@router.post("/create/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def answer_create(
        question_id: int,
        _answer_create: AnswerCreate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):

    # create answer
    question = question_service.get_question(db, question_id=question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    answer_service.create_answer(db, question=question, answer_create=_answer_create, user=current_user)
