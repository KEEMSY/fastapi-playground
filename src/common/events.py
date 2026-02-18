import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


# --- 도메인 이벤트 정의 ---

class EventType(str, Enum):
    QUESTION_VOTED = "question.voted"
    ANSWER_CREATED = "answer.created"
    ANSWER_VOTED = "answer.voted"


@dataclass
class DomainEvent:
    event_type: EventType
    actor_user_id: int       # 행동한 사용자
    target_user_id: int      # 알림 받을 사용자
    resource_id: int         # question_id 또는 answer_id
    resource_type: str       # "question" 또는 "answer"
    message: str             # 알림 메시지
    timestamp: datetime = field(default_factory=datetime.utcnow)


# --- 이벤트 버스 ---

EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class EventBus:
    """인프로세스 비동기 이벤트 버스.

    사용법:
        event_bus.subscribe(EventType.QUESTION_VOTED, my_handler)
        await event_bus.publish(DomainEvent(...))
    """

    def __init__(self):
        self._handlers: dict[EventType, list[EventHandler]] = {}

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info(f"Handler {handler.__name__} subscribed to {event_type.value}")

    async def publish(self, event: DomainEvent) -> None:
        """async 컨텍스트에서 이벤트 발행 (fire-and-forget)."""
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                asyncio.create_task(self._safe_call(handler, event))
            except Exception as e:
                logger.error(f"Failed to dispatch event {event.event_type}: {e}")

    def publish_sync(self, event: DomainEvent) -> None:
        """sync 컨텍스트(Answer 도메인 등)에서 이벤트 발행.

        FastAPI의 sync 엔드포인트는 threadpool에서 실행되므로,
        메인 asyncio 이벤트 루프에 태스크를 예약한다.
        """
        try:
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(self.publish(event))
            )
        except RuntimeError:
            logger.warning(f"No running event loop; event {event.event_type} dropped")

    @staticmethod
    async def _safe_call(handler: EventHandler, event: DomainEvent) -> None:
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Error in handler {handler.__name__} for {event.event_type.value}: {e}",
                exc_info=True
            )


# 싱글턴 인스턴스
event_bus = EventBus()
