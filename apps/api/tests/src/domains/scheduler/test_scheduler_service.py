"""
스케줄러 서비스 단위 테스트

서비스 레이어의 비즈니스 로직을 DB 세션과 함께 검증합니다.
- 실행 이력 CRUD
- 트리거 파싱 및 검증 로직
- 스케줄 작업 등록/해제 로직
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from src.domains.scheduler.models import ScheduledJobHistory
from src.domains.scheduler.service import (
    create_job_history,
    update_job_history,
    get_job_histories,
)


# ======================================================================
# 실행 이력 서비스 테스트 (기존 동기 서비스)
# ======================================================================


class TestJobHistoryService:
    """실행 이력 서비스 테스트"""

    def test_create_job_history_정상(self, db_session):
        """실행 이력 생성 - running 상태"""
        # given, when
        history = create_job_history(
            db=db_session,
            job_id="test_job",
            job_name="테스트 작업",
            status="running",
        )

        # then
        assert history.id is not None
        assert history.job_id == "test_job"
        assert history.job_name == "테스트 작업"
        assert history.status == "running"
        assert history.started_at is not None
        assert history.finished_at is None

    def test_update_job_history_성공(self, db_session):
        """실행 이력 업데이트 - success"""
        # given
        history = create_job_history(
            db=db_session,
            job_id="update_test",
            job_name="업데이트 테스트",
            status="running",
        )

        # when
        updated = update_job_history(
            db=db_session,
            history_id=history.id,
            status="success",
        )

        # then
        assert updated.status == "success"
        assert updated.finished_at is not None
        assert updated.duration_seconds is not None
        assert updated.error_message is None

    def test_update_job_history_실패(self, db_session):
        """실행 이력 업데이트 - failed with error message"""
        # given
        history = create_job_history(
            db=db_session,
            job_id="fail_test",
            job_name="실패 테스트",
            status="running",
        )

        # when
        updated = update_job_history(
            db=db_session,
            history_id=history.id,
            status="failed",
            error_message="ConnectionError: 외부 API 연결 실패",
        )

        # then
        assert updated.status == "failed"
        assert updated.finished_at is not None
        assert updated.error_message == "ConnectionError: 외부 API 연결 실패"

    def test_update_job_history_존재하지_않는_이력(self, db_session):
        """존재하지 않는 이력 업데이트 시 None 반환"""
        # given, when
        result = update_job_history(
            db=db_session,
            history_id=999999,
            status="success",
        )

        # then
        assert result is None

    def test_get_job_histories_전체_조회(self, db_session):
        """전체 이력 조회"""
        # given
        create_job_history(db_session, "job_a", "작업 A", "success")
        create_job_history(db_session, "job_b", "작업 B", "failed")
        create_job_history(db_session, "job_a", "작업 A", "success")

        # when
        histories = get_job_histories(db=db_session)

        # then
        assert len(histories) >= 3

    def test_get_job_histories_job_id_필터(self, db_session):
        """job_id로 필터링 조회"""
        # given
        create_job_history(db_session, "filter_job_x", "작업 X", "success")
        create_job_history(db_session, "filter_job_y", "작업 Y", "success")
        create_job_history(db_session, "filter_job_x", "작업 X", "failed")

        # when
        histories = get_job_histories(db=db_session, job_id="filter_job_x")

        # then
        assert all(h.job_id == "filter_job_x" for h in histories)
        assert len(histories) >= 2

    def test_get_job_histories_status_필터(self, db_session):
        """status로 필터링 조회"""
        # given
        create_job_history(db_session, "status_test", "상태 테스트", "success")
        create_job_history(db_session, "status_test", "상태 테스트", "failed")

        # when
        successes = get_job_histories(db=db_session, status="success")

        # then
        assert all(h.status == "success" for h in successes)

    def test_get_job_histories_페이지네이션(self, db_session):
        """limit, offset으로 페이지네이션"""
        # given
        for i in range(10):
            create_job_history(db_session, f"page_job_{i}", f"페이지 테스트 {i}", "success")

        # when
        page1 = get_job_histories(db=db_session, limit=3, offset=0)
        page2 = get_job_histories(db=db_session, limit=3, offset=3)

        # then
        assert len(page1) == 3
        assert len(page2) == 3
        # 서로 다른 결과인지 확인
        page1_ids = {h.id for h in page1}
        page2_ids = {h.id for h in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_get_job_histories_정렬순서(self, db_session):
        """이력이 created_at 내림차순으로 정렬되는지 확인"""
        # given
        create_job_history(db_session, "order_test", "정렬 테스트 1", "success")
        create_job_history(db_session, "order_test", "정렬 테스트 2", "success")
        create_job_history(db_session, "order_test", "정렬 테스트 3", "success")

        # when
        histories = get_job_histories(db=db_session, job_id="order_test")

        # then
        for i in range(len(histories) - 1):
            assert histories[i].created_at >= histories[i + 1].created_at


# ======================================================================
# track_execution 데코레이터 테스트
# ======================================================================


class TestTrackExecutionDecorator:
    """track_execution 데코레이터 단위 테스트"""

    @pytest.mark.asyncio
    async def test_track_execution_성공시_이력_저장(self):
        """데코레이터가 성공 시 running → success로 이력을 저장하는지 확인"""
        # given
        mock_db = MagicMock()
        mock_history = MagicMock()
        mock_history.id = 1

        with patch(
            "src.common.scheduler.SessionLocal", return_value=mock_db
        ), patch(
            "src.common.scheduler.create_job_history", return_value=mock_history
        ) as mock_create, patch(
            "src.common.scheduler.update_job_history"
        ) as mock_update:
            from src.common.scheduler import track_execution

            @track_execution("test_job", "테스트 작업")
            async def sample_job():
                return "done"

            # when
            result = await sample_job()

            # then
            mock_create.assert_called_once_with(
                db=mock_db,
                job_id="test_job",
                job_name="테스트 작업",
                status="running",
            )
            mock_update.assert_called_once_with(
                db=mock_db,
                history_id=1,
                status="success",
            )
            assert result == "done"

    @pytest.mark.asyncio
    async def test_track_execution_실패시_이력_저장(self):
        """데코레이터가 실패 시 running → failed로 이력을 저장하는지 확인"""
        # given
        mock_db = MagicMock()
        mock_history = MagicMock()
        mock_history.id = 1

        with patch(
            "src.common.scheduler.SessionLocal", return_value=mock_db
        ), patch(
            "src.common.scheduler.create_job_history", return_value=mock_history
        ), patch(
            "src.common.scheduler.update_job_history"
        ) as mock_update:
            from src.common.scheduler import track_execution

            @track_execution("fail_job", "실패 작업")
            async def failing_job():
                raise ValueError("작업 실행 중 에러 발생")

            # when, then
            with pytest.raises(ValueError, match="작업 실행 중 에러 발생"):
                await failing_job()

            mock_update.assert_called_once_with(
                db=mock_db,
                history_id=1,
                status="failed",
                error_message="작업 실행 중 에러 발생",
            )

    @pytest.mark.asyncio
    async def test_track_execution_db_세션_정리(self):
        """데코레이터가 항상 DB 세션을 close하는지 확인"""
        # given
        mock_db = MagicMock()
        mock_history = MagicMock()
        mock_history.id = 1

        with patch(
            "src.common.scheduler.SessionLocal", return_value=mock_db
        ), patch(
            "src.common.scheduler.create_job_history", return_value=mock_history
        ), patch(
            "src.common.scheduler.update_job_history"
        ):
            from src.common.scheduler import track_execution

            @track_execution("cleanup_test", "정리 테스트")
            async def sample_job():
                return "done"

            # when
            await sample_job()

            # then
            mock_db.close.assert_called_once()


# ======================================================================
# 스케줄러 유틸리티 함수 테스트
# ======================================================================


class TestSchedulerUtils:
    """스케줄러 유틸리티 함수 테스트"""

    def test_get_scheduled_jobs_빈_목록(self):
        """작업이 없을 때 빈 목록 반환"""
        with patch("src.common.scheduler.scheduler") as mock_scheduler:
            mock_scheduler.get_jobs.return_value = []
            from src.common.scheduler import get_scheduled_jobs

            # when
            jobs = get_scheduled_jobs()

            # then
            assert jobs == []

    def test_get_scheduled_jobs_작업_있음(self):
        """등록된 작업 정보 반환"""
        with patch("src.common.scheduler.scheduler") as mock_scheduler:
            mock_job = MagicMock()
            mock_job.id = "test_job"
            mock_job.name = "테스트 작업"
            mock_job.next_run_time = datetime(2026, 12, 31, 23, 59)
            mock_job.trigger = MagicMock(__str__=lambda self: "interval[0:01:00]")

            mock_scheduler.get_jobs.return_value = [mock_job]
            from src.common.scheduler import get_scheduled_jobs

            # when
            jobs = get_scheduled_jobs()

            # then
            assert len(jobs) == 1
            assert jobs[0]["id"] == "test_job"
            assert jobs[0]["name"] == "테스트 작업"
            assert jobs[0]["next_run"] is not None

    def test_run_job_now_존재하지_않는_작업(self):
        """존재하지 않는 작업 실행 시 False 반환"""
        with patch("src.common.scheduler.scheduler") as mock_scheduler:
            mock_scheduler.get_job.return_value = None
            from src.common.scheduler import run_job_now

            # when
            result = run_job_now("non_existent")

            # then
            assert result is False
