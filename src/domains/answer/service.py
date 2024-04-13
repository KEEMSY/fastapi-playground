from datetime import datetime

from sqlalchemy.orm import Session

from src.domains.answer.models import Answer
from src.domains.answer.schemas import AnswerCreate, AnswerUpdate
from src.domains.question.models import Question
from src.domains.user.models import User


def create_answer(db: Session, question: Question, answer_create: AnswerCreate, user: User):
    db_answer = Answer(
        question=question, content=answer_create.content, create_date=datetime.now(), user=user
    )
    db.add(db_answer)
    db.commit()


def get_answer_by_id(db: Session, answer_id: int) -> Answer:
    # return db.query(Answer).filter(Answer.id == answer_id).first()
    return db.query(Answer).get(answer_id)


def update_answer(db: Session, db_answer: Answer,
                  answer_update: AnswerUpdate):
    db_answer.content = answer_update.content
    db_answer.modify_date = datetime.now()
    db.add(db_answer)
    db.commit()


def delete_answer(db: Session, db_answer: Answer):
    db.delete(db_answer)
    db.commit()