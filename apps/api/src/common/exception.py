from http import HTTPStatus
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from src.main import app
from src.common.presentation.response import BaseErrorResponse, ResultCode


@app.exception_handler(HTTPException)
async def http_exception_handler(exception_instance: HTTPException):
    """FastAPI HTTPException handler
    일반적인 HTTP 예외를 처리합니다.
    """
    return JSONResponse(
        status_code=exception_instance.status_code,
        content={
            "result": ResultCode.ERROR.code,
            "message": exception_instance.detail,
            "data": {
                "error_type": type(exception_instance).__name__,
                "error_detail": str(exception_instance),
            },
        },
    )


@app.exception_handler(BaseErrorResponse)
async def base_error_response_handler(exception_instance: BaseErrorResponse):
    """
    custom exception handler
    """
    return JSONResponse(
        status_code=exception_instance.status_code,
        content={
            "result": exception_instance.result,
            "message": exception_instance.message,
            "data": exception_instance.data,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(exception_instance: SQLAlchemyError):
    """SQLAlchemy exception handler
    데이터베이스 관련 예외를 처리합니다.
    """ 
    # original exception
    if hasattr(exception_instance, "orig"):
        return JSONResponse(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
            content={
                "result": ResultCode.DATABASE_ERROR.code,
                "message": "데이터베이스 오류가 발생했습니다.",
                "data": {
                    "error_type": type(exception_instance.orig).__name__,
                    "error_detail": str(exception_instance.orig),
                },
            },
        )
    # default exception
    return JSONResponse(
        status_code=HTTPStatus.SERVICE_UNAVAILABLE.value,
        content={
            "result": ResultCode.DATABASE_ERROR.code,
            "message": "데이터베이스 오류가 발생했습니다.",
            "data": {
                "error_type": type(exception_instance).__name__,
                "error_detail": str(exception_instance),
            },
        },
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(exception_instance: StarletteHTTPException):
    """Starlette HTTPException handler
    HTTP 상태 코드별로 적절한 에러 메시지를 반환합니다.
    """
    status_code = exception_instance.status_code
    error_messages = {
        HTTPStatus.UNAUTHORIZED.value: "인증이 필요합니다.",
        HTTPStatus.NOT_FOUND.value: "요청한 리소스를 찾을 수 없습니다.",
        HTTPStatus.METHOD_NOT_ALLOWED.value: "허용되지 않는 메서드입니다.",
        HTTPStatus.BAD_REQUEST.value: "잘못된 요청입니다.",
        HTTPStatus.SERVICE_UNAVAILABLE.value: "외부 서버 오류가 발생했습니다.",
        HTTPStatus.FORBIDDEN.value: "접근 권한이 없습니다.",
        HTTPStatus.CONFLICT.value: "요청이 충돌했습니다.",
        HTTPStatus.REQUEST_TIMEOUT.value: "요청 시간이 초과했습니다.",
        HTTPStatus.GONE.value: "요청한 리소스가 삭제되었습니다.",
        HTTPStatus.TOO_MANY_REQUESTS.value: "너무 많은 요청이 발생했습니다.",
    }
    
    error_message = error_messages.get(status_code, "서버 오류가 발생했습니다.")

    return JSONResponse(
        status_code=status_code,
        content={
            "result": ResultCode.ERROR.code,
            "message": error_message,
            "data": {
                "error_type": type(exception_instance).__name__,
                "error_detail": str(exception_instance.detail),
            },
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(exception_instance: Exception):
    """General exception handler
    처리되지 않은 모든 예외를 처리합니다.
    """
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
        content={
            "result": ResultCode.SERVER_ERROR.code,
            "message": "예기치 않은 서버 오류가 발생했습니다.",
            "data": {
                "error_type": type(exception_instance).__name__,
                "error_detail": str(exception_instance),
            },
        },
    )
