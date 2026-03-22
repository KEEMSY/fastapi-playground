"""
스케줄러 도메인 API 테스트

== 유스케이스 목록 ==

[UC-1] 스케줄 작업 생성 (CRUD - Create)
  - 정상: cron 트리거로 작업 생성
  - 정상: interval 트리거로 작업 생성
  - 정상: date 트리거로 일회성 작업 생성
  - 비정상: 잘못된 트리거 타입
  - 비정상: 잘못된 cron 표현식
  - 비정상: 과거 날짜의 date 트리거
  - 비정상: 필수 필드 누락
  - 비정상: 중복 job_id로 생성 시도

[UC-2] 스케줄 작업 목록 조회 (CRUD - Read List)
  - 정상: 전체 작업 목록 조회
  - 정상: 작업이 없을 때 빈 목록 반환
  - 정상: 활성/비활성 필터링 조회

[UC-3] 스케줄 작업 단건 조회 (CRUD - Read Detail)
  - 정상: ID로 작업 상세 조회
  - 비정상: 존재하지 않는 작업 ID 조회

[UC-4] 스케줄 작업 수정 (CRUD - Update)
  - 정상: 트리거 변경 (interval → cron)
  - 정상: 작업 이름 변경
  - 비정상: 존재하지 않는 작업 수정
  - 비정상: 잘못된 cron 표현식으로 수정

[UC-5] 스케줄 작업 삭제 (CRUD - Delete)
  - 정상: 작업 삭제
  - 비정상: 존재하지 않는 작업 삭제

[UC-6] 스케줄 작업 활성/비활성 토글
  - 정상: 활성 → 비활성
  - 정상: 비활성 → 활성
  - 비정상: 존재하지 않는 작업 토글

[UC-7] 스케줄 작업 수동 실행
  - 정상: 등록된 작업 즉시 실행
  - 비정상: 존재하지 않는 작업 실행
  - 비정상: 비활성 작업 실행 시도

[UC-8] 실행 이력 조회
  - 정상: 전체 이력 조회
  - 정상: job_id 필터 조회
  - 정상: status 필터 조회 (success/failed/running)
  - 정상: 페이지네이션 (limit, offset)
  - 정상: 이력이 없을 때 빈 목록

[UC-9] 스케줄러 상태 조회
  - 정상: 스케줄러 running 상태 확인
  - 정상: 등록된 작업 수 확인

== 테스트 매트릭스 ==

| API Endpoint                              | Method | 정상 | 비정상 | 합계 |
|------------------------------------------|--------|------|--------|------|
| POST   /api/scheduler/schedules          | CREATE | 4    | 4      | 8    |
| GET    /api/scheduler/schedules          | LIST   | 3    | 0      | 3    |
| GET    /api/scheduler/schedules/{id}     | DETAIL | 1    | 1      | 2    |
| PUT    /api/scheduler/schedules/{id}     | UPDATE | 2    | 2      | 4    |
| DELETE /api/scheduler/schedules/{id}     | DELETE | 1    | 1      | 2    |
| PATCH  /api/scheduler/schedules/{id}/toggle | TOGGLE | 2 | 1      | 3    |
| POST   /api/scheduler/schedules/{id}/run | RUN    | 1    | 2      | 3    |
| GET    /api/scheduler/history            | HISTORY| 5    | 0      | 5    |
| GET    /api/scheduler/status             | STATUS | 2    | 0      | 2    |
| 합계                                     |        | 21   | 11     | 32   |
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

# ======================================================================
# 테스트 헬퍼
# ======================================================================

BASE_URL = "/api/scheduler"


def _make_cron_schedule(
    job_id: str = "cleanup_old_data",
    name: str = "오래된 데이터 정리",
    job_type: str = "data_cleanup",
    trigger_type: str = "cron",
    cron_expression: str = "0 2 * * *",
    description: str = "매일 새벽 2시에 30일 이상 된 데이터를 삭제합니다",
) -> dict:
    return {
        "job_id": job_id,
        "name": name,
        "job_type": job_type,
        "trigger_type": trigger_type,
        "trigger_args": {"cron_expression": cron_expression},
        "description": description,
    }


def _make_interval_schedule(
    job_id: str = "sync_external_api",
    name: str = "외부 API 동기화",
    job_type: str = "api_sync",
    trigger_type: str = "interval",
    seconds: int = 0,
    minutes: int = 30,
    hours: int = 0,
    description: str = "30분마다 외부 API에서 데이터를 가져옵니다",
) -> dict:
    return {
        "job_id": job_id,
        "name": name,
        "job_type": job_type,
        "trigger_type": trigger_type,
        "trigger_args": {"seconds": seconds, "minutes": minutes, "hours": hours},
        "description": description,
    }


def _make_date_schedule(
    job_id: str = "send_notification_once",
    name: str = "일회성 알림 발송",
    job_type: str = "notification",
    trigger_type: str = "date",
    run_date: str = "2026-12-31T23:59:00",
    description: str = "특정 시각에 한번 알림을 발송합니다",
) -> dict:
    return {
        "job_id": job_id,
        "name": name,
        "job_type": job_type,
        "trigger_type": trigger_type,
        "trigger_args": {"run_date": run_date},
        "description": description,
    }


# ======================================================================
# UC-1: 스케줄 작업 생성
# ======================================================================


class TestSchedulerCreate:
    """스케줄 작업 생성 테스트"""

    @pytest.mark.asyncio
    async def test_scheduler_create_cron_정상(self, async_client: AsyncClient):
        """cron 트리거로 스케줄 작업 생성"""
        # given
        payload = _make_cron_schedule()

        # when
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 204

    @pytest.mark.asyncio
    async def test_scheduler_create_interval_정상(self, async_client: AsyncClient):
        """interval 트리거로 스케줄 작업 생성"""
        # given
        payload = _make_interval_schedule()

        # when
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 204

    @pytest.mark.asyncio
    async def test_scheduler_create_date_정상(self, async_client: AsyncClient):
        """date 트리거로 일회성 작업 생성"""
        # given
        payload = _make_date_schedule()

        # when
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 204

    @pytest.mark.asyncio
    async def test_scheduler_create_학습용_예제_정상(self, async_client: AsyncClient):
        """학습용 예제 작업(로그 출력) 생성"""
        # given
        payload = _make_interval_schedule(
            job_id="learning_example_log",
            name="학습용 로그 출력",
            job_type="example",
            minutes=1,
            description="1분마다 로그를 출력하는 학습용 작업",
        )

        # when
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 204

    @pytest.mark.asyncio
    async def test_scheduler_create_잘못된_트리거타입(self, async_client: AsyncClient):
        """잘못된 트리거 타입으로 생성 시 422 에러"""
        # given
        payload = _make_cron_schedule(trigger_type="invalid_trigger")

        # when
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_scheduler_create_잘못된_cron_표현식(self, async_client: AsyncClient):
        """잘못된 cron 표현식으로 생성 시 에러"""
        # given
        payload = _make_cron_schedule(cron_expression="invalid cron")

        # when
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 422 or res.status_code == 400

    @pytest.mark.asyncio
    async def test_scheduler_create_과거_날짜_date_트리거(
        self, async_client: AsyncClient
    ):
        """과거 날짜의 date 트리거로 생성 시 에러"""
        # given
        payload = _make_date_schedule(run_date="2020-01-01T00:00:00")

        # when
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 422 or res.status_code == 400

    @pytest.mark.asyncio
    async def test_scheduler_create_필수_필드_누락(self, async_client: AsyncClient):
        """필수 필드 누락 시 422 에러"""
        # given
        payload = {"job_id": "incomplete_job"}  # name, job_type 등 누락

        # when
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_scheduler_create_중복_job_id(self, async_client: AsyncClient):
        """중복 job_id로 생성 시 에러"""
        # given
        payload = _make_cron_schedule(job_id="duplicate_job")
        await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # when - 동일 job_id로 다시 생성
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 409 or res.status_code == 400


# ======================================================================
# UC-2: 스케줄 작업 목록 조회
# ======================================================================


class TestSchedulerList:
    """스케줄 작업 목록 조회 테스트"""

    @pytest.mark.asyncio
    async def test_scheduler_list_정상(self, async_client: AsyncClient):
        """전체 작업 목록 조회"""
        # given - 작업 2개 등록
        await async_client.post(
            f"{BASE_URL}/schedules",
            json=_make_cron_schedule(job_id="list_test_1", name="테스트 작업 1"),
        )
        await async_client.post(
            f"{BASE_URL}/schedules",
            json=_make_interval_schedule(job_id="list_test_2", name="테스트 작업 2"),
        )

        # when
        res = await async_client.get(f"{BASE_URL}/schedules")

        # then
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_scheduler_list_빈_목록(self, async_client: AsyncClient):
        """등록된 작업이 없을 때 빈 목록 반환"""
        # given - 모든 작업 미등록 상태 (cleanup fixture에 의해)

        # when
        res = await async_client.get(f"{BASE_URL}/schedules")

        # then
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_scheduler_list_활성_필터(self, async_client: AsyncClient):
        """활성 상태 필터링 조회"""
        # given
        await async_client.post(
            f"{BASE_URL}/schedules",
            json=_make_cron_schedule(job_id="active_filter_test", name="필터 테스트"),
        )

        # when
        res = await async_client.get(f"{BASE_URL}/schedules", params={"is_active": True})

        # then
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        for job in data:
            assert job.get("is_active") is True


# ======================================================================
# UC-3: 스케줄 작업 단건 조회
# ======================================================================


class TestSchedulerDetail:
    """스케줄 작업 단건 조회 테스트"""

    @pytest.mark.asyncio
    async def test_scheduler_detail_정상(self, async_client: AsyncClient):
        """ID로 작업 상세 조회"""
        # given
        job_id = "detail_test_job"
        await async_client.post(
            f"{BASE_URL}/schedules",
            json=_make_cron_schedule(job_id=job_id, name="상세 조회 테스트"),
        )

        # when
        res = await async_client.get(f"{BASE_URL}/schedules/{job_id}")

        # then
        assert res.status_code == 200
        data = res.json()
        assert data["job_id"] == job_id
        assert data["name"] == "상세 조회 테스트"
        assert data["trigger_type"] == "cron"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_scheduler_detail_존재하지_않는_작업(self, async_client: AsyncClient):
        """존재하지 않는 작업 ID 조회 시 404"""
        # given, when
        res = await async_client.get(f"{BASE_URL}/schedules/non_existent_job_id")

        # then
        assert res.status_code == 404


# ======================================================================
# UC-4: 스케줄 작업 수정
# ======================================================================


class TestSchedulerUpdate:
    """스케줄 작업 수정 테스트"""

    @pytest.mark.asyncio
    async def test_scheduler_update_트리거_변경_정상(self, async_client: AsyncClient):
        """interval → cron 트리거 변경"""
        # given
        job_id = "update_trigger_test"
        await async_client.post(
            f"{BASE_URL}/schedules",
            json=_make_interval_schedule(job_id=job_id, name="트리거 변경 테스트"),
        )

        # when
        update_payload = {
            "trigger_type": "cron",
            "trigger_args": {"cron_expression": "0 3 * * *"},
        }
        res = await async_client.put(
            f"{BASE_URL}/schedules/{job_id}", json=update_payload
        )

        # then
        assert res.status_code == 204

        # verify
        detail = await async_client.get(f"{BASE_URL}/schedules/{job_id}")
        assert detail.json()["trigger_type"] == "cron"

    @pytest.mark.asyncio
    async def test_scheduler_update_이름_변경_정상(self, async_client: AsyncClient):
        """작업 이름 변경"""
        # given
        job_id = "update_name_test"
        await async_client.post(
            f"{BASE_URL}/schedules",
            json=_make_cron_schedule(job_id=job_id, name="원래 이름"),
        )

        # when
        update_payload = {"name": "변경된 이름"}
        res = await async_client.put(
            f"{BASE_URL}/schedules/{job_id}", json=update_payload
        )

        # then
        assert res.status_code == 204

        # verify
        detail = await async_client.get(f"{BASE_URL}/schedules/{job_id}")
        assert detail.json()["name"] == "변경된 이름"

    @pytest.mark.asyncio
    async def test_scheduler_update_존재하지_않는_작업(self, async_client: AsyncClient):
        """존재하지 않는 작업 수정 시 404"""
        # given, when
        update_payload = {"name": "변경 시도"}
        res = await async_client.put(
            f"{BASE_URL}/schedules/non_existent_job", json=update_payload
        )

        # then
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_scheduler_update_잘못된_cron_표현식(self, async_client: AsyncClient):
        """잘못된 cron 표현식으로 수정 시 에러"""
        # given
        job_id = "update_bad_cron_test"
        await async_client.post(
            f"{BASE_URL}/schedules",
            json=_make_cron_schedule(job_id=job_id, name="cron 수정 에러 테스트"),
        )

        # when
        update_payload = {
            "trigger_type": "cron",
            "trigger_args": {"cron_expression": "not a valid cron"},
        }
        res = await async_client.put(
            f"{BASE_URL}/schedules/{job_id}", json=update_payload
        )

        # then
        assert res.status_code == 422 or res.status_code == 400


# ======================================================================
# UC-5: 스케줄 작업 삭제
# ======================================================================


class TestSchedulerDelete:
    """스케줄 작업 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_scheduler_delete_정상(self, async_client: AsyncClient):
        """작업 삭제 성공"""
        # given
        job_id = "delete_test_job"
        await async_client.post(
            f"{BASE_URL}/schedules",
            json=_make_cron_schedule(job_id=job_id, name="삭제 테스트"),
        )

        # when
        res = await async_client.delete(f"{BASE_URL}/schedules/{job_id}")

        # then
        assert res.status_code == 204

        # verify - 조회 시 404
        detail = await async_client.get(f"{BASE_URL}/schedules/{job_id}")
        assert detail.status_code == 404

    @pytest.mark.asyncio
    async def test_scheduler_delete_존재하지_않는_작업(self, async_client: AsyncClient):
        """존재하지 않는 작업 삭제 시 404"""
        # given, when
        res = await async_client.delete(f"{BASE_URL}/schedules/non_existent_job")

        # then
        assert res.status_code == 404


