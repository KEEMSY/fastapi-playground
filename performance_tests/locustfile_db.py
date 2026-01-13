"""
DB 세션 테스트 시나리오
- 동기/비동기 DB 세션의 성능 차이 측정
- DB 연결 풀 사용 패턴 분석
- 대용량 데이터 조회 성능 비교

실행 방법:
    locust -f locustfile_db.py --host=http://localhost:7777

사전 준비:
    python scripts/generate_test_data.py --records=100000
"""

from locust import HttpUser, task, between, events
import random


class SyncDBSessionUser(HttpUser):
    """동기 DB 세션 테스트 사용자"""
    wait_time = between(0.1, 0.5)
    weight = 1

    @task(3)
    def sync_db_session(self):
        """동기 DB 세션으로 pg_sleep 실행"""
        timeout = 1
        with self.client.get(
            f"/api/v1/standard/sync-test-with-sync-db-session?timeout={timeout}",
            name="[SYNC DB] Session Sleep",
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def sync_bulk_read(self):
        """동기 대용량 데이터 조회"""
        limit = random.choice([100, 500, 1000])
        offset = random.randint(0, 90000)
        with self.client.get(
            f"/api/v1/standard/sync-bulk-read?limit={limit}&offset={offset}",
            name=f"[SYNC DB] Bulk Read ({limit})",
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class AsyncDBSessionUser(HttpUser):
    """비동기 DB 세션 테스트 사용자"""
    wait_time = between(0.1, 0.5)
    weight = 1

    @task(3)
    def async_db_session(self):
        """비동기 DB 세션으로 pg_sleep 실행"""
        timeout = 1
        with self.client.get(
            f"/api/v1/standard/async-test-with-async-db-session?timeout={timeout}",
            name="[ASYNC DB] Session Sleep",
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def async_bulk_read(self):
        """비동기 대용량 데이터 조회"""
        limit = random.choice([100, 500, 1000])
        offset = random.randint(0, 90000)
        with self.client.get(
            f"/api/v1/standard/async-bulk-read?limit={limit}&offset={offset}",
            name=f"[ASYNC DB] Bulk Read ({limit})",
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class AsyncWithSyncDBUser(HttpUser):
    """비동기 함수 내 동기 DB 세션 테스트 (안티패턴)"""
    wait_time = between(0.1, 0.5)
    weight = 1

    @task
    def async_with_sync_db(self):
        """비동기 함수에서 동기 DB 세션 사용"""
        timeout = 1
        with self.client.get(
            f"/api/v1/standard/async-test-with-async-db-session-with-sync?timeout={timeout}",
            name="[ASYNC+SYNC DB] Session (Anti-pattern)",
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class MultipleQueriesUser(HttpUser):
    """다중 쿼리 테스트 사용자"""
    wait_time = between(0.1, 0.5)
    weight = 1

    @task(1)
    def sync_multiple_queries(self):
        """동기 다중 쿼리"""
        query_count = random.choice([3, 5])
        with self.client.get(
            f"/api/v1/standard/sync-test-with-sync-db-session-multiple-queries?query_count={query_count}",
            name=f"[SYNC DB] Multiple Queries ({query_count})",
            catch_response=True,
            timeout=60
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def async_multiple_queries(self):
        """비동기 다중 쿼리"""
        query_count = random.choice([3, 5])
        with self.client.get(
            f"/api/v1/standard/async-test-with-async-db-session-multiple-queries?query_count={query_count}",
            name=f"[ASYNC DB] Multiple Queries ({query_count})",
            catch_response=True,
            timeout=60
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class BulkReadComparisonUser(HttpUser):
    """대용량 조회 비교 테스트 사용자"""
    wait_time = between(0.1, 0.5)
    weight = 1

    @task(1)
    def sync_bulk_small(self):
        """동기 소량 조회 (100건)"""
        self.client.get(
            "/api/v1/standard/sync-bulk-read?limit=100",
            name="[BULK] Sync 100",
            timeout=30
        )

    @task(1)
    def async_bulk_small(self):
        """비동기 소량 조회 (100건)"""
        self.client.get(
            "/api/v1/standard/async-bulk-read?limit=100",
            name="[BULK] Async 100",
            timeout=30
        )

    @task(1)
    def sync_bulk_large(self):
        """동기 대량 조회 (1000건)"""
        self.client.get(
            "/api/v1/standard/sync-bulk-read?limit=1000",
            name="[BULK] Sync 1000",
            timeout=30
        )

    @task(1)
    def async_bulk_large(self):
        """비동기 대량 조회 (1000건)"""
        self.client.get(
            "/api/v1/standard/async-bulk-read?limit=1000",
            name="[BULK] Async 1000",
            timeout=30
        )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """테스트 시작 시 실행"""
    print("\n" + "=" * 60)
    print(" DB 세션 성능 테스트 시작")
    print(" 테스트 유형: 동기 vs 비동기 DB 세션 비교")
    print(" ")
    print(" 테스트 항목:")
    print("   - DB 세션 pg_sleep 실행")
    print("   - 대용량 데이터 조회 (100~1000건)")
    print("   - 다중 쿼리 실행")
    print(" ")
    print(" 사전 준비:")
    print("   python scripts/generate_test_data.py --records=100000")
    print("=" * 60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """테스트 종료 시 실행"""
    print("\n" + "=" * 60)
    print(" DB 세션 성능 테스트 완료")
    print("=" * 60 + "\n")
