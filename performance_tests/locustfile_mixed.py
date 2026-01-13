"""
혼합 부하 테스트 시나리오
- 실제 환경을 모사한 다양한 요청 패턴 조합
- 동기/비동기, I/O 대기, DB 조회를 혼합하여 테스트
- 실제 운영 환경과 유사한 부하 패턴 생성

실행 방법:
    locust -f locustfile_mixed.py --host=http://localhost:7777

    # 단일 인스턴스 테스트
    locust -f locustfile_mixed.py --host=http://localhost:7777 \
        --users=100 --spawn-rate=10 --run-time=5m --headless \
        --csv=results/mixed_single_100

    # 다중 인스턴스 테스트
    locust -f locustfile_mixed.py --host=http://localhost:7777 \
        --users=500 --spawn-rate=20 --run-time=5m --headless \
        --csv=results/mixed_multi_500
"""

from locust import HttpUser, task, between, events, tag
import random


class SyncWorkloadUser(HttpUser):
    """동기 워크로드 사용자 - 실제 동기 서비스 시뮬레이션"""
    wait_time = between(0.5, 2.0)
    weight = 3  # 동기 사용자 비율 조절

    @task(5)
    def simple_request(self):
        """단순 요청 (가장 빈번)"""
        self.client.get(
            "/api/v1/standard/sync-test",
            name="[SYNC] Simple"
        )

    @task(2)
    def io_wait_short(self):
        """짧은 I/O 대기"""
        self.client.get(
            "/api/v1/standard/sync-test-with-wait?timeout=1",
            name="[SYNC] IO Wait 1s",
            timeout=15
        )

    @task(1)
    def io_wait_long(self):
        """긴 I/O 대기"""
        self.client.get(
            "/api/v1/standard/sync-test-with-wait?timeout=3",
            name="[SYNC] IO Wait 3s",
            timeout=15
        )

    @task(2)
    def db_read(self):
        """DB 조회"""
        limit = random.choice([100, 200, 500])
        offset = random.randint(0, 90000)
        self.client.get(
            f"/api/v1/standard/sync-bulk-read?limit={limit}&offset={offset}",
            name=f"[SYNC] DB Read",
            timeout=30
        )

    @task(1)
    def db_sleep(self):
        """DB 세션 대기"""
        self.client.get(
            "/api/v1/standard/sync-test-with-sync-db-session?timeout=1",
            name="[SYNC] DB Sleep",
            timeout=15
        )


class AsyncWorkloadUser(HttpUser):
    """비동기 워크로드 사용자 - 실제 비동기 서비스 시뮬레이션"""
    wait_time = between(0.5, 2.0)
    weight = 3  # 비동기 사용자 비율 조절

    @task(5)
    def simple_request(self):
        """단순 요청 (가장 빈번)"""
        self.client.get(
            "/api/v1/standard/async-test",
            name="[ASYNC] Simple"
        )

    @task(2)
    def io_wait_short(self):
        """짧은 I/O 대기"""
        self.client.get(
            "/api/v1/standard/async-test-with-await?timeout=1",
            name="[ASYNC] IO Wait 1s",
            timeout=15
        )

    @task(1)
    def io_wait_long(self):
        """긴 I/O 대기"""
        self.client.get(
            "/api/v1/standard/async-test-with-await?timeout=3",
            name="[ASYNC] IO Wait 3s",
            timeout=15
        )

    @task(2)
    def db_read(self):
        """DB 조회"""
        limit = random.choice([100, 200, 500])
        offset = random.randint(0, 90000)
        self.client.get(
            f"/api/v1/standard/async-bulk-read?limit={limit}&offset={offset}",
            name=f"[ASYNC] DB Read",
            timeout=30
        )

    @task(1)
    def db_sleep(self):
        """DB 세션 대기"""
        self.client.get(
            "/api/v1/standard/async-test-with-async-db-session?timeout=1",
            name="[ASYNC] DB Sleep",
            timeout=15
        )


