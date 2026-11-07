from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from order_flow.models import ProcessedMessage, TaskDispatchOutbox


async def record_event(session, consumer_name: str, event: dict, enqueue_receipt: bool = False) -> bool:
    """Atomically record delivery and its receipt command, if applicable."""
    try:
        async with session.begin():
            existing = await session.scalar(
                select(ProcessedMessage.id).where(
                    ProcessedMessage.consumer_name == consumer_name,
                    ProcessedMessage.message_id == event["message_id"],
                )
            )
            if existing is not None:
                return False
            session.add(ProcessedMessage(consumer_name=consumer_name, message_id=event["message_id"]))
            if enqueue_receipt:
                session.add(TaskDispatchOutbox(
                    id=event["message_id"], order_id=event["order_id"], status="pending"
                ))
            await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(
            select(ProcessedMessage.id).where(
                ProcessedMessage.consumer_name == consumer_name,
                ProcessedMessage.message_id == event["message_id"],
            )
        )
        if existing is not None:
            return False
        raise
    return True
