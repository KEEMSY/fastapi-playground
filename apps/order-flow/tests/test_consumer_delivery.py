import pytest

from order_flow.delivery import route_failed_message


class FakeMessage:
    body = b"encoded-event"
    message_id = "event-1"
    content_type = "avro/binary"
    headers = {}

    def __init__(self, headers=None):
        self.headers = headers or {}
        self.acked = False
        self.nacked = False
        self.requeue = None

    async def ack(self):
        self.acked = True

    async def nack(self, requeue):
        self.nacked = True
        self.requeue = requeue


def make_message(body, message_id, content_type, headers):
    message = FakeMessage(headers=headers)
    message.body = body
    message.message_id = message_id
    message.content_type = content_type
    return message


class FakeExchange:
    def __init__(self):
        self.messages = []

    async def publish(self, message, routing_key, mandatory):
        self.messages.append((message, routing_key, mandatory))


@pytest.mark.asyncio
async def test_failed_message_is_republished_to_its_consumer_retry_queue():
    original = FakeMessage()
    retry_exchange = FakeExchange()
    dead_exchange = FakeExchange()

    outcome = await route_failed_message(
        original, "orders.audit", retry_exchange, dead_exchange, make_message, max_retries=2,
        error=ValueError("temporary")
    )

    assert outcome == "retry"
    assert original.acked is True
    assert retry_exchange.messages[0][1:] == ("orders.audit", True)
    retried_message = retry_exchange.messages[0][0]
    assert retried_message.headers["x-retry-count"] == 1
    assert dead_exchange.messages == []


@pytest.mark.asyncio
async def test_exhausted_message_is_sent_to_consumer_specific_dlq():
    original = FakeMessage(headers={"x-retry-count": 2})
    retry_exchange = FakeExchange()
    dead_exchange = FakeExchange()

    outcome = await route_failed_message(
        original, "orders.receipts", retry_exchange, dead_exchange, make_message, max_retries=2,
        error=ValueError("bad schema")
    )

    assert outcome == "dead-letter"
    assert original.acked is True
    assert retry_exchange.messages == []
    assert dead_exchange.messages[0][1:] == ("orders.receipts", True)
    dead_letter = dead_exchange.messages[0][0]
    assert dead_letter.headers["x-retry-count"] == 2
    assert dead_letter.headers["x-failure-reason"] == "bad schema"


@pytest.mark.asyncio
async def test_publish_failure_nacks_original_for_broker_redelivery():
    original = FakeMessage()

    class FailedExchange:
        async def publish(self, message, routing_key, mandatory):
            raise ConnectionError("broker unavailable")

    outcome = await route_failed_message(
        original, "orders.audit", FailedExchange(), FakeExchange(), make_message, max_retries=2,
        error=ValueError("temporary")
    )

    assert outcome == "requeued"
    assert original.acked is False
    assert original.nacked is True
    assert original.requeue is True