class RealisticUser(HttpUser):
    """실제 사용자 패턴 시뮬레이션"""
    wait_time = between(1.0, 3.0)
    weight = 4  # 가장 높은 비율

    @task(10)
    def browse_simple(self):
        """일반 페이지 조회 (가장 빈번)"""
        endpoint = random.choice([
            "/api/v1/standard/sync-test",
            "/api/v1/standard/async-test"
        ])
        self.client.get(endpoint, name="[REAL] Browse")

    @task(3)
    def search_data(self):
        """데이터 검색"""
        limit = random.choice([50, 100])
        category = random.choice([
            "technology", "science", "business", "sports", "entertainment"
        ])
        endpoint = random.choice([
            f"/api/v1/standard/sync-bulk-read?limit={limit}&category={category}",
            f"/api/v1/standard/async-bulk-read?limit={limit}&category={category}"
        ])
        self.client.get(endpoint, name="[REAL] Search", timeout=30)

    @task(2)
    def detail_view(self):
        """상세 조회 (I/O 포함)"""
        endpoint = random.choice([
            "/api/v1/standard/sync-test-with-wait?timeout=1",
            "/api/v1/standard/async-test-with-await?timeout=1"
        ])
        self.client.get(endpoint, name="[REAL] Detail", timeout=15)

    @task(1)
    def heavy_operation(self):
        """무거운 작업"""
        endpoint = random.choice([
            "/api/v1/standard/sync-bulk-read?limit=1000",
            "/api/v1/standard/async-bulk-read?limit=1000",
            "/api/v1/standard/sync-test-with-sync-db-session?timeout=2",
            "/api/v1/standard/async-test-with-async-db-session?timeout=2"
        ])
        self.client.get(endpoint, name="[REAL] Heavy", timeout=30)


class StressTestUser(HttpUser):
    """스트레스 테스트용 사용자 - 빠른 요청 생성"""
    wait_time = between(0.1, 0.3)
    weight = 2

    @task(3)
    def rapid_simple(self):
        """빠른 단순 요청"""
        endpoint = random.choice([
            "/api/v1/standard/sync-test",
            "/api/v1/standard/async-test"
        ])
        self.client.get(endpoint, name="[STRESS] Rapid")

    @task(1)
    def rapid_db(self):
        """빠른 DB 요청"""
        endpoint = random.choice([
            "/api/v1/standard/sync-bulk-read?limit=50",
            "/api/v1/standard/async-bulk-read?limit=50"
        ])
        self.client.get(endpoint, name="[STRESS] Rapid DB", timeout=30)


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """테스트 시작 시 실행"""
    print("\n" + "=" * 70)
    print(" 혼합 부하 성능 테스트 시작")
    print("=" * 70)
    print(" ")
    print(" 사용자 유형:")
    print("   - SyncWorkloadUser (weight=3): 동기 워크로드")
    print("   - AsyncWorkloadUser (weight=3): 비동기 워크로드")
    print("   - RealisticUser (weight=4): 실제 사용자 패턴")
    print("   - StressTestUser (weight=2): 스트레스 테스트")
    print(" ")
    print(" 요청 패턴:")
    print("   - 단순 요청: 50%")
    print("   - I/O 대기: 20%")
    print("   - DB 조회: 20%")
    print("   - 무거운 작업: 10%")
    print(" ")
    print(" 실행 권장:")
    print("   단일 인스턴스: --users=100 --spawn-rate=10")
    print("   다중 인스턴스: --users=500 --spawn-rate=20")
    print("=" * 70 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """테스트 종료 시 실행"""
    stats = environment.stats
    print("\n" + "=" * 70)
    print(" 혼합 부하 성능 테스트 완료")
    print("=" * 70)
    print(f" 총 요청 수: {stats.total.num_requests:,}")
    print(f" 실패 수: {stats.total.num_failures:,}")
    print(f" 평균 응답 시간: {stats.total.avg_response_time:.2f}ms")
    print(f" 최대 응답 시간: {stats.total.max_response_time:.2f}ms")
    if stats.total.num_requests > 0:
        print(f" RPS: {stats.total.total_rps:.2f}")
    print("=" * 70 + "\n")