# ======================================================================
# UC-6: 스케줄 작업 활성/비활성 토글
# ======================================================================


class TestSchedulerToggle:
    """스케줄 작업 활성/비활성 토글 테스트"""

    @pytest.mark.asyncio
    async def test_scheduler_toggle_활성에서_비활성(self, async_client: AsyncClient):
        """활성 → 비활성 토글"""
        # given
        job_id = "toggle_test_active"
        await async_client.post(
            f"{BASE_URL}/schedules",
            json=_make_cron_schedule(job_id=job_id, name="토글 테스트"),
        )

        # when
        res = await async_client.patch(f"{BASE_URL}/schedules/{job_id}/toggle")

        # then
        assert res.status_code == 200
        data = res.json()
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_scheduler_toggle_비활성에서_활성(self, async_client: AsyncClient):
        """비활성 → 활성 토글"""
        # given
        job_id = "toggle_test_inactive"
        await async_client.post(
            f"{BASE_URL}/schedules",
            json=_make_cron_schedule(job_id=job_id, name="토글 테스트 2"),
        )
        # 먼저 비활성화
        await async_client.patch(f"{BASE_URL}/schedules/{job_id}/toggle")

        # when - 다시 활성화
        res = await async_client.patch(f"{BASE_URL}/schedules/{job_id}/toggle")

        # then
        assert res.status_code == 200
        data = res.json()
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_scheduler_toggle_존재하지_않는_작업(self, async_client: AsyncClient):
        """존재하지 않는 작업 토글 시 404"""
        # given, when
        res = await async_client.patch(
            f"{BASE_URL}/schedules/non_existent_job/toggle"
        )

        # then
        assert res.status_code == 404


