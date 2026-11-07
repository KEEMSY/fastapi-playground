import asyncio
import logging
from datetime import datetime, timezone

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from order_flow.db import SessionFactory
from order_flow.models import TaskDispatchOutbox

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_flow.task_relay")


def publish_receipt_task(order_id: str, task_id: str) -> None:
    from order_flow.tasks import send_order_receipt

    send_order_receipt.apply_async(args=[order_id], task_id=task_id)


async def relay_once(session_factory=SessionFactory, publisher=publish_receipt_task, batch_size: int = 20) -> int:
    dispatched = 0
    async with session_factory() as session:
        async with session.begin():
            rows = (await session.scalars(
                select(TaskDispatchOutbox)
                .where(TaskDispatchOutbox.status == "pending")
                .order_by(TaskDispatchOutbox.created_at, TaskDispatchOutbox.id)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )).all()
            for row in rows:
                row.attempts += 1
                task_id = f"receipt-{row.id}"
                try:
                    await run_in_threadpool(publisher, row.order_id, task_id)
                except Exception:
                    logger.exception(
                        "receipt task publish failed order_id=%s task_id=%s",
                        row.order_id,
                        task_id,
                    )
                    continue
                row.status = "dispatched"
                row.dispatched_at = datetime.now(timezone.utc)
                dispatched += 1
                logger.info(
                    "dispatched order_id=%s task_id=%s attempts=%s",
                    row.order_id,
                    task_id,
                    row.attempts,
                )
    return dispatched


async def main():
    while True:
        try:
            count = await relay_once()
        except Exception:
            logger.exception("task outbox poll failed; pending commands will be retried")
            await asyncio.sleep(1)
            continue
        if count == 0:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
