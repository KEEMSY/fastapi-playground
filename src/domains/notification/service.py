from datetime import datetime

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domains.notification.models import Notification


async def create_notification(
    db: AsyncSession,
    user_id: int,
    actor_user_id: int,
    event_type: str,
    resource_type: str,
    resource_id: int,
    message: str,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        message=message,
        created_at=datetime.utcnow(),
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    result = await db.execute(
        select(Notification)
        .where(Notification.id == notification.id)
        .options(selectinload(Notification.actor))
    )
    return result.scalars().one()


async def get_notifications(
    db: AsyncSession, user_id: int, offset: int = 0, limit: int = 20
) -> tuple[int, int, list[Notification]]:
    total_q = await db.execute(
        select(func.count()).select_from(
            select(Notification).where(Notification.user_id == user_id).subquery()
        )
    )
    total = total_q.scalar_one()

    unread_q = await db.execute(
        select(func.count()).select_from(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read == False
            ).subquery()
        )
    )
    unread_count = unread_q.scalar_one()

    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .options(selectinload(Notification.actor))
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    notifications = result.scalars().fetchall()

    return total, unread_count, notifications


async def mark_as_read(
    db: AsyncSession, user_id: int, notification_ids: list[int]
) -> int:
    stmt = (
        update(Notification)
        .where(
            Notification.id.in_(notification_ids),
            Notification.user_id == user_id,
        )
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


async def mark_all_as_read(db: AsyncSession, user_id: int) -> int:
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount
