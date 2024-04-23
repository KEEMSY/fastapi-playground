from enum import Enum


class BLErrorCode(str, Enum):
    UNKNOWN_ERROR = "B0000"
    UNAUTHORIZED = "B0001"
    OPERATION_NOT_ALLOWED = "B0002"


class DLErrorCode(str, Enum):
    UNKNOWN_ERROR = "D0000"
    DATABASE_ERROR = "D0001"
    NOT_FOUND = "D0002"
    VALIDATION_ERROR = "D0003"
