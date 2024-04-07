import datetime

from pydantic import BaseModel, field_validator


class AnswerCreate(BaseModel):
    content: str

    @field_validator("content")
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Content can't be empty")
        return v


class Answer(BaseModel):
    id: int
    content: str
    create_date: datetime.datetime
