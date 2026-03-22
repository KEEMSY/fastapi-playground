"""
작업 함수 레지스트리

스케줄에서 실행할 수 있는 작업 함수들을 정의합니다.
모든 함수는 async이며, 자체 DB 세션을 생성합니다.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import httpx
from sqlalchemy import delete, select, func

from src.database.database import AsyncSessionPrimary
from src.domains.scheduler.models import ScheduledJobHistory

logger = logging.getLogger(__name__)

# 작업 유형 → 실행 함수 매핑
JOB_REGISTRY: dict[str, callable] = {}


def register_job(job_type: str):
    """작업 함수 등록 데코레이터"""

    def decorator(func):
        JOB_REGISTRY[job_type] = func
        return func

    return decorator


def get_job_func(job_type: str):
    """작업 유형에 해당하는 실행 함수 반환"""
    func = JOB_REGISTRY.get(job_type)
    if func is None:
        raise ValueError(f"등록되지 않은 작업 유형입니다: {job_type}")
    return func


@register_job("data_cleanup")
async def execute_data_cleanup(job_params: dict = None) -> str:
    """30일 이상 된 scheduled_job_history 삭제"""
    days = 30
    if job_params and "retention_days" in job_params:
        days = int(job_params["retention_days"])

    cutoff = datetime.utcnow() - timedelta(days=days)

    async with AsyncSessionPrimary() as db:
        count_stmt = select(func.count()).select_from(
            select(ScheduledJobHistory.id)
            .where(ScheduledJobHistory.created_at < cutoff)
            .subquery()
        )
        result = await db.execute(count_stmt)
        count = result.scalar_one()

        if count > 0:
            stmt = delete(ScheduledJobHistory).where(
                ScheduledJobHistory.created_at < cutoff
            )
            await db.execute(stmt)
            await db.commit()

    summary = f"{days}일 이전 이력 {count}건 삭제 완료"
    logger.info(f"[data_cleanup] {summary}")
    return summary


@register_job("api_sync")
async def execute_api_sync(job_params: dict = None) -> str:
    """외부 API 호출 (httpx 사용)"""
    url = "https://jsonplaceholder.typicode.com/posts/1"
    if job_params and "url" in job_params:
        url = job_params["url"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()

    summary = f"API 호출 성공: {url} (상태코드: {response.status_code})"
    logger.info(f"[api_sync] {summary}")
    return summary


@register_job("notification")
async def execute_notification(job_params: dict = None) -> str:
    """알림 시뮬레이션 (로거 사용)"""
    message = "기본 알림 메시지"
    if job_params and "message" in job_params:
        message = job_params["message"]

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    summary = f"알림 발송: {message} (시각: {now})"
    logger.info(f"[notification] {summary}")
    return summary


@register_job("sample_log")
async def execute_sample_log(job_params: dict = None) -> str:
    """단순 로그 출력"""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    label = "sample"
    if job_params and "label" in job_params:
        label = job_params["label"]

    summary = f"[{label}] 샘플 로그 실행: {now}"
    logger.info(f"[sample_log] {summary}")
    return summary
