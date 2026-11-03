import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    actor_user_id: int
    actor_username: Optional[str] = None
    event_type: str
    resource_type: str
    resource_id: int
    message: str
    is_read: bool
    created_at: datetime.datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_actor(cls, notification) -> "NotificationResponse":
        return cls(
            id=notification.id,
            user_id=notification.user_id,
            actor_user_id=notification.actor_user_id,
            actor_username=notification.actor.username if notification.actor else None,
            event_type=notification.event_type,
            resource_type=notification.resource_type,
            resource_id=notification.resource_id,
            message=notification.message,
            is_read=notification.is_read,
            created_at=notification.created_at,
        )


class NotificationList(BaseModel):
    total: int = 0
    unread_count: int = 0
    notifications: list[NotificationResponse] = []


class NotificationReadUpdate(BaseModel):
    notification_ids: list[int]