# ======================================================================
# UC-7: 스케줄 작업 수동 실행
# ======================================================================


class TestSchedulerRunManually:
    """스케줄 작업 수동 실행 테스트"""

    @pytest.mark.asyncio
    async def test_scheduler_run_정상(self, async_client: AsyncClient):
        """등록된 작업 즉시 실행"""
        # given
        job_id = "run_test_job"
        await async_client.post(
            f"{BASE_URL}/schedules",
            json=_make_interval_schedule(
                job_id=job_id,
                name="수동 실행 테스트",
                job_type="example",
                minutes=60,
            ),
        )

        # when
        res = await async_client.post(f"{BASE_URL}/schedules/{job_id}/run")

        # then
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["job_id"] == job_id

    @pytest.mark.asyncio
    async def test_scheduler_run_존재하지_않는_작업(self, async_client: AsyncClient):
        """존재하지 않는 작업 실행 시 404"""
        # given, when
        res = await async_client.post(f"{BASE_URL}/schedules/non_existent_job/run")

        # then
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_scheduler_run_비활성_작업(self, async_client: AsyncClient):
        """비활성 작업 실행 시도 시 에러"""
        # given
        job_id = "run_inactive_test"
        await async_client.post(
            f"{BASE_URL}/schedules",
            json=_make_cron_schedule(job_id=job_id, name="비활성 실행 테스트"),
        )
        # 비활성화
        await async_client.patch(f"{BASE_URL}/schedules/{job_id}/toggle")

        # when
        res = await async_client.post(f"{BASE_URL}/schedules/{job_id}/run")

        # then
        assert res.status_code == 400 or res.status_code == 409


