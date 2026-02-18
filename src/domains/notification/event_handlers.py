import json
import logging

from src.common.events import DomainEvent, EventType, event_bus
from src.database.database import AsyncSessionPrimary
from src.domains.notification import service as notification_service
from src.domains.notification.sse_manager import sse_manager

logger = logging.getLogger(__name__)


async def handle_domain_event(event: DomainEvent) -> None:
    """도메인 이벤트를 받아 알림을 DB에 저장하고 SSE로 푸시한다."""
    # 자기 행동에 자기에게 알림 보내지 않음
    if event.actor_user_id == event.target_user_id:
        return

    # 핸들러는 fire-and-forget으로 실행되므로 별도 DB 세션 사용
    async with AsyncSessionPrimary() as db:
        try:
            notification = await notification_service.create_notification(
                db=db,
                user_id=event.target_user_id,
                actor_user_id=event.actor_user_id,
                event_type=event.event_type.value,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                message=event.message,
            )

            sse_payload = json.dumps({
                "id": notification.id,
                "event_type": notification.event_type,
                "resource_type": notification.resource_type,
                "resource_id": notification.resource_id,
                "message": notification.message,
                "actor_username": notification.actor.username if notification.actor else None,
                "created_at": notification.created_at.isoformat(),
            }, ensure_ascii=False)

            await sse_manager.send_to_user(
                user_id=event.target_user_id,
                data=sse_payload,
            )

            logger.info(
                f"Notification created: id={notification.id}, "
                f"user={event.target_user_id}, type={event.event_type.value}"
            )
        except Exception as e:
            logger.error(f"Failed to handle event {event.event_type.value}: {e}", exc_info=True)


def register_event_handlers() -> None:
    """모든 이벤트 타입에 핸들러를 등록한다. 앱 시작 시 1회 호출."""
    for event_type in EventType:
        event_bus.subscribe(event_type, handle_domain_event)
    logger.info("Notification event handlers registered")
