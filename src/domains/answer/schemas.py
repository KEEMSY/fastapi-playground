from __future__ import annotations

import datetime
from typing import Union

from pydantic import BaseModel, field_validator

from src.domains.user.schemas import User


class AnswerCreate(BaseModel):
    content: str

    @field_validator("content")
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Content can't be empty")
        return v


class AnswerUpdate(AnswerCreate):
    answer_id: int


class AnswerDelete(BaseModel):
    answer_id: int


class Answer(BaseModel):
    id: int
    content: str
    create_date: datetime.datetime
    modify_date: Union[datetime.datetime, None] = None
    user: Union[User, None]
    question_id: int
