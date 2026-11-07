import pytest

pytest.importorskip("fastavro")

from order_flow.events import decode_order_created, decode_order_created_v2, encode_order_created


def test_order_created_event_round_trips_through_avro():
    event = {"message_id": "m-1", "order_id": "o-1", "sku": "book", "quantity": 3}

    assert decode_order_created(encode_order_created(event)) == {**event, "customer_note": None}


def test_v2_reader_adds_default_when_reading_v1_event():
    event = {"message_id": "m-1", "order_id": "o-1", "sku": "book", "quantity": 3}

    assert decode_order_created_v2(encode_order_created(event))["customer_note"] is None


def test_v1_reader_ignores_additive_v2_field():
    from order_flow.events import encode_order_created_v2

    event = {
        "message_id": "m-2", "order_id": "o-2", "sku": "book", "quantity": 2,
        "customer_note": "leave at the door",
    }

    decoded = decode_order_created(
        encode_order_created_v2(event), writer_version=2, reader_version=1
    )

    assert decoded == {key: value for key, value in event.items() if key != "customer_note"}


def test_v2_reader_uses_default_for_v1_writer():
    event = {"message_id": "m-3", "order_id": "o-3", "sku": "book", "quantity": 4}

    decoded = decode_order_created_v2(encode_order_created(event))

    assert decoded["customer_note"] is None


def test_reader_rejects_incompatible_field_type_and_required_addition():
    from io import BytesIO

    from fastavro import parse_schema, schemaless_reader
    from fastavro._read_common import SchemaResolutionError

    from order_flow.events import ORDER_CREATED_SCHEMA

    event = {"message_id": "m-4", "order_id": "o-4", "sku": "book", "quantity": 5}
    payload = encode_order_created(event)
    incompatible_schemas = [
        {
            "type": "record", "name": "OrderCreated", "namespace": "com.example.orderflow.v1",
            "fields": [
                {"name": "message_id", "type": "string"},
                {"name": "order_id", "type": "string"},
                {"name": "sku", "type": "string"},
                {"name": "quantity", "type": "string"},
            ],
        },
        {
            "type": "record", "name": "OrderCreated", "namespace": "com.example.orderflow.v1",
            "fields": [
                {"name": "message_id", "type": "string"},
                {"name": "order_id", "type": "string"},
                {"name": "sku", "type": "string"},
                {"name": "quantity", "type": "int"},
                {"name": "required_region", "type": "string"},
            ],
        },
    ]

    for reader_schema in incompatible_schemas:
        with pytest.raises(SchemaResolutionError):
            schemaless_reader(
                BytesIO(payload), ORDER_CREATED_SCHEMA, parse_schema(reader_schema)
            )


def test_message_header_selects_writer_schema_and_legacy_defaults_to_v1():
    from order_flow.events import decode_order_created_message, encode_order_created_v2

    v1_event = {"message_id": "m-5", "order_id": "o-5", "sku": "book", "quantity": 6}
    v2_event = {**v1_event, "customer_note": "call first"}

    assert decode_order_created_message(encode_order_created(v1_event), {}) == {
        **v1_event, "customer_note": None
    }
    assert decode_order_created_message(
        encode_order_created_v2(v2_event), {"schema-version": 2}
    ) == v2_event


def test_message_header_rejects_unknown_writer_schema_version():
    from order_flow.events import decode_order_created_message

    with pytest.raises(ValueError, match="unsupported OrderCreated schema version"):
        decode_order_created_message(b"payload", {"schema-version": 99})
