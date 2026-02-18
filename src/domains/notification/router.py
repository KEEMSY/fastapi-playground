import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request
from starlette.responses import StreamingResponse

from src.database.database import get_async_db
from src.domains.notification import schemas as notification_schema
from src.domains.notification import service as notification_service
from src.domains.notification.sse_manager import sse_manager
from src.domains.user.models import User
from src.domains.user.router import get_current_user_with_async, SECRET_KEY, ALGORITHM
from src.domains.user import service as user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notification")

HEARTBEAT_INTERVAL = 30  # seconds


# --- SSE 전용 인증 (query param 토큰 지원) ---

async def get_current_user_for_sse(
    request: Request,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """Authorization 헤더 또는 query param ?token=xxx 모두 지원.

    브라우저 EventSource API는 커스텀 헤더를 보낼 수 없으므로
    SSE 엔드포인트에서는 query param 폴백이 필요하다.
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token_value = auth_header.split(" ", 1)[1]
    elif token:
        token_value = token
    else:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token_value, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await user_service.get_user_async(db, username=username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# --- REST API ---

@router.get("/list", response_model=notification_schema.NotificationList)
async def notification_list(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async),
    page: int = 0,
    size: int = 20,
):
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
    await notification_service.mark_as_read(
        db, user_id=current_user.id, notification_ids=body.notification_ids
    )


@router.put("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async),
):
    await notification_service.mark_all_as_read(db, user_id=current_user.id)


# --- SSE 스트리밍 ---

@router.get("/stream")
async def notification_stream(
    request: Request,
    current_user: User = Depends(get_current_user_for_sse),
):
    """SSE 엔드포인트: 실시간 알림 스트리밍.

    클라이언트 사용법:
        const es = new EventSource('/api/notification/stream?token=<jwt>');
        es.addEventListener('notification', (e) => {
            const data = JSON.parse(e.data);
            console.log(data);
        });
    """

    async def event_generator():
        queue = sse_manager.connect(current_user.id)
        try:
            yield f"event: connected\ndata: {json.dumps({'user_id': current_user.id})}\n\n"

            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL)
                    yield f"event: notification\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        break
                    yield f"event: heartbeat\ndata: {json.dumps({'type': 'ping'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            sse_manager.disconnect(current_user.id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
