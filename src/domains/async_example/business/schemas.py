import datetime
from typing import Optional

from pydantic import BaseModel

from src.domains.user.schemas import User


class AsyncExampleSchema(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    create_date: Optional[datetime.datetime] = None
    modify_date: Optional[datetime.datetime] = None
    user: Optional[User] = None

    model_config = {
        'extra': 'forbid',
        'from_attributes': True,
    }


class ASyncExampleSchemaList(BaseModel):
    total: int
    example_list: list[AsyncExampleSchema] = []

    model_config = {
        'extra': 'forbid',
        'from_attributes': True,
    }
