import json
import os
from pathlib import Path
from io import BytesIO

from fastavro import parse_schema, schemaless_reader, schemaless_writer

_SCHEMA_PATH = Path(os.getenv("ORDER_CREATED_SCHEMA", Path.cwd() / "schemas" / "order-created.avsc"))
if not _SCHEMA_PATH.exists():
    _SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "order-created.avsc"
_SCHEMA_V2_PATH = _SCHEMA_PATH.with_name("order-created-v2.avsc")
with _SCHEMA_PATH.open(encoding="utf-8") as schema_file:
    ORDER_CREATED_SCHEMA = parse_schema(json.load(schema_file))
with _SCHEMA_V2_PATH.open(encoding="utf-8") as schema_file:
    ORDER_CREATED_V2_SCHEMA = parse_schema(json.load(schema_file))


SCHEMAS = {1: ORDER_CREATED_SCHEMA, 2: ORDER_CREATED_V2_SCHEMA}


def encode_order_created(event: dict, writer_version: int = 1) -> bytes:
    if writer_version not in SCHEMAS:
        raise ValueError(f"unsupported OrderCreated writer schema version: {writer_version}")
    writer_event = dict(event)
    if writer_version == 2:
        writer_event.setdefault("customer_note", None)
    output = BytesIO()
    schemaless_writer(output, SCHEMAS[writer_version], writer_event)
    return output.getvalue()


def encode_order_created_v2(event: dict) -> bytes:
    return encode_order_created(event, writer_version=2)


def decode_order_created(payload: bytes, writer_version: int = 1, reader_version: int = 2) -> dict:
    if writer_version not in SCHEMAS or reader_version not in SCHEMAS:
        raise ValueError("unsupported OrderCreated schema version")
    return schemaless_reader(BytesIO(payload), SCHEMAS[writer_version], SCHEMAS[reader_version])


def decode_order_created_v2(payload: bytes) -> dict:
    return decode_order_created(payload, writer_version=1, reader_version=2)


def decode_order_created_message(payload: bytes, headers: dict | None) -> dict:
    writer_version = int((headers or {}).get("schema-version", 1))
    return decode_order_created(payload, writer_version=writer_version)
