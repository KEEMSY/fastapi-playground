"""Complete the TODOs to implement Avro writer/reader schema resolution."""

import json
from io import BytesIO
from pathlib import Path

from fastavro import parse_schema, schemaless_reader, schemaless_writer

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"


def load_schema(filename: str) -> dict:
    with (SCHEMA_DIR / filename).open(encoding="utf-8") as file:
        return parse_schema(json.load(file))


WRITER_V1 = load_schema("user-signed-up-v1.avsc")
READER_V2 = load_schema("user-signed-up-v2.avsc")
INCOMPATIBLE_READER = load_schema("user-signed-up-incompatible.avsc")


def encode_v1(event: dict) -> bytes:
    """Encode an event using the v1 schema. TODO: implement with fastavro."""
    raise NotImplementedError("Implement Avro binary encoding")


def decode(payload: bytes, reader_schema: dict = WRITER_V1) -> dict:
    """Decode bytes with the v1 writer schema and the requested reader schema."""
    raise NotImplementedError("Implement writer/reader schema resolution")
