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


def encode_order_created(event: dict) -> bytes:
    output = BytesIO()
    schemaless_writer(output, ORDER_CREATED_SCHEMA, event)
    return output.getvalue()


def decode_order_created(payload: bytes) -> dict:
    return schemaless_reader(BytesIO(payload), ORDER_CREATED_SCHEMA)


def decode_order_created_v2(payload: bytes) -> dict:
    return schemaless_reader(BytesIO(payload), ORDER_CREATED_SCHEMA, ORDER_CREATED_V2_SCHEMA)
