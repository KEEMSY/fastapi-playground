import logging
from collections.abc import Callable

logger = logging.getLogger("order_flow.consumer")


async def route_failed_message(
    message,
    queue_name: str,
    retry_exchange,
    dead_exchange,
    message_factory: Callable,
    *,
    max_retries: int,
    error: Exception,
) -> str:
    headers = dict(message.headers or {})
    retry_count = int(headers.get("x-retry-count", 0))
    if retry_count < max_retries:
        outcome = "retry"
        routing_key = queue_name
        headers["x-retry-count"] = retry_count + 1
        exchange = retry_exchange
    else:
        outcome = "dead-letter"
        routing_key = queue_name
        headers["x-failure-reason"] = str(error)[:500]
        exchange = dead_exchange

    retry_message = message_factory(
        body=message.body,
        message_id=message.message_id,
        content_type=message.content_type,
        headers=headers,
    )
    try:
        await exchange.publish(retry_message, routing_key=routing_key, mandatory=True)
    except Exception:
        logger.exception(
            "failure route publish failed queue=%s message_id=%s; requeueing original",
            queue_name,
            message.message_id,
        )
        await message.nack(requeue=True)
        return "requeued"

    await message.ack()
    return outcome
