from datetime import datetime

from sqlalchemy.orm import Session

from src.domains.question.models import Question
from src.domains.question.schemas import QuestionCreate, QuestionUpdate
from src.domains.user.models import User


# offset: 시작 위치, limit: 가져올 데이터 수
def get_question_list(db: Session, offset: int = 0, limit: int = 10):
    _question_list = db.query(Question).order_by(Question.create_date.desc())

    total = _question_list.count()
    question_list = _question_list.offset(offset).limit(limit).all()
    return total, question_list  # (전체 건수, 페이징 적용된 질문 목록)


def get_question(db: Session, question_id: int):
    question = db.query(Question).get(question_id)
    return question


def create_question(db: Session, question_create: QuestionCreate, user: User):
    db_question = Question(
        subject=question_create.subject,
        content=question_create.content,
        create_date=datetime.now(),
        user=user
    )
    db.add(db_question)
    db.commit()


def update_question(db: Session, question_model: Question, question_update: QuestionUpdate):
    question_model.subject = question_update.subject
    question_model.content = question_update.content
    question_model.modify_date = datetime.now()
    db.add(question_model)
    db.commit()


def delete_question(db: Session, question_model: Question):
    db.delete(question_model)
    db.commit()
