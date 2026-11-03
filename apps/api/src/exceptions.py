from functools import wraps
from typing import Optional

from aioredis import RedisError as AsyncRedisError
from pydantic import ValidationError
from redis import RedisError as SyncRedisError
from sqlalchemy.exc import SQLAlchemyError

"""
각 계층 별 에러는 각 계층에서 예상하지 못한 에러가 발생할 경우, 계층 별 에러를 발생시킨다.
"""


class PLException(Exception):
    def __init__(self, detail: Optional[str], status_code: int = 500, code: str = "D0000"):
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class BLException(Exception):
    def __init__(self, detail: Optional[str], code: str = "B0000"):
        self.code = code
        self.detail = detail
        super().__init__(detail)


class DLException(Exception):
    def __init__(self, detail: Optional[str], code: str = "D0000"):
        self.code = code
        self.detail = detail
        super().__init__(detail)


class ExceptionResponse(Exception):
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code


def handle_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        session = kwargs.get('db') if 'db' in kwargs else None
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            raise ExceptionResponse(
                message=f"데이터 검증 에러가 발생 했습니다.: {str(e)}", error_code="V0000"
            )
        except SQLAlchemyError as e:
            if session:
                session.rollback()
            raise ExceptionResponse(
                message=f"데이터베이스 에러가 발생 했습니다.: {str(e)}", error_code="D0000"
            )
        except SyncRedisError as e:
            raise ExceptionResponse(
                message=f"SyncRedisError 에러가 발생 했습니다.: {str(e)}", error_code="R0000"
            )
        except AsyncRedisError as e:
            raise ExceptionResponse(
                message=f"AsyncRedisError 에러가 발생 했습니다.: {str(e)}", error_code="R0000"
            )
        except Exception as e:
            if session:
                session.rollback()
            raise ExceptionResponse(
                message=f"예측 하지 못한 에러가 발생 했습니다.: {str(e)}", error_code="E0000"
            )

    return wrapper
