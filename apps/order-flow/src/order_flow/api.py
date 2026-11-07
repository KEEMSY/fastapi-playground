import hashlib
import json
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from order_flow.db import get_session
from order_flow.models import IdempotencyRecord, Order, OrderReceipt, OutboxEvent, ProcessedMessage, TaskDispatchOutbox
from order_flow.schemas import OrderCreate, OrderProgressResponse, OrderResponse

app = FastAPI(title="Order Flow Lab")


def request_digest(payload: OrderCreate) -> str:
    canonical = json.dumps(payload.model_dump(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


async def replay_or_conflict(session: AsyncSession, key: str, digest: str):
    existing = await session.get(IdempotencyRecord, key)
    if existing is None:
        return None
    if existing.request_hash != digest:
        raise HTTPException(status_code=409, detail="Idempotency-Key was already used with a different request")
    return existing.response_body


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/orders/{order_id}", response_model=OrderProgressResponse)
async def get_order_progress(order_id: str, session: AsyncSession = Depends(get_session)):
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    event = await session.scalar(
        select(OutboxEvent).where(OutboxEvent.aggregate_id == order_id)
    )
    processed_consumers = []
    receipt_task_status = None
    if event is not None:
        processed_consumers = list(await session.scalars(
            select(ProcessedMessage.consumer_name)
            .where(ProcessedMessage.message_id == event.id)
            .order_by(ProcessedMessage.consumer_name)
        ))
        task_command = await session.get(TaskDispatchOutbox, event.id)
        if task_command is not None:
            receipt_task_status = task_command.status

    receipt = await session.get(OrderReceipt, order_id)
    return OrderProgressResponse(
        order_id=order.id,
        order_status=order.status,
        event_status=event.status if event is not None else None,
        processed_consumers=processed_consumers,
        receipt_task_status=receipt_task_status,
        receipt_recorded=receipt is not None,
    )


@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    response: Response,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    session: AsyncSession = Depends(get_session),
):
    digest = request_digest(payload)
    order_id = str(uuid4())
    event_id = str(uuid4())
    response_body = {"id": order_id, **payload.model_dump(), "status": "created"}
    event_payload = {"message_id": event_id, "order_id": order_id, **payload.model_dump()}
    try:
        async with session.begin():
            replay = await replay_or_conflict(session, idempotency_key, digest)
            if replay is not None:
                response.status_code = status.HTTP_200_OK
                return replay
            session.add(Order(id=order_id, **payload.model_dump(), status="created"))
            session.add(IdempotencyRecord(key=idempotency_key, request_hash=digest, response_body=response_body))
            session.add(OutboxEvent(id=event_id, aggregate_id=order_id, event_type="order.created",
                                    payload=event_payload, status="pending"))
            await session.flush()
    except IntegrityError:
        await session.rollback()
        replay = await replay_or_conflict(session, idempotency_key, digest)
        if replay is None:
            raise
        response.status_code = status.HTTP_200_OK
        return replay

    return response_body