# ======================================================================
# UC-8: 실행 이력 조회
# ======================================================================


class TestSchedulerHistory:
    """실행 이력 조회 테스트"""

    @pytest.mark.asyncio
    async def test_scheduler_history_전체_조회(self, async_client: AsyncClient):
        """전체 실행 이력 조회"""
        # given, when
        res = await async_client.get(f"{BASE_URL}/history")

        # then
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_scheduler_history_job_id_필터(self, async_client: AsyncClient):
        """job_id로 필터링된 이력 조회"""
        # given - 작업 생성 후 수동 실행하여 이력 생성
        job_id = "history_filter_test"
        await async_client.post(
            f"{BASE_URL}/schedules",
            json=_make_interval_schedule(
                job_id=job_id, name="이력 필터 테스트", job_type="example", minutes=60
            ),
        )
        await async_client.post(f"{BASE_URL}/schedules/{job_id}/run")

        # when
        res = await async_client.get(
            f"{BASE_URL}/history", params={"job_id": job_id}
        )

        # then
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        for history in data:
            assert history["job_id"] == job_id

    @pytest.mark.asyncio
    async def test_scheduler_history_status_필터(self, async_client: AsyncClient):
        """status로 필터링된 이력 조회"""
        # given, when
        res = await async_client.get(
            f"{BASE_URL}/history", params={"status": "success"}
        )

        # then
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        for history in data:
            assert history["status"] == "success"

    @pytest.mark.asyncio
    async def test_scheduler_history_페이지네이션(self, async_client: AsyncClient):
        """limit, offset 파라미터로 페이지네이션"""
        # given, when
        res = await async_client.get(
            f"{BASE_URL}/history", params={"limit": 5, "offset": 0}
        )

        # then
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    @pytest.mark.asyncio
    async def test_scheduler_history_빈_이력(self, async_client: AsyncClient):
        """이력이 없을 때 빈 목록 반환"""
        # given - 존재하지 않는 job_id로 필터
        # when
        res = await async_client.get(
            f"{BASE_URL}/history", params={"job_id": "absolutely_no_history_job"}
        )

        # then
        assert res.status_code == 200
        data = res.json()
        assert data == []


