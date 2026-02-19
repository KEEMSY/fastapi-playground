"""
스케줄러 설정 및 작업 정의

APScheduler를 사용하여 주기적인 백그라운드 작업을 실행합니다.
나중에 Celery Beat으로 마이그레이션할 수 있도록 구조화되어 있습니다.
"""

import logging
from datetime import datetime
from functools import wraps
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.database.database import SessionLocal
from src.domains.scheduler.service import (
    create_job_history,
    update_job_history
)

logger = logging.getLogger(__name__)

# 전역 스케줄러 인스턴스
scheduler = AsyncIOScheduler()


def start_scheduler():
    """스케줄러 시작"""
    if scheduler.running:
        logger.warning("스케줄러가 이미 실행 중입니다.")
        return

    # 스케줄 작업 등록
    register_jobs()

    scheduler.start()
    logger.info("✅ 스케줄러 시작 완료")


def stop_scheduler():
    """스케줄러 종료"""
    if not scheduler.running:
        return

    scheduler.shutdown(wait=True)
    logger.info("🛑 스케줄러 종료 완료")


def register_jobs():
    """스케줄 작업 등록

    여기에 실행할 스케줄 작업들을 추가합니다.
    """

    # 테스트 작업: 1분마다 실행
    scheduler.add_job(
        test_job_every_minute,
        trigger=IntervalTrigger(minutes=1),
        id="test_job_every_minute",
        name="테스트 작업 (1분 간격)",
        replace_existing=True,
    )

    # 테스트 작업: 매일 새벽 2시 실행
    scheduler.add_job(
        test_job_daily_2am,
        trigger=CronTrigger(hour=2, minute=0),
        id="test_job_daily_2am",
        name="테스트 작업 (매일 새벽 2시)",
        replace_existing=True,
    )

    logger.info(f"📋 {len(scheduler.get_jobs())}개의 스케줄 작업 등록 완료")


# ===== 스케줄 작업 데코레이터 =====

def track_execution(job_id: str, job_name: str):
    """스케줄 작업 실행 이력을 DB에 저장하는 데코레이터

    Args:
        job_id: 작업 ID
        job_name: 작업 이름
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            db = SessionLocal()
            history = None

            try:
                # 실행 이력 생성 (status: running)
                history = create_job_history(
                    db=db,
                    job_id=job_id,
                    job_name=job_name,
                    status="running"
                )

                # 작업 실행
                result = await func(*args, **kwargs)

                # 성공 처리
                update_job_history(
                    db=db,
                    history_id=history.id,
                    status="success"
                )

                return result

            except Exception as e:
                logger.error(f"❌ [{job_name}] 실행 실패: {e}", exc_info=True)

                # 실패 처리
                if history:
                    update_job_history(
                        db=db,
                        history_id=history.id,
                        status="failed",
                        error_message=str(e)
                    )

                raise
            finally:
                db.close()

        return wrapper
    return decorator


# ===== 스케줄 작업 정의 =====

@track_execution("test_job_every_minute", "테스트 작업 (1분 간격)")
async def test_job_every_minute():
    """테스트 작업: 1분마다 실행"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"⏰ [1분 간격 작업] 실행 시간: {now}")
    print(f"⏰ [1분 간격 작업] 실행 시간: {now}")


@track_execution("test_job_daily_2am", "테스트 작업 (매일 새벽 2시)")
async def test_job_daily_2am():
    """테스트 작업: 매일 새벽 2시 실행"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"🌙 [매일 새벽 2시 작업] 실행 시간: {now}")
    print(f"🌙 [매일 새벽 2시 작업] 실행 시간: {now}")


# ===== 스케줄러 유틸리티 함수 =====

def get_scheduled_jobs():
    """등록된 모든 스케줄 작업 조회

    Returns:
        list: 작업 정보 목록 [{"id": ..., "name": ..., "next_run": ...}, ...]
    """
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return jobs


def run_job_now(job_id: str):
    """스케줄 작업 즉시 실행

    Args:
        job_id: 실행할 작업 ID

    Returns:
        bool: 성공 여부
    """
    job = scheduler.get_job(job_id)
    if not job:
        logger.error(f"작업을 찾을 수 없습니다: {job_id}")
        return False

    try:
        job.func()  # 작업 즉시 실행
        logger.info(f"✅ 작업 수동 실행 완료: {job_id}")
        return True
    except Exception as e:
        logger.error(f"❌ 작업 실행 실패: {job_id}, 에러: {e}")
        return False
