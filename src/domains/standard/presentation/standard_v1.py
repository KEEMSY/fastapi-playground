import asyncio
import time
import os
import multiprocessing
import threading
from fastapi import APIRouter, Query

from src.common.constants import APIVersion
from src.common.presentation.response import BaseErrorResponse, BaseResponse
from src.common.presentation.router import create_versioned_router
from src.domains.standard.presentation.schemas.standard import StandardResponse
from src.utils import Logging

# V1 라우터 생성
router_v1 = create_versioned_router(
    prefix="standard",
    version=APIVersion.V1,
    tags=["standard-v1"],
    responses={
        400: {"model": BaseErrorResponse.BadRequestResponse},
        404: {"model": BaseErrorResponse.NotFoundResponse},
        422: {"model": BaseErrorResponse.InvalidRequestResponse},
        500: {"model": BaseErrorResponse.ServerErrorResponse},
    }
)

logger = Logging.__call__().get_logger(name=__name__, path="standard.py", isThread=True)


@router_v1.get(
    "/sync-test",
    response_model=BaseResponse[StandardResponse],
    summary="단순 동기 응답을 반환하는 API"
)
def sync_test():
    process_id = os.getpid()
    worker_id = multiprocessing.current_process().name
    thread_id = threading.current_thread().name
    
    logger.info(
        f"Request received - Process ID: {process_id}, "
        f"Worker: {worker_id}, Thread: {thread_id}"
    )
    
    logger.info("Test API")
    return BaseResponse(
        data=StandardResponse(
            message=f"test (PID: {process_id}, Worker: {worker_id}, Thread: {thread_id})"
        ),
    )


@router_v1.get(
    "/async-test",
    response_model=BaseResponse[StandardResponse],
    summary="단순 비동기 응답을 반환하는 API"
)
async def async_test():
    process_id = os.getpid()
    worker_id = multiprocessing.current_process().name
    thread_id = threading.current_thread().name
    
    logger.info(
        f"Request received - Process ID: {process_id}, "
        f"Worker: {worker_id}, Thread: {thread_id}"
    )
    
    logger.info("Test API")
    return BaseResponse(
        data=StandardResponse(
            message=f"test (PID: {process_id}, Worker: {worker_id}, Thread: {thread_id})"
        ),
    )


@router_v1.get(
    "/sync-test-with-await",
    response_model=BaseResponse[StandardResponse],
    summary="동기 대기 응답을 반환하는 API"
)
def sync_test_with_await(
    timeout: int = Query(
        default=1,
        ge=1,
        le=10,
        description="대기 시간 (초)"
    )
):
    process_id = os.getpid()
    worker_id = multiprocessing.current_process().name
    thread_id = threading.current_thread().name
    
    logger.info(
        f"Request received - Process ID: {process_id}, "
        f"Worker: {worker_id}, Thread: {thread_id}"
    )
    
    logger.info(f"Waiting for {timeout} seconds")
    time.sleep(timeout)
    logger.info("Done")
    
    return BaseResponse(
        data=StandardResponse(
            message=f"test (PID: {process_id}, Worker: {worker_id}, Thread: {thread_id})"
        ),
    )
    
@router_v1.get(
    "/async-test-with-await",
    response_model=BaseResponse[StandardResponse],
    summary="비동기 대기 응답을 반환하는 API"
)
async def async_test_with_await(
    timeout: int = Query(
        default=1,
        ge=1,
        le=10,
        description="대기 시간 (초)"
    )
):
    process_id = os.getpid()
    worker_id = multiprocessing.current_process().name
    thread_id = threading.current_thread().name
    
    logger.info(
        f"Request received - Process ID: {process_id}, "
        f"Worker: {worker_id}, Thread: {thread_id}"
    )
    
    logger.info(f"Waiting for {timeout} seconds")
    await asyncio.sleep(timeout)
    
    logger.info(
        f"Done - Process ID: {process_id}, "
        f"Worker: {worker_id}, Thread: {thread_id}"
    )
    
    return BaseResponse(
        data=StandardResponse(
            message=f"test (PID: {process_id}, Worker: {worker_id}, Thread: {thread_id})"
        ),
    )

@router_v1.get(
    "/async-test-with-await-with-sync",
    response_model=BaseResponse[StandardResponse],
    summary="비동기 메서드 내 동기 대기 응답을 반환하는 API",
    description="비동기 메서드 내 동기 대기 응답을 사용하는 경우, 메인 스레드를 블로킹하여 비동기 효과를 무효화할 수 있습니다"
)
async def async_test_with_await_with_sync(
    timeout: int = Query(
        default=1,
        ge=1,
        le=10,
        description="대기 시간 (초)"
    )
):
    process_id = os.getpid()
    worker_id = multiprocessing.current_process().name
    thread_id = threading.current_thread().name
    
    logger.info(
        f"Request received - Process ID: {process_id}, "
        f"Worker: {worker_id}, Thread: {thread_id}"
    )
    
    logger.info(f"Waiting for {timeout} seconds")
    time.sleep(timeout)
    
    logger.info(
        f"Done - Process ID: {process_id}, "
        f"Worker: {worker_id}, Thread: {thread_id}"
    )
    
    return BaseResponse(
        data=StandardResponse(
            message=f"test (PID: {process_id}, Worker: {worker_id}, Thread: {thread_id})"
        ),
    )