# ======================================================================
# UC-9: 스케줄러 상태 조회
# ======================================================================


class TestSchedulerStatus:
    """스케줄러 상태 조회 테스트"""

    @pytest.mark.asyncio
    async def test_scheduler_status_정상(self, async_client: AsyncClient):
        """스케줄러 상태 조회"""
        # given, when
        res = await async_client.get(f"{BASE_URL}/status")

        # then
        assert res.status_code == 200
        data = res.json()
        assert "running" in data
        assert "jobs_count" in data

    @pytest.mark.asyncio
    async def test_scheduler_status_작업_수_확인(self, async_client: AsyncClient):
        """등록된 작업 수 확인"""
        # given
        await async_client.post(
            f"{BASE_URL}/schedules",
            json=_make_cron_schedule(job_id="status_count_test", name="상태 카운트 테스트"),
        )

        # when
        res = await async_client.get(f"{BASE_URL}/status")

        # then
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data["jobs_count"], int)
        assert data["jobs_count"] >= 1


# ======================================================================
# 트리거 타입별 검증 테스트 (단위 테스트)
# ======================================================================


class TestTriggerValidation:
    """트리거 타입별 유효성 검증 단위 테스트"""

    @pytest.mark.asyncio
    async def test_cron_trigger_다양한_표현식(self, async_client: AsyncClient):
        """다양한 cron 표현식 검증"""
        cron_cases = [
            ("0 * * * *", "매시 정각"),
            ("*/5 * * * *", "5분마다"),
            ("0 9-18 * * 1-5", "평일 근무시간"),
            ("0 0 1 * *", "매월 1일 자정"),
        ]

        for idx, (cron_expr, desc) in enumerate(cron_cases):
            payload = _make_cron_schedule(
                job_id=f"cron_validation_{idx}",
                name=f"cron 검증: {desc}",
                cron_expression=cron_expr,
            )
            res = await async_client.post(f"{BASE_URL}/schedules", json=payload)
            assert res.status_code == 204, f"cron 표현식 '{cron_expr}' ({desc}) 실패"

    @pytest.mark.asyncio
    async def test_interval_trigger_다양한_간격(self, async_client: AsyncClient):
        """다양한 interval 간격 검증"""
        interval_cases = [
            (30, 0, 0, "30초"),
            (0, 5, 0, "5분"),
            (0, 0, 1, "1시간"),
            (0, 30, 2, "2시간 30분"),
        ]

        for idx, (sec, min_, hr, desc) in enumerate(interval_cases):
            payload = _make_interval_schedule(
                job_id=f"interval_validation_{idx}",
                name=f"interval 검증: {desc}",
                seconds=sec,
                minutes=min_,
                hours=hr,
            )
            res = await async_client.post(f"{BASE_URL}/schedules", json=payload)
            assert res.status_code == 204, f"interval '{desc}' 실패"

    @pytest.mark.asyncio
    async def test_interval_trigger_간격_0_에러(self, async_client: AsyncClient):
        """간격이 0인 interval 트리거 에러"""
        # given
        payload = _make_interval_schedule(
            job_id="interval_zero_test",
            name="간격 0 테스트",
            seconds=0,
            minutes=0,
            hours=0,
        )

        # when
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 422 or res.status_code == 400


