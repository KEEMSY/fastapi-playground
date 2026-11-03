from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from order_flow.models import ProcessedMessage


async def record_event(session, consumer_name: str, event: dict) -> bool:
    """Atomically record delivery; return False for a message already applied."""
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
