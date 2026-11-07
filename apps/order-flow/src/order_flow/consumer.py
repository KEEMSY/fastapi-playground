import asyncio
import logging
import os

import aio_pika

from order_flow.db import SessionFactory
from order_flow.dispatch import record_and_enqueue
from order_flow.events import decode_order_created

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_flow.consumer")
AMQP_URL = os.getenv("AMQP_URL", "amqp://order_flow:order_flow@localhost:5673/")
EXCHANGE_NAME = "orders.events"
QUEUES = ("orders.audit", "orders.receipts")


async def consume_queue(queue_name: str, channel, exchange):
    queue = await channel.declare_queue(queue_name, durable=True)
    await queue.bind(exchange, routing_key="order.created")
    async with queue.iterator() as messages:
        async for message in messages:
            async with message.process(requeue=True):
                event = decode_order_created(message.body)
                is_new = await record_and_enqueue(queue_name, event, SessionFactory)
                logger.info(
                    "queue=%s order_id=%s message_id=%s duplicate=%s",
                    queue_name,
                    event["order_id"],
                    event["message_id"],
                    not is_new,
                )


async def main():
    connection = await aio_pika.connect_robust(AMQP_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True)
    await asyncio.gather(*(consume_queue(queue_name, channel, exchange) for queue_name in QUEUES))


if __name__ == "__main__":
    asyncio.run(main())
