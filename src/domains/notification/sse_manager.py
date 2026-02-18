import asyncio
import logging

logger = logging.getLogger(__name__)


class SSEConnectionManager:
    """SSE 연결 관리자.

    user_id별 asyncio.Queue를 관리하여 실시간 알림을 전달한다.
    한 사용자가 여러 탭을 열 수 있으므로 user_id → set[Queue]로 관리.

    멀티 인스턴스가 필요해지면 Redis Pub/Sub를 여기에 추가하면 된다.
    """

    def __init__(self):
        self._connections: dict[int, set[asyncio.Queue]] = {}

    def connect(self, user_id: int) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(queue)
        logger.info(
            f"SSE connected: user_id={user_id}, "
            f"total={sum(len(v) for v in self._connections.values())}"
        )
        return queue

    def disconnect(self, user_id: int, queue: asyncio.Queue) -> None:
        if user_id in self._connections:
            self._connections[user_id].discard(queue)
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info(f"SSE disconnected: user_id={user_id}")

    async def send_to_user(self, user_id: int, data: str) -> None:
        """해당 user_id의 모든 SSE 연결에 데이터를 푸시한다."""
        queues = self._connections.get(user_id, set())
        for queue in queues:
            await queue.put(data)


# 싱글턴 인스턴스
sse_manager = SSEConnectionManager()
