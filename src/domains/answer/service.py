from datetime import datetime

from sqlalchemy.orm import Session

from src.domains.answer.models import Answer
from src.domains.answer.schemas import AnswerCreate
from src.domains.question.models import Question


def create_answer(db: Session, question: Question, answer_create: AnswerCreate):
    db_answer = Answer(
        question=question, content=answer_create.content, create_date=datetime.now()
    )
    db.add(db_answer)
    db.commit()