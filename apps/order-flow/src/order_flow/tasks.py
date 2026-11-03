import asyncio
import logging

from order_flow.celery_app import celery_app
from order_flow.db import engine
from order_flow.receipts import mark_receipt_sent

logger = logging.getLogger(__name__)


async def run_receipt_task(order_id: str) -> bool:
    try:
        return await mark_receipt_sent(order_id)
    finally:
        # Celery runs this synchronous task in a new asyncio loop per invocation.
        # Dispose pooled async connections so the next invocation does not reuse
        # a connection attached to the previous loop.
        await engine.dispose()


@celery_app.task(
    bind=True,
    name="order_flow.send_order_receipt",
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5,
)
def send_order_receipt(self, order_id: str):
    created = asyncio.run(run_receipt_task(order_id))
    logger.info("receipt order_id=%s already_exists=%s", order_id, not created)
    return {"order_id": order_id, "created": created}
