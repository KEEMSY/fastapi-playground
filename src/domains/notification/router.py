from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.database.database import get_async_db
from src.domains.notification import schemas as notification_schema
from src.domains.notification import service as notification_service
from src.domains.user.models import User
from src.domains.user.router import get_current_user_with_async

router = APIRouter(prefix="/api/notification")


@router.get("/list", response_model=notification_schema.NotificationList)
async def notification_list(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async),
    page: int = 0,
    size: int = 20,
):
    """알림 목록 조회 (페이징)

    클라이언트에서 주기적으로 호출하여 새 알림 확인
    예: 10초마다 폴링
    """
    total, unread_count, notifications = await notification_service.get_notifications(
        db, user_id=current_user.id, offset=page * size, limit=size
    )
    return {
        "total": total,
        "unread_count": unread_count,
        "notifications": [
            notification_schema.NotificationResponse.from_orm_with_actor(n)
            for n in notifications
        ],
    }


@router.put("/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notifications_read(
    body: notification_schema.NotificationReadUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async),
):
    """선택한 알림을 읽음 처리"""
    await notification_service.mark_as_read(
        db, user_id=current_user.id, notification_ids=body.notification_ids
    )


@router.put("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async),
):
    """모든 알림을 읽음 처리"""
    await notification_service.mark_all_as_read(db, user_id=current_user.id)
