"""
I/O 대기 테스트 시나리오
- I/O 바운드 작업에서 비동기의 동시성 이점 측정
- asyncio.sleep vs time.sleep 비교
- 비동기 함수 내 동기 블로킹의 영향 분석

실행 방법:
    locust -f locustfile_io.py --host=http://localhost:7777
"""

from locust import HttpUser, task, between, events
import random


class SyncIOUser(HttpUser):
    """동기 I/O 대기 테스트 사용자"""
    wait_time = between(0.1, 0.5)
    weight = 1

    @task
    def sync_io_wait(self):
        """동기 방식 I/O 대기 (time.sleep)"""
        timeout = random.choice([1, 2])  # 1-2초 랜덤 대기
        with self.client.get(
            f"/api/v1/standard/sync-test-with-wait?timeout={timeout}",
            name=f"[SYNC] IO Wait ({timeout}s)",
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class AsyncIOUser(HttpUser):
    """비동기 I/O 대기 테스트 사용자"""
    wait_time = between(0.1, 0.5)
    weight = 1

    @task
    def async_io_wait(self):
        """비동기 방식 I/O 대기 (asyncio.sleep)"""
        timeout = random.choice([1, 2])  # 1-2초 랜덤 대기
        with self.client.get(
            f"/api/v1/standard/async-test-with-await?timeout={timeout}",
            name=f"[ASYNC] IO Wait ({timeout}s)",
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class AsyncWithSyncBlockingUser(HttpUser):
    """비동기 함수 내 동기 블로킹 테스트 (안티패턴)"""
    wait_time = between(0.1, 0.5)
    weight = 1

    @task
    def async_with_sync_blocking(self):
        """비동기 함수 내 time.sleep (안티패턴)"""
        timeout = 1
        with self.client.get(
            f"/api/v1/standard/async-test-with-await-with-sync?timeout={timeout}",
            name="[ASYNC+SYNC BLOCKING] IO Wait (Anti-pattern)",
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class AsyncProperUser(HttpUser):
    """올바른 비동기 I/O 대기 테스트"""
    wait_time = between(0.1, 0.5)
    weight = 1

    @task
    def async_proper_wait(self):
        """비동기 함수 내 asyncio.sleep (올바른 패턴)"""
        timeout = 1
        with self.client.get(
            f"/api/v1/standard/async-test-with-await-with-async?timeout={timeout}",
            name="[ASYNC PROPER] IO Wait (Correct)",
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class ComparisonUser(HttpUser):
    """동기/비동기 I/O 비교 테스트 사용자"""
    wait_time = between(0.1, 0.5)
    weight = 1

    @task(1)
    def sync_io(self):
        """동기 I/O 대기"""
        self.client.get(
            "/api/v1/standard/sync-test-with-wait?timeout=1",
            name="[COMPARE] Sync IO 1s",
            timeout=30
        )

    @task(1)
    def async_io(self):
        """비동기 I/O 대기"""
        self.client.get(
            "/api/v1/standard/async-test-with-await?timeout=1",
            name="[COMPARE] Async IO 1s",
            timeout=30
        )

    @task(1)
    def async_blocking(self):
        """비동기 함수 내 동기 블로킹"""
        self.client.get(
            "/api/v1/standard/async-test-with-await-with-sync?timeout=1",
            name="[COMPARE] Async+Sync Blocking 1s",
            timeout=30
        )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """테스트 시작 시 실행"""
    print("\n" + "=" * 60)
    print(" I/O 대기 성능 테스트 시작")
    print(" 테스트 유형: 동기 vs 비동기 I/O 처리 비교")
    print(" ")
    print(" 핵심 비교 포인트:")
    print("   - 동기: time.sleep() - 스레드 블로킹")
    print("   - 비동기: asyncio.sleep() - 이벤트 루프 양보")
    print("   - 안티패턴: async 함수 내 time.sleep()")
    print("=" * 60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """테스트 종료 시 실행"""
    print("\n" + "=" * 60)
    print(" I/O 대기 성능 테스트 완료")
    print(" 예상 결과:")
    print("   - 비동기 I/O가 동기 대비 ~10배 높은 RPS")
    print("   - 안티패턴(async+sync)은 동기와 유사한 성능")
    print("=" * 60 + "\n")
