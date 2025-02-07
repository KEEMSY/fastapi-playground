from enum import Enum
from datetime import datetime
from typing import Optional, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class ResultCode(Enum):
    SUCCESS = ("success", "정상 처리 되었습니다.")
    ERROR = ("error", "에러가 발생했습니다.")
    VALIDATION_ERROR = ("validation_error", "입력값이 올바르지 않습니다.")
    NOT_FOUND = ("not_found", "요청한 리소스를 찾을 수 없습니다.")
    FORBIDDEN = ("forbidden", "권한이 없습니다.")
    UNAUTHORIZED = ("unauthorized", "인증이 필요합니다.")
    SERVER_ERROR = ("server_error", "서버 오류가 발생했습니다.")
    DATABASE_ERROR = ("database_error", "데이터베이스 오류가 발생했습니다.")
    def __init__(self, code: str, message: str):
        self._code = code
        self._message = message

    @property
    def code(self) -> str:
        return self._code

    @property
    def message(self) -> str:
        return self._message

class BaseResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    result: str = Field(
        default=ResultCode.SUCCESS.code, description="작업의 결과 코드를 반환 합니다."
    )
    message: str = Field(
        default=ResultCode.SUCCESS.message,
        description="작업의 결과 메세지를 반환합니다.",
    )
    data: Optional[T] = Field(
        default=None, description="작업 결과 데이터를 반환합니다."
    )

class BaseErrorResponse(BaseModel):
    """기본 에러 응답 클래스
    
    FastAPI의 responses 파라미터에서 사용되는 에러 응답 예시들을 정의합니다.
    각 에러 타입별로 미리 정의된 응답 형식을 제공합니다.
    
    Examples:
        @app.get("/items/{item_id}",
                responses={
                    401: {"model": BaseErrorResponse.UnauthorizedResponse},
                    404: {"model": BaseErrorResponse.NotFoundResponse},
                    500: {"model": BaseErrorResponse.ServerErrorResponse}
                })
    """
    result: str = Field(description="작업의 결과 코드를 반환 합니다.")
    message: str = Field(description="에러 메세지를 반환합니다.")
    status_code: int = Field(description="HTTP 상태 코드")

    class BadRequestResponse(BaseModel):
        """잘못된 요청 파라미터 에러 응답"""
        result: str = Field(default=ResultCode.VALIDATION_ERROR.code)
        message: str = Field(default=ResultCode.VALIDATION_ERROR.message)
        status_code: int = Field(default=400)

    class UnauthorizedResponse(BaseModel):
        """인증 실패 에러 응답"""
        result: str = Field(default=ResultCode.UNAUTHORIZED.code)
        message: str = Field(default=ResultCode.UNAUTHORIZED.message)
        status_code: int = Field(default=401)

    class ForbiddenResponse(BaseModel):
        """권한 없음 에러 응답"""
        result: str = Field(default=ResultCode.FORBIDDEN.code)
        message: str = Field(default=ResultCode.FORBIDDEN.message)
        status_code: int = Field(default=403)

    class NotFoundResponse(BaseModel):
        """리소스를 찾을 수 없는 경우의 에러 응답"""
        result: str = Field(default=ResultCode.NOT_FOUND.code)
        message: str = Field(default=ResultCode.NOT_FOUND.message)
        status_code: int = Field(default=404)

    class InvalidRequestResponse(BaseModel):
        """잘못된 요청 파라미터 에러 응답"""
        result: str = Field(default=ResultCode.VALIDATION_ERROR.code)
        message: str = Field(default=ResultCode.VALIDATION_ERROR.message)
        status_code: int = Field(default=422)
    
    class ServerErrorResponse(BaseModel):
        """서버 내부 에러 응답"""
        result: str = Field(default=ResultCode.SERVER_ERROR.code)
        message: str = Field(default=ResultCode.SERVER_ERROR.message)
        status_code: int = Field(default=500)

    class DatabaseErrorResponse(BaseModel):
        """데이터베이스 관련 에러 응답"""
        result: str = Field(default=ResultCode.DATABASE_ERROR.code)
        message: str = Field(default=ResultCode.DATABASE_ERROR.message)
        status_code: int = Field(default=500)



    