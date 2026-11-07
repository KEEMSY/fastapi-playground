from order_flow.db import SessionFactory
from order_flow.processing import record_event


async def record_and_enqueue(
    queue_name: str,
    event: dict,
    session_factory=SessionFactory,
) -> bool:
    async with session_factory() as session:
        return await record_event(
            session,
            queue_name,
            event,
            enqueue_receipt=queue_name == "orders.receipts",
        )
