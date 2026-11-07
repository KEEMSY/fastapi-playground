import asyncio
import logging
import os

import aio_pika

from order_flow.db import SessionFactory
from order_flow.delivery import route_failed_message
from order_flow.dispatch import record_and_enqueue
from order_flow.events import decode_order_created

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_flow.consumer")
AMQP_URL = os.getenv("AMQP_URL", "amqp://order_flow:order_flow@localhost:5673/")
EXCHANGE_NAME = "orders.events"
RETRY_EXCHANGE_NAME = "orders.retry"
DEAD_EXCHANGE_NAME = "orders.dead"
QUEUES = ("orders.audit", "orders.receipts")
MAX_RETRIES = max(0, int(os.getenv("CONSUMER_MAX_RETRIES", "3")))
RETRY_DELAY_MS = max(1, int(os.getenv("CONSUMER_RETRY_DELAY_MS", "3000")))


def make_message(body, message_id, content_type, headers):
    return aio_pika.Message(
        body=body,
        message_id=message_id,
        content_type=content_type,
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        headers=headers,
    )


async def declare_topology(channel):
    event_exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True)
    retry_exchange = await channel.declare_exchange(RETRY_EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True)
    dead_exchange = await channel.declare_exchange(DEAD_EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True)

    for queue_name in QUEUES:
        queue = await channel.declare_queue(queue_name, durable=True)
        await queue.bind(event_exchange, routing_key="order.created")
        await queue.bind(event_exchange, routing_key=f"retry.{queue_name}")

        retry_queue = await channel.declare_queue(
            f"{queue_name}.retry",
            durable=True,
            arguments={
                "x-message-ttl": RETRY_DELAY_MS,
                "x-dead-letter-exchange": EXCHANGE_NAME,
                "x-dead-letter-routing-key": f"retry.{queue_name}",
            },
        )
        await retry_queue.bind(retry_exchange, routing_key=queue_name)

        dead_queue = await channel.declare_queue(f"{queue_name}.dlq", durable=True)
        await dead_queue.bind(dead_exchange, routing_key=queue_name)

    return event_exchange, retry_exchange, dead_exchange


async def consume_queue(queue_name: str, channel, retry_exchange, dead_exchange):
    queue = await channel.declare_queue(queue_name, durable=True)
    async with queue.iterator() as messages:
        async for message in messages:
            try:
                event = decode_order_created(message.body)
                is_new = await record_and_enqueue(queue_name, event, SessionFactory)
            except Exception as error:
                outcome = await route_failed_message(
                    message,
                    queue_name,
                    retry_exchange,
                    dead_exchange,
                    make_message,
                    max_retries=MAX_RETRIES,
                    error=error,
                )
                logger.warning(
                    "queue=%s message_id=%s retry_count=%s outcome=%s error=%s",
                    queue_name,
                    message.message_id,
                    (message.headers or {}).get("x-retry-count", 0),
                    outcome,
                    error,
                )
            else:
                await message.ack()
                logger.info(
                    "queue=%s order_id=%s message_id=%s duplicate=%s",
                    queue_name,
                    event["order_id"],
                    event["message_id"],
                    not is_new,
                )


async def main():
    connection = await aio_pika.connect_robust(AMQP_URL)
    channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
    await channel.set_qos(prefetch_count=10)
    _, retry_exchange, dead_exchange = await declare_topology(channel)
    await asyncio.gather(*(
        consume_queue(queue_name, channel, retry_exchange, dead_exchange)
        for queue_name in QUEUES
    ))


if __name__ == "__main__":
    asyncio.run(main())