# ======================================================================
# 작업 유형별 테스트
# ======================================================================


class TestJobTypes:
    """작업 유형별 생성 및 실행 테스트"""

    @pytest.mark.asyncio
    async def test_data_cleanup_작업_생성(self, async_client: AsyncClient):
        """데이터 정리/만료 작업 생성"""
        # given
        payload = _make_cron_schedule(
            job_id="data_cleanup_job",
            name="오래된 데이터 삭제",
            job_type="data_cleanup",
            cron_expression="0 3 * * *",
            description="매일 새벽 3시에 만료된 데이터를 삭제합니다",
        )

        # when
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 204

    @pytest.mark.asyncio
    async def test_api_sync_작업_생성(self, async_client: AsyncClient):
        """외부 API 동기화 작업 생성"""
        # given
        payload = _make_interval_schedule(
            job_id="api_sync_job",
            name="외부 API 데이터 동기화",
            job_type="api_sync",
            minutes=15,
            description="15분마다 외부 API에서 데이터를 가져옵니다",
        )

        # when
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 204

    @pytest.mark.asyncio
    async def test_notification_작업_생성(self, async_client: AsyncClient):
        """알림/이메일 발송 예약 작업 생성"""
        # given
        payload = _make_date_schedule(
            job_id="notification_job",
            name="이벤트 알림 발송",
            job_type="notification",
            run_date="2026-12-25T09:00:00",
            description="크리스마스 이벤트 알림을 발송합니다",
        )

        # when
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 204

    @pytest.mark.asyncio
    async def test_example_작업_생성(self, async_client: AsyncClient):
        """학습용 예제 작업 생성"""
        # given
        payload = _make_interval_schedule(
            job_id="example_job",
            name="학습용 로그 출력 작업",
            job_type="example",
            minutes=1,
            description="학습 목적의 간단한 로그 출력 작업입니다",
        )

        # when
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 204

    @pytest.mark.asyncio
    async def test_잘못된_job_type_에러(self, async_client: AsyncClient):
        """지원하지 않는 작업 유형 시 에러"""
        # given
        payload = _make_cron_schedule(
            job_id="invalid_type_job",
            name="잘못된 타입 테스트",
            job_type="unsupported_type",
        )

        # when
        res = await async_client.post(f"{BASE_URL}/schedules", json=payload)

        # then
        assert res.status_code == 422
