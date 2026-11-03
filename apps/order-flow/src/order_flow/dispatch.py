from order_flow.db import SessionFactory
from order_flow.processing import record_event


async def record_and_dispatch(
    queue_name: str,
    event: dict,
    session_factory=SessionFactory,
    receipt_task=None,
) -> bool:
    async with session_factory() as session:
        is_new = await record_event(session, queue_name, event)

    if is_new and queue_name == "orders.receipts":
        if receipt_task is None:
            from order_flow.tasks import send_order_receipt

            receipt_task = send_order_receipt
        receipt_task.delay(event["order_id"])

    return is_new
