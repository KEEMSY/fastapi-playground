from sqlalchemy.exc import IntegrityError

from order_flow.db import SessionFactory
from order_flow.models import OrderReceipt


async def mark_receipt_sent(order_id: str, session_factory=SessionFactory) -> bool:
    """Persist the task's effect once, even when Celery redelivers the task."""
    async with session_factory() as session:
        try:
            async with session.begin():
                if await session.get(OrderReceipt, order_id):
                    return False
                session.add(OrderReceipt(order_id=order_id))
                await session.flush()
        except IntegrityError:
            await session.rollback()
            if await session.get(OrderReceipt, order_id):
                return False
            raise
    return True
