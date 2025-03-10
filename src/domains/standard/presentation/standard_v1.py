import asyncio
import time
import os
import multiprocessing
import threading
import random
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.constants import APIVersion
from src.common.presentation.response import BaseErrorResponse, BaseResponse
from src.common.presentation.router import create_versioned_router
from src.domains.standard.presentation.schemas.standard import StandardResponse, StandardDbResponse, DatabaseSessionInfo, PoolInfo, QueryExecutionInfo
from src.utils import Logging
from src.database.database import get_db, get_async_db, async_engine
from src.domains.standard.database.standard_repository import StandardRepository
from src.domains.standard.database.standard_async_repository import StandardAsyncRepository

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
    
    # Repository 생성
    repo = StandardRepository(db)
    
    # 데이터베이스 정보 조회
    session_info, pool_info = repo.get_database_info()
    
    # 로그 기록
    logger.info(f"Connection Pool Status - Max: {pool_info.max_connections}, "
                f"Current: {pool_info.current_connections}, "
                f"Available: {pool_info.available_connections}, "
                f"Wait Timeout: {pool_info.wait_timeout}s")
    
    # 대기 쿼리 실행
    logger.info(f"Waiting for {timeout} seconds")
    repo.execute_sleep_query(timeout)
    
    return BaseResponse(
        data=StandardDbResponse(
            message=f"test (PID: {process_id}, Worker: {worker_id}, Thread: {thread_id})",
            session_info=session_info,
            pool_info=pool_info
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
    
    # Repository 생성
    repo = StandardAsyncRepository(db)
    
    # 데이터베이스 정보 조회
    logger.info(f"Checking async connection pool status before query execution")
    session_info, pool_info = await repo.get_database_info()
    
    # 로그 기록
    logger.info(f"Connection Pool Status - Max: {pool_info.max_connections}, "
                f"Current: {pool_info.current_connections}, "
                f"Available: {pool_info.available_connections}, "
                f"Wait Timeout: {pool_info.wait_timeout}s")
    
    # 대기 쿼리 실행
    logger.info(f"Waiting for {timeout} seconds")
    await repo.execute_sleep_query(timeout)
    
    return BaseResponse(
        data=StandardDbResponse(
            message=f"test (PID: {process_id}, Worker: {worker_id}, Thread: {thread_id})",
            session_info=session_info,
            pool_info=pool_info
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
    
    # Repository 생성
    repo = StandardRepository(db)
    
    # 데이터베이스 정보 조회
    logger.info(f"Checking connection pool status before query execution")
    session_info, pool_info = repo.get_database_info()
    
    # 로그 기록
    logger.info(f"Connection Pool Status - Max: {pool_info.max_connections}, "
                f"Current: {pool_info.current_connections}, "
                f"Available: {pool_info.available_connections}, "
                f"Wait Timeout: {pool_info.wait_timeout}s")
    
    # 대기 쿼리 실행 (비동기 메서드에서 동기 실행)
    logger.info(f"Waiting for {timeout} seconds")
    repo.execute_sleep_query(timeout)
    
    return BaseResponse(
        data=StandardDbResponse(
            message=f"test (PID: {process_id}, Worker: {worker_id}, Thread: {thread_id})",
            session_info=session_info,
            pool_info=pool_info
        ),
    )    

@router_v1.get(
    "/sync-test-with-sync-db-session-multiple-queries",
    response_model=BaseResponse[StandardDbResponse],
    description="동기 메서드 내 여러 개의 랜덤 지연시간 쿼리 실행 API",
    summary="동기 메서드 내 여러 개의 랜덤 지연시간 쿼리 실행 API"
)
def sync_test_with_sync_multiple_queries(
    query_count: int = Query(
        default=3,
        ge=1,
        le=10,
        description="실행할 쿼리 횟수"
    ),
    db: Session = Depends(get_db)
):
    process_id = os.getpid()
    worker_id = multiprocessing.current_process().name
    thread_id = threading.current_thread().name
    
    # Repository 생성
    repo = StandardRepository(db)
    
    # 데이터베이스 정보 조회
    session_info, pool_info = repo.get_database_info()
    
    # 쿼리 실행 정보를 저장할 리스트
    query_executions = []
    
    # 여러 개의 랜덤 지연시간 쿼리 실행
    logger.info(f"Executing {query_count} queries with random delay")
    for i in range(query_count):
        delay = round(random.uniform(0.01, 10), 2)  # 0.01초에서 10초 사이의 랜덤 지연
        logger.info(f"Query {i+1}/{query_count}: Executing with {delay}s delay")
        
        # 쿼리 실행 시간 측정 시작
        start_time = time.time()
        repo.execute_sleep_query(delay)
        end_time = time.time()
        actual_duration = round(end_time - start_time, 3)
        
        # 쿼리 실행 정보 저장
        query_executions.append(QueryExecutionInfo(
            query_number=i+1,
            delay_seconds=delay,
            actual_duration_seconds=actual_duration
        ))
        
        logger.info(f"Query {i+1}/{query_count}: Completed in {actual_duration}s (planned delay: {delay}s)")
    
    return BaseResponse(
        data=StandardDbResponse(
            message=f"test (PID: {process_id}, Worker: {worker_id}, Thread: {thread_id})",
            session_info=session_info,
            pool_info=pool_info,
            query_executions=query_executions
        ),
    )


@router_v1.get(
    "/async-test-with-async-db-session-multiple-queries",
    response_model=BaseResponse[StandardDbResponse],
    description="비동기 메서드 내 여러 개의 랜덤 지연시간 쿼리 실행 API",
    summary="비동기 메서드 내 여러 개의 랜덤 지연시간 쿼리 실행 API"
)
async def async_test_with_async_db_session_multiple_queries(
    query_count: int = Query(
        default=3,
        ge=1,
        le=10,
        description="실행할 쿼리 횟수"
    ),
    db: AsyncSession = Depends(get_async_db)
):
    process_id = os.getpid()
    worker_id = multiprocessing.current_process().name
    thread_id = threading.current_thread().name
    
    # Repository 생성
    repo = StandardAsyncRepository(db)
    
    # 데이터베이스 정보 조회
    logger.info(f"Checking async connection pool status before query execution")
    session_info, pool_info = await repo.get_database_info()
    
    # 쿼리 실행 정보를 저장할 리스트
    query_executions = []
    
    # 여러 개의 랜덤 지연시간 쿼리 실행
    logger.info(f"Executing {query_count} queries with random delay")
    for i in range(query_count):
        # delay = round(random.uniform(0.01, 10), 2)  # 0.01초에서 10초 사이의 랜덤 지연
        delay = round(random.uniform(0.01,2), 2)  # 0.01초에서 10초 사이의 랜덤 지연
        logger.info(f"Query {i+1}/{query_count}: Executing with {delay}s delay")
        
        # 쿼리 실행 시간 측정 시작
        start_time = time.time()
        await repo.execute_sleep_query(delay)
        end_time = time.time()
        actual_duration = round(end_time - start_time, 3)
        
        # 쿼리 실행 정보 저장
        query_executions.append(QueryExecutionInfo(
            query_number=i+1,
            delay_seconds=delay,
            actual_duration_seconds=actual_duration
        ))
        
        logger.info(f"Query {i+1}/{query_count}: Completed in {actual_duration}s (planned delay: {delay}s)")
    
    return BaseResponse(
        data=StandardDbResponse(
            message=f"test (PID: {process_id}, Worker: {worker_id}, Thread: {thread_id})",
            session_info=session_info,
            pool_info=pool_info,
            query_executions=query_executions
        ),
    )


@router_v1.get(
    "/async-test-with-sync-db-session-multiple-queries",
    response_model=BaseResponse[StandardDbResponse],
    description="비동기 메서드 내 동기 DB 세션으로 여러 개의 랜덤 지연시간 쿼리 실행 API",
    summary="비동기 메서드 내 동기 DB 세션으로 여러 개의 랜덤 지연시간 쿼리 실행 API"
)
async def async_test_with_sync_db_session_multiple_queries(
    query_count: int = Query(
        default=3,
        ge=1,
        le=10,
        description="실행할 쿼리 횟수"
    ),
    db: Session = Depends(get_db)
):
    process_id = os.getpid()
    worker_id = multiprocessing.current_process().name
    thread_id = threading.current_thread().name
    
    # Repository 생성
    repo = StandardRepository(db)
    
    # 데이터베이스 정보 조회
    logger.info(f"Checking connection pool status before query execution")
    session_info, pool_info = repo.get_database_info()
    
    # 쿼리 실행 정보를 저장할 리스트
    query_executions = []
    
    # 여러 개의 랜덤 지연시간 쿼리 실행
    logger.info(f"Executing {query_count} queries with random delay")
    for i in range(query_count):
        delay = round(random.uniform(0.01, 10), 2)  # 0.01초에서 10초 사이의 랜덤 지연
        logger.info(f"Query {i+1}/{query_count}: Executing with {delay}s delay")
        
        # 쿼리 실행 시간 측정 시작
        start_time = time.time()
        repo.execute_sleep_query(delay)
        end_time = time.time()
        actual_duration = round(end_time - start_time, 3)
        
        # 쿼리 실행 정보 저장
        query_executions.append(QueryExecutionInfo(
            query_number=i+1,
            delay_seconds=delay,
            actual_duration_seconds=actual_duration
        ))
        
        logger.info(f"Query {i+1}/{query_count}: Completed in {actual_duration}s (planned delay: {delay}s)")
    
    return BaseResponse(
        data=StandardDbResponse(
            message=f"test (PID: {process_id}, Worker: {worker_id}, Thread: {thread_id})",
            session_info=session_info,
            pool_info=pool_info,
            query_executions=query_executions
        ),
    )    
