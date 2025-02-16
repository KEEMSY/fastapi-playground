import asyncio
import time
import os
import multiprocessing
import threading
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.constants import APIVersion
from src.common.presentation.response import BaseErrorResponse, BaseResponse
from src.common.presentation.router import create_versioned_router
from src.domains.standard.presentation.schemas.standard import StandardResponse, StandardDbResponse, DatabaseSessionInfo
from src.utils import Logging
from src.database.database import get_db, get_async_db, async_engine

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
    "/sync-test-with-wait",
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

@router_v1.get(
    "/async-test-with-await-with-async",
    response_model=BaseResponse[StandardResponse],
    summary="비동기 메서드 내 비동기 대기 응답을 반환하는 API",
    description="비동기 메서드 내 동기 대기 응답을 사용하는 경우, 메인 스레드를 블로킹하여 비동기 효과를 무효화할 수 있습니다"
)
async def async_test_with_await_with_async(
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
    "/sync-test-with-sync-db-session",
    response_model=BaseResponse[StandardDbResponse],
    description="동기 메서드 내 동기 db session 사용 API",
    summary="동기 메서드 내 동기 db session 사용 API"
)
def sync_test_with_sync(
    timeout: int = Query(
        default=1,
        ge=1,
        le=10,
        description="대기 시간 (초)"
    ),
    db: Session = Depends(get_db)
):
    process_id = os.getpid()
    worker_id = multiprocessing.current_process().name
    thread_id = threading.current_thread().name
    
    # MySQL용 연결 정보 조회
    result = db.execute(text("""
        SELECT 
            COUNT(*) as total_connections,
            SUM(CASE WHEN COMMAND != 'Sleep' THEN 1 ELSE 0 END) as active_connections
        FROM information_schema.PROCESSLIST
    """))
    db_stats = result.mappings().first()
    
    # MySQL 상태 정보 조회
    result = db.execute(text("""
        SHOW GLOBAL STATUS 
        WHERE Variable_name IN 
        ('Threads_connected', 'Threads_running', 'Max_used_connections')
    """))
    additional_stats = {row[0]: row[1] for row in result}
    
    # 대기 쿼리 실행
    logger.info(f"Waiting for {timeout} seconds")
    db.execute(text("SELECT SLEEP(:timeout)"), {"timeout": timeout})
    
    session_info = DatabaseSessionInfo(
        total_connections=db_stats["total_connections"],
        active_connections=db_stats["active_connections"],
        threads_connected=additional_stats.get("Threads_connected", "0"),
        threads_running=additional_stats.get("Threads_running", "0"),
        max_used_connections=additional_stats.get("Max_used_connections", "0")
    )
    
    return BaseResponse(
        data=StandardDbResponse(
            message=f"test (PID: {process_id}, Worker: {worker_id}, Thread: {thread_id})",
            session_info=session_info
        ),
    )


@router_v1.get(
    "/async-test-with-async-db-session",
    response_model=BaseResponse[StandardDbResponse],
    description="비동기 메서드 내 비동기 db session 사용 API",
    summary="비동기 메서드 내 비동기 db session 사용 API"
)
async def async_test_with_async_db_session(
    timeout: int = Query(
        default=1,
        ge=1,
        le=10,
        description="대기 시간 (초)"
    ),
    db: AsyncSession = Depends(get_async_db)
):
    process_id = os.getpid()
    worker_id = multiprocessing.current_process().name
    thread_id = threading.current_thread().name
    
    # 현재 데이터베이스 연결 정보 조회
    async with async_engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT 
                COUNT(*) as total_connections,
                SUM(CASE WHEN COMMAND != 'Sleep' THEN 1 ELSE 0 END) as active_connections
            FROM information_schema.PROCESSLIST
        """))
        
        db_stats = result.mappings().first()
        
        # 추가 세션 정보 조회
        result = await conn.execute(text("""
            SHOW GLOBAL STATUS 
            WHERE Variable_name IN 
            ('Threads_connected', 'Threads_running', 'Max_used_connections')
        """))
        additional_stats = {row[0]: row[1] for row in result}
    
    # 대기 쿼리 실행
    logger.info(f"Waiting for {timeout} seconds")
    await db.execute(text("SELECT SLEEP(:timeout)"), {"timeout": timeout})
    
    session_info = DatabaseSessionInfo(
        total_connections=db_stats["total_connections"],
        active_connections=db_stats["active_connections"],
        threads_connected=additional_stats.get("Threads_connected", "0"),
        threads_running=additional_stats.get("Threads_running", "0"),
        max_used_connections=additional_stats.get("Max_used_connections", "0")
    )
    
    return BaseResponse(
        data=StandardDbResponse(
            message=f"test (PID: {process_id}, Worker: {worker_id}, Thread: {thread_id})",
            session_info=session_info
        ),
    )

@router_v1.get(
    "/async-test-with-async-db-session-with-sync",
    response_model=BaseResponse[StandardDbResponse],
    description="비동기 메서드 내 동기 db session 사용 API",
    summary="비동기 메서드 내 동기 db session 사용 API"
)
async def async_test_with_async_db_session_with_sync(
    timeout: int = Query(
        default=1,
        ge=1,
        le=10,
        description="대기 시간 (초)"
    ),
    db: Session = Depends(get_db)
):
    process_id = os.getpid()
    worker_id = multiprocessing.current_process().name
    thread_id = threading.current_thread().name
    
    # MySQL용 연결 정보 조회
    result = db.execute(text("""
        SELECT 
            COUNT(*) as total_connections,
            SUM(CASE WHEN COMMAND != 'Sleep' THEN 1 ELSE 0 END) as active_connections
        FROM information_schema.PROCESSLIST
    """))
    db_stats = result.mappings().first()
    
    # MySQL 상태 정보 조회
    result = db.execute(text("""
        SHOW GLOBAL STATUS 
        WHERE Variable_name IN 
        ('Threads_connected', 'Threads_running', 'Max_used_connections')
    """))
    additional_stats = {row[0]: row[1] for row in result}
    
    # 대기 쿼리 실행
    logger.info(f"Waiting for {timeout} seconds")
    db.execute(text("SELECT SLEEP(:timeout)"), {"timeout": timeout})
    
    session_info = DatabaseSessionInfo(
        total_connections=db_stats["total_connections"],
        active_connections=db_stats["active_connections"],
        threads_connected=additional_stats.get("Threads_connected", "0"),
        threads_running=additional_stats.get("Threads_running", "0"),
        max_used_connections=additional_stats.get("Max_used_connections", "0")
    )
    
    return BaseResponse(
        data=StandardDbResponse(
            message=f"test (PID: {process_id}, Worker: {worker_id}, Thread: {thread_id})",
            session_info=session_info
        ),
    )    
