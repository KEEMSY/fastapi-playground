"""SSE 연결 관리자

SSE(Server-Sent Events) 연결을 관리하고 사용자별로 메시지를 전송합니다.
각 서버 인스턴스마다 독립적으로 동작하며, 멀티 탭을 지원합니다.
"""

import asyncio
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)


class SSEConnectionManager:
    """SSE 연결 관리자

    - user_id별로 asyncio.Queue 관리
    - 한 사용자가 여러 탭을 열 수 있으므로 set[Queue] 사용
    - 각 서버 인스턴스마다 독립적으로 동작
    """

    def __init__(self):
        # user_id -> set of queues (다중 탭 지원)
        self._connections: Dict[int, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: int) -> asyncio.Queue:
        """새 SSE 연결 등록

        Args:
            user_id: 사용자 ID

        Returns:
            asyncio.Queue: 메시지 수신용 큐
        """
        async with self._lock:
            queue = asyncio.Queue()

            if user_id not in self._connections:
                self._connections[user_id] = set()

            self._connections[user_id].add(queue)

            logger.info(
                f"SSE 연결 추가: user_id={user_id}, "
                f"총 연결 수={len(self._connections[user_id])}"
            )

            return queue

    async def disconnect(self, user_id: int, queue: asyncio.Queue) -> None:
        """SSE 연결 해제

        Args:
            user_id: 사용자 ID
            queue: 해제할 큐
        """
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id].discard(queue)

                # 해당 사용자의 모든 연결이 끊어졌으면 딕셔너리에서 제거
                if not self._connections[user_id]:
                    del self._connections[user_id]

                logger.info(
                    f"SSE 연결 해제: user_id={user_id}, "
                    f"남은 연결 수={len(self._connections.get(user_id, []))}"
                )

    async def send_to_user(self, user_id: int, data: str) -> None:
        """해당 서버에 연결된 사용자에게만 전송

        Args:
            user_id: 사용자 ID
            data: 전송할 데이터 (JSON 문자열)
        """
        if user_id not in self._connections:
            return

        # 해당 사용자의 모든 연결(탭)에 전송
        queues = self._connections[user_id].copy()  # 복사하여 iteration 중 수정 방지

        for queue in queues:
            try:
                await queue.put(data)
            except Exception as e:
                logger.error(f"SSE 메시지 전송 실패: user_id={user_id}, error={e}")

    def get_connected_users(self) -> Set[int]:
        """현재 연결된 사용자 ID 목록 (폴링 최적화용)

        Returns:
            set[int]: 연결된 사용자 ID 집합
        """
        return set(self._connections.keys())

    def total_connections(self) -> int:
        """총 연결 수 (모니터링용)

        Returns:
            int: 전체 SSE 연결 수
        """
        return sum(len(queues) for queues in self._connections.values())

    def get_stats(self) -> dict:
        """연결 통계 정보

        Returns:
            dict: 통계 정보
        """
        return {
            "connected_users": len(self._connections),
            "total_connections": self.total_connections(),
            "users": {
                user_id: len(queues)
                for user_id, queues in self._connections.items()
            }
        }


# 싱글턴 인스턴스
sse_manager = SSEConnectionManager()
