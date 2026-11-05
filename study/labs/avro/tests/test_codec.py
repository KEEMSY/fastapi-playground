import pytest
from fastavro import schemaless_reader
from fastavro._read_common import SchemaResolutionError
from io import BytesIO

from avro_lab.codec import (
    INCOMPATIBLE_READER,
    READER_V2,
    WRITER_V1,
    decode,
    encode_v1,
)


@pytest.fixture
def event_v1():
    return {
        "event_id": "evt-001",
        "user_id": "user-123",
        "email": "dev@example.com",
    }


def test_avro_binary_round_trip_preserves_v1_fields(event_v1):
    payload = encode_v1(event_v1)

    assert isinstance(payload, bytes)
    assert payload != str(event_v1).encode()
    assert decode(payload) == event_v1


def test_v2_reader_applies_default_to_old_v1_payload(event_v1):
    payload = encode_v1(event_v1)

    decoded = decode(payload, READER_V2)

    assert decoded == {**event_v1, "display_name": None}


def test_reader_required_field_without_default_cannot_read_v1(event_v1):
    payload = encode_v1(event_v1)

    with pytest.raises(SchemaResolutionError):
        schemaless_reader(
            BytesIO(payload),
            WRITER_V1,
            INCOMPATIBLE_READER,
        )
