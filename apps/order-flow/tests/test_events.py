import pytest

pytest.importorskip("fastavro")

from order_flow.events import decode_order_created, decode_order_created_v2, encode_order_created


def test_order_created_event_round_trips_through_avro():
    event = {"message_id": "m-1", "order_id": "o-1", "sku": "book", "quantity": 3}

    assert decode_order_created(encode_order_created(event)) == event


def test_v2_reader_adds_default_when_reading_v1_event():
    event = {"message_id": "m-1", "order_id": "o-1", "sku": "book", "quantity": 3}

    assert decode_order_created_v2(encode_order_created(event))["customer_note"] is None
