from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domains.notification.models import Notification
from src.database.database import get_async_db

logger = logging.getLogger(__name__)


async def create_notification(
    db: AsyncSession,
    user_id: int,
    actor_user_id: int,
    event_type: str,
    resource_type: str,
    resource_id: int,
    message: str,
) -> Notification | None:
    """알림 생성 및 DB 저장

    Args:
        user_id: 알림 받을 사용자 ID
        actor_user_id: 행동한 사용자 ID
        event_type: 이벤트 타입 (question_voted, answer_created 등)
        resource_type: 리소스 타입 (question, answer)
        resource_id: 리소스 ID
        message: 알림 메시지

    Returns:
        생성된 Notification 객체 (자기 자신에게는 None)
    """
    # 자기 자신에게는 알림 보내지 않음
    if user_id == actor_user_id:
        return None

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

    # actor 정보 로드
    result = await db.execute(
        select(Notification)
        .where(Notification.id == notification.id)
        .options(selectinload(Notification.actor))
    )
    notification = result.scalars().one()

    return notification


def create_notification_sync(
    db,
    user_id: int,
    actor_user_id: int,
    event_type: str,
    resource_type: str,
    resource_id: int,
    message: str,
):
    """동기 컨텍스트(sync 라우터)에서 알림 생성

    Args:
        db: 동기 DB 세션
        user_id: 알림 받을 사용자 ID
        actor_user_id: 행동한 사용자 ID
        event_type: 이벤트 타입
        resource_type: 리소스 타입
        resource_id: 리소스 ID
        message: 알림 메시지

    Returns:
        생성된 Notification 객체 (자기 자신에게는 None)
    """
    # 자기 자신에게는 알림 보내지 않음
    if user_id == actor_user_id:
        return None

    try:
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
        db.commit()
        db.refresh(notification)
        return notification
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        db.rollback()
        return None


async def _create_notification_background(
    user_id: int,
    actor_user_id: int,
    event_type: str,
    resource_type: str,
    resource_id: int,
    message: str,
) -> None:
    """백그라운드에서 알림 생성 (내부용)"""
    try:
        # 새 DB 세션 생성
        async for db in get_async_db():
            try:
                await create_notification(
                    db=db,
                    user_id=user_id,
                    actor_user_id=actor_user_id,
                    event_type=event_type,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    message=message,
                )
            finally:
                await db.close()
            break
    except Exception as e:
        logger.error(f"Failed to create notification in background: {e}")


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
