from __future__ import annotations

import datetime
from typing import Union

from pydantic import BaseModel, field_validator

from src.domains.answer.schemas import Answer
from src.domains.user.schemas import User


class Question(BaseModel):
    id: int
    subject: str
    content: str
    create_date: datetime.datetime
    modify_date: Union[datetime.datetime, None] = None
    answers: list[Answer] = []
    user: Union[User, None]
    voter: list[User] = []


class QuestionList(BaseModel):
    total: int = 0
    question_list: list[Question] = []


class QuestionCreate(BaseModel):
    subject: str
    content: str

    @field_validator("subject", "content")
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Subject and content can't be empty")
        return v


class QuestionUpdate(QuestionCreate):
    question_id: int


class QuestionDelete(BaseModel):
    question_id: int


class QuestionVote(BaseModel):
    question_id: int
