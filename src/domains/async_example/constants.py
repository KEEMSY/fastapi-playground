from enum import Enum


# .env 내 ENVIRONMENT 설정에 따라 환경을 구분한다.
class Environment(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING"
    PRODUCTION = "PRODUCTION"

    @property
    def is_debug(self):
        return self in (self.DEVELOPMENT, self.TESTING)

    @property
    def is_testing(self):
        return self == self.TESTING

    @property
    def is_deployed(self) -> bool:
        return self in self.PRODUCTION


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
