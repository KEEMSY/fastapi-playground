import datetime

from pydantic import BaseModel

from src.domains.answer.schemas import Answer


class Question(BaseModel):
    id: int
    subject: str
    content: str
    create_date: datetime.datetime
    answers: list[Answer] = []
