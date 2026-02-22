import asyncio
import logging

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import StreamingResponse
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.database.database import get_async_db
from src.domains.notification import schemas as notification_schema
from src.domains.notification import service as notification_service
from src.domains.notification.sse_manager import sse_manager
from src.domains.user.models import User
from src.domains.user.router import get_current_user_with_async
from src.domains.user import service as user_service

# JWT 설정 (user.router와 동일)
SECRET_KEY = "d6bb5677104d5fe5259db4a9988f5243c4e77ecd577a7bc340c25c477e62418f"
ALGORITHM = "HS256"

router = APIRouter(prefix="/api/notification")
logger = logging.getLogger(__name__)


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


async def get_current_user_for_sse(
    token: str = Query(..., description="JWT access token"),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """SSE용 토큰 인증 (query parameter 사용)

    EventSource API는 커스텀 헤더를 지원하지 않으므로 query parameter로 토큰을 받습니다.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await user_service.get_user_async(db, username=username)
    if user is None:
        raise credentials_exception

    return user


@router.get("/stream")
async def notification_stream(
    request: Request,
    current_user: User = Depends(get_current_user_for_sse)
):
    """SSE 실시간 알림 스트림

    - 30초마다 heartbeat 전송 (NGINX timeout 방지)
    - 재연결 지원
    - 다중 탭 지원 (각 탭마다 독립적 연결)

    Query Parameters:
        token: JWT access token (required)

    Events:
        - connected: 연결 성공 (1회)
        - notification: 새 알림 (실시간)
        - heartbeat: 연결 유지 (30초 간격)
    """
    async def event_generator():
        queue = await sse_manager.connect(current_user.id)

        try:
            # 연결 성공 이벤트
            yield f"event: connected\ndata: {{\"user_id\": {current_user.id}}}\n\n"
            logger.info(f"SSE connection established: user_id={current_user.id}")

            # 메인 루프
            while True:
                try:
                    # 30초 타임아웃으로 대기
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"event: notification\ndata: {data}\n\n"

                except asyncio.TimeoutError:
                    # 연결 끊김 체크
                    if await request.is_disconnected():
                        logger.info(f"SSE client disconnected: user_id={current_user.id}")
                        break

                    # Heartbeat 전송 (연결 유지)
                    yield "event: heartbeat\ndata: {\"type\": \"ping\"}\n\n"

        except Exception as e:
            logger.error(f"SSE stream error: user_id={current_user.id}, error={e}", exc_info=True)
        finally:
            await sse_manager.disconnect(current_user.id, queue)
            logger.info(f"SSE connection closed: user_id={current_user.id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # NGINX 버퍼링 방지
        }
    )
