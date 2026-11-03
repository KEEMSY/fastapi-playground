"""DB 폴링 시스템

백그라운드에서 주기적으로 DB를 폴링하여 새 알림을 감지하고 SSE로 푸시합니다.
각 서버 인스턴스마다 독립적으로 동작합니다.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from src.database.database import AsyncSessionPrimary
from src.domains.notification.sse_manager import sse_manager
from src.domains.notification import service as notification_service
from src.domains.notification.schemas import NotificationResponse

logger = logging.getLogger(__name__)


class NotificationPoller:
    """백그라운드에서 DB를 주기적으로 폴링하여 새 알림을 SSE로 푸시

    - 폴링 간격: 1.5초 (서버 3대 × 40 QPS = 120 QPS, DB 부하 미미)
    - 최적화: 연결된 사용자만 조회
    - 각 서버 인스턴스마다 독립적으로 실행
    """

    def __init__(self, interval: float = 1.5):
        """
        Args:
            interval: 폴링 간격 (초)
        """
        self.interval = interval
        self.last_check: datetime = datetime.utcnow()
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """앱 시작 시 백그라운드 태스크로 실행"""
        if self.running:
            logger.warning("NotificationPoller is already running")
            return

        self.running = True
        self.last_check = datetime.utcnow()
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"NotificationPoller started (interval={self.interval}s)")

    async def stop(self):
        """앱 종료 시 폴링 중지"""
        if not self.running:
            return

        self.running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("NotificationPoller stopped")

    async def _poll_loop(self):
        """메인 폴링 루프"""
        while self.running:
            try:
                await asyncio.sleep(self.interval)
                await self._check_and_push_notifications()
            except asyncio.CancelledError:
                logger.info("Polling loop cancelled")
                break
            except Exception as e:
                logger.error(f"폴링 에러: {e}", exc_info=True)

    async def _check_and_push_notifications(self):
        """새 알림 확인 및 SSE 푸시"""
        # 1. 연결된 사용자만 조회 (최적화)
        connected_users = sse_manager.get_connected_users()
        if not connected_users:
            # logger.debug("No connected users, skipping poll")
            return

        # 2. DB에서 새 알림 조회
        try:
            async with AsyncSessionPrimary() as db:
                new_notifications = await notification_service.get_new_notifications_since(
                    db,
                    since=self.last_check,
                    user_ids=list(connected_users)
                )
        except Exception as e:
            logger.error(f"DB 조회 에러: {e}", exc_info=True)
            return

        # 3. 시간 업데이트 (새 알림이 있든 없든 항상 업데이트)
        # 단, 새 알림이 있으면 가장 최신 알림의 created_at으로 업데이트
        if new_notifications:
            self.last_check = max(n.created_at for n in new_notifications)
            logger.info(f"Found {len(new_notifications)} new notifications")
        else:
            # 새 알림이 없어도 현재 시간으로 업데이트하여 시간 누적 방지
            self.last_check = datetime.utcnow()

        # 4. user_id별로 그룹핑
        user_notifications: dict[int, list] = {}
        for notif in new_notifications:
            if notif.user_id not in user_notifications:
                user_notifications[notif.user_id] = []
            user_notifications[notif.user_id].append(notif)

        # 5. 각 사용자에게 SSE 푸시
        for user_id, notifications in user_notifications.items():
            for notif in notifications:
                try:
                    # NotificationResponse로 변환 후 JSON 직렬화
                    payload = NotificationResponse.from_orm_with_actor(notif).model_dump_json()
                    await sse_manager.send_to_user(user_id, payload)
                    logger.debug(f"Pushed notification {notif.id} to user {user_id}")
                except Exception as e:
                    logger.error(f"SSE 푸시 에러: user_id={user_id}, error={e}", exc_info=True)


# 싱글턴 인스턴스
notification_poller = NotificationPoller()
