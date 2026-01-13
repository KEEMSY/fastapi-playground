"""
단순 응답 테스트 시나리오
- 동기/비동기 핸들러의 기본 성능 차이 측정
- I/O 작업 없이 순수 응답 속도 비교

실행 방법:
    locust -f locustfile_simple.py --host=http://localhost:7777
"""

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
import time


class SyncSimpleUser(HttpUser):
    """동기 엔드포인트만 테스트하는 사용자"""
    wait_time = between(0.1, 0.5)
    weight = 1

    @task
    def sync_simple(self):
        """단순 동기 응답 테스트"""
        with self.client.get(
            "/api/v1/standard/sync-test",
            name="[SYNC] Simple Response",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class AsyncSimpleUser(HttpUser):
    """비동기 엔드포인트만 테스트하는 사용자"""
    wait_time = between(0.1, 0.5)
    weight = 1

    @task
    def async_simple(self):
        """단순 비동기 응답 테스트"""
        with self.client.get(
            "/api/v1/standard/async-test",
            name="[ASYNC] Simple Response",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class MixedSimpleUser(HttpUser):
    """동기/비동기 혼합 테스트 사용자"""
    wait_time = between(0.1, 0.5)
    weight = 1

    @task(1)
    def sync_simple(self):
        """단순 동기 응답"""
        self.client.get("/api/v1/standard/sync-test", name="[MIXED] Sync Simple")

    @task(1)
    def async_simple(self):
        """단순 비동기 응답"""
        self.client.get("/api/v1/standard/async-test", name="[MIXED] Async Simple")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """테스트 시작 시 실행"""
    print("\n" + "=" * 60)
    print(" 단순 응답 성능 테스트 시작")
    print(" 테스트 유형: 동기 vs 비동기 기본 응답 속도 비교")
    print("=" * 60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """테스트 종료 시 실행"""
    print("\n" + "=" * 60)
    print(" 단순 응답 성능 테스트 완료")
    print("=" * 60 + "\n")
