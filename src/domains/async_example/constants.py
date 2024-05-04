from enum import Enum


class ErrorCode(str, Enum):
    UNKNOWN_ERROR = "0000"
    NOT_FOUND = "0001"
    VALIDATION_ERROR = "0002"
    DUPLICATE_ERROR = "0003"
    CONSTRAINT_ERROR = "0004"
    DATABASE_ERROR = "0005"


class BLErrorCode(str, Enum):
    UNKNOWN_ERROR = "B0000"
    UNAUTHORIZED = "B0001"
    OPERATION_NOT_ALLOWED = "B0002"


class DLErrorCode(str, Enum):
    UNKNOWN_ERROR = "D0000"
    DATABASE_ERROR = "D0001"
    NOT_FOUND = "D0002"
    VALIDATION_ERROR = "D0003"
