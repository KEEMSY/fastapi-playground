import asyncio
import logging
import os

import aio_pika
from sqlalchemy import select

from order_flow.db import SessionFactory
from order_flow.events import encode_order_created
from order_flow.models import OutboxEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_flow.relay")
AMQP_URL = os.getenv("AMQP_URL", "amqp://order_flow:order_flow@localhost:5673/")
EXCHANGE_NAME = "orders.events"


async def relay_once(exchange, batch_size: int = 20) -> int:
    published = 0
    async with SessionFactory() as session:
        async with session.begin():
            rows = (await session.scalars(
                select(OutboxEvent)
                .where(OutboxEvent.status == "pending")
                .order_by(OutboxEvent.created_at, OutboxEvent.id)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )).all()
            for row in rows:
                message = aio_pika.Message(
                    body=encode_order_created(row.payload),
                    message_id=row.id,
                    content_type="avro/binary",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                )
                await exchange.publish(message, routing_key=row.event_type, mandatory=True)
                row.status = "published"
                row.attempts += 1
                published += 1
    return published


async def main():
    connection = await aio_pika.connect_robust(AMQP_URL)
    channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
    exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True)
    # Provision durable bindings so confirmed publishes have destinations even
    # before the separate consumer processes start.
    for queue_name in ("orders.audit", "orders.receipts"):
        queue = await channel.declare_queue(queue_name, durable=True)
        await queue.bind(exchange, routing_key="order.created")
    try:
        while True:
            try:
                count = await relay_once(exchange)
                if count:
                    logger.info("published %d outbox event(s)", count)
                else:
                    await asyncio.sleep(1)
            except Exception:
                logger.exception("outbox publish failed; pending events will be retried")
                await asyncio.sleep(1)
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
