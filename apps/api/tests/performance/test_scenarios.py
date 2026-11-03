import asyncio
import time
import aiohttp
import requests
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import os
import psutil
import multiprocessing
import threading
import statistics
from collections import Counter

"""
성능 테스트 시나리오:

1. 비동기 엔드포인트 + 비동기 대기(10초) 테스트
   - 비동기 대기 요청 50개 + 단순 동기 요청 50개
   - 비동기 대기 요청 50개 + 단순 비동기 요청 50개

2. 비동기 엔드포인트 + 동기 대기(10초) 테스트
   - 동기 대기 요청 50개 + 단순 동기 요청 50개
   - 동기 대기 요청 50개 + 단순 비동기 요청 50개

3. 동기 엔드포인트 + 동기 대기(10초) 테스트
   - 동기 대기 요청 50개 + 단순 동기 요청 50개
   - 동기 대기 요청 50개 + 단순 비동기 요청 50개

테스트 조건:
- 각 시나리오는 대기 요청 50개 + 일반 요청 50개로 구성
- 대기 요청은 1초의 대기 시간 포함
- 일반 요청은 대기 시간 없음
"""

BASE_URL = "http://localhost:7777/api/v1/standard"
WAIT_REQUESTS = 50  # 대기 요청 수
NORMAL_REQUESTS = 50  # 일반 요청 수
WAIT_TIME = 1  # 대기 시간


async def async_request(session, url):
    """
    클라이언트 역할을 하는 메서드
    - 고객은 요청을 동시다발적으로 보낼 수 있음
    """
    start_time = time.time()
    async with session.get(url) as response:
        result = await response.json()
        end_time = time.time()
        
        # 메시지에서 서버 정보 파싱
        message = result.get("data", {}).get("message", "")
        # print(f"Debug - Raw message: {message}")  # 디버그용 로그
        
        server_info = {}
        if "PID:" in message:
            info_part = message.split("(")[1].split(")")[0]
            parts = info_part.split(", ")
            # print(f"Debug - Parsed parts: {parts}")  # 디버그용 로그
            server_info = {
                "server_process_id": parts[0].split(": ")[1],  # 서버 프로세스 ID
                "server_worker_id": parts[1].split(": ")[1],
                "server_thread_id": parts[2].split(": ")[1]
            }
        
        return {
            "time": end_time - start_time,
            "status": response.status,
            "client_process_id": os.getpid(),  # 클라이언트 프로세스 ID
            **server_info
        }


async def run_mixed_test(wait_endpoint, normal_endpoint, scenario_name):
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        process_id = os.getpid()
        worker_id = multiprocessing.current_process().name
        thread_id = threading.current_thread().name

        # URL 구성
        wait_url = f"{BASE_URL}/{wait_endpoint}"
        normal_url = f"{BASE_URL}/{normal_endpoint}"

        # 대기 요청과 일반 요청을 모두 비동기로 처리
        wait_tasks = [async_request(session, wait_url) for _ in range(WAIT_REQUESTS)]
        normal_tasks = [async_request(session, normal_url) for _ in range(NORMAL_REQUESTS)]

        all_tasks = wait_tasks + normal_tasks
        responses = await asyncio.gather(*all_tasks)

        total_time = time.time() - start_time

        # 응답 분리 및 성공/실패 카운트 계산
        wait_responses = responses[:WAIT_REQUESTS]
        normal_responses = responses[WAIT_REQUESTS:]

        wait_success = sum(1 for r in wait_responses if r["status"] == 200)
        wait_fail = WAIT_REQUESTS - wait_success
        normal_success = sum(1 for r in normal_responses if r["status"] == 200)
        normal_fail = NORMAL_REQUESTS - normal_success

        # 결과 출력
        print("\n" + "=" * 80)
        print(f"🎯 시나리오: {scenario_name}".center(80))
        print("=" * 80 + "\n")

        print("🔄 실행 정보:")
        print(f"├─ 프로세스 ID: {process_id}")
        print(f"├─ 워커: {worker_id}")
        print(f"└─ 스레드: {thread_id}")

        print("\n📌 요청 정보:")
        print(f"├─ 대기 요청: {wait_url}")
        print(f"└─ 일반 요청: {normal_url}")

        print("\n⏱️  처리 시간:")
        print(f"├─ 총 처리 시간: {total_time:.2f}초")
        print(f"├─ 대기 요청 평균: {statistics.mean(r['time'] for r in wait_responses):.2f}초")
        print(f"├─ 일반 요청 평균: {statistics.mean(r['time'] for r in normal_responses):.2f}초")
        print(f"└─ 전체 평균 응답: {statistics.mean(r['time'] for r in responses):.2f}초")

        print("\n📊 요청 처리 결과:")
        print("├─ 대기 요청")
        print(f"│  ├─ 성공: {wait_success}/{WAIT_REQUESTS} ({wait_success/WAIT_REQUESTS*100:.1f}%)")
        print(f"│  ├─ 실패: {wait_fail}/{WAIT_REQUESTS} ({wait_fail/WAIT_REQUESTS*100:.1f}%)")
        print(f"│  ├─ 최대 응답 시간: {max(r['time'] for r in wait_responses):.2f}초")
        print(f"│  └─ 최소 응답 시간: {min(r['time'] for r in wait_responses):.2f}초")
        
        # 워커/스레드 통계 추가
        print("│  ├─ 워커 분포:")
        worker_counts = Counter(r["server_worker_id"] for r in wait_responses if r["server_worker_id"])
        for worker, count in worker_counts.items():
            print(f"│  │  └─ {worker}: {count}개 요청")
        print("│  └─ 스레드 분포:")
        thread_counts = Counter(r["server_thread_id"] for r in wait_responses if r["server_thread_id"])
        for thread, count in thread_counts.items():
            print(f"│     └─ {thread}: {count}개 요청")

        print("└─ 일반 요청")
        print(f"   ├─ 성공: {normal_success}/{NORMAL_REQUESTS} ({normal_success/NORMAL_REQUESTS*100:.1f}%)")
        print(f"   ├─ 실패: {normal_fail}/{NORMAL_REQUESTS} ({normal_fail/NORMAL_REQUESTS*100:.1f}%)")
        print(f"   ├─ 최대 응답 시간: {max(r['time'] for r in normal_responses):.2f}초")
        print(f"   └─ 최소 응답 시간: {min(r['time'] for r in normal_responses):.2f}초")
        
        # 워커/스레드 통계 추가
        print("   ├─ 워커 분포:")
        worker_counts = Counter(r["server_worker_id"] for r in normal_responses if r["server_worker_id"])
        for worker, count in worker_counts.items():
            print(f"   │  └─ {worker}: {count}개 요청")
        print("   └─ 스레드 분포:")
        thread_counts = Counter(r["server_thread_id"] for r in normal_responses if r["server_thread_id"])
        for thread, count in thread_counts.items():
            print(f"      └─ {thread}: {count}개 요청")

        return responses


def get_system_info():
    """시스템의 동시성 관련 정보를 반환"""
    process = psutil.Process()
    return {
        "CPU 코어 수": multiprocessing.cpu_count(),
        "물리 CPU 코어 수": psutil.cpu_count(logical=False),
        "논리 CPU 코어 수": psutil.cpu_count(logical=True),
        "현재 프로세스 스레드 수": process.num_threads(),
        "시스템 전체 CPU 사용률": psutil.cpu_percent(interval=1),
        "현재 프로세스 CPU 사용률": process.cpu_percent(interval=1),
        "현재 프로세스 메모리 사용": f"{process.memory_info().rss / 1024 / 1024:.1f} MB",
    }


def get_thread_info():
    process = psutil.Process()
    return {
        "현재 프로세스 스레드 수": process.num_threads(),
        "활성화된 스레드 수": threading.active_count(),
        "현재 스레드 이름": threading.current_thread().name,
    }


async def main():
    # 결과를 저장할 리스트
    results = []

    # 시나리오 정의를 딕셔너리 리스트로 변경
    scenarios = [
        {
            "name": "[비동기 엔드포인트 + 비동기 대기] + 단순 동기",
            "wait_endpoint": "async-test-with-await-with-async",
            "normal_endpoint": "sync-test",
            "client_type": "비동기 클라이언트",
        },
        {
            "name": "[비동기 엔드포인트 + 비동기 대기] + 단순 비동기",
            "wait_endpoint": "async-test-with-await-with-async",
            "normal_endpoint": "async-test",
            "client_type": "비동기 클라이언트",
        },
        {
            "name": "[비동기 엔드포인트 + 동기 대기] + 단순 동기",
            "wait_endpoint": "async-test-with-await-with-sync",
            "normal_endpoint": "sync-test",
            "client_type": "비동기 클라이언트",
        },
        {
            "name": "[비동기 엔드포인트 + 동기 대기] + 단순 비동기",
            "wait_endpoint": "async-test-with-await-with-sync",
            "normal_endpoint": "async-test",
            "client_type": "비동기 클라이언트",
        },
        {
            "name": "[동기 엔드포인트 + 동기 대기] + 단순 동기",
            "wait_endpoint": "sync-test-with-await",
            "normal_endpoint": "sync-test",
            "client_type": "비동기 클라이언트",
        },
        {
            "name": "[동기 엔드포인트 + 동기 대기] + 단순 비동기",
            "wait_endpoint": "sync-test-with-await",
            "normal_endpoint": "async-test",
            "client_type": "비동기 클라이언트",
        },
    ]

    print("\n" + " " * 23 + "🚀 성능 테스트 시작 🚀" + " " * 24)
    print("=" * 60)
    print(f"📊 대기 요청 수: {WAIT_REQUESTS}")
    print(f"📊 일반 요청 수: {NORMAL_REQUESTS}")
    print(f"⏱️  대기 시간: {WAIT_TIME}")
    print("=" * 60 + "\n")

    for scenario in scenarios:
        print("▼" * 60)
        print(f"          📌 테스트 시나리오: {scenario['name']}")
        print("▲" * 60)
        print(f"🔹 대기 요청 엔드포인트: {scenario['wait_endpoint']}")
        print(f"🔸 일반 요청 엔드포인트: {scenario['normal_endpoint']}")
        print(f"📡 클라이언트 실행 방식: {scenario['client_type']}")
        print("-" * 60)

        try:
            start_time = time.time()
            responses = await run_mixed_test(
                scenario["wait_endpoint"], scenario["normal_endpoint"], scenario["name"]
            )
            total_time = time.time() - start_time

            # 응답 분리
            wait_responses = responses[:WAIT_REQUESTS]
            normal_responses = responses[WAIT_REQUESTS:]

            # 결과 저장
            result = {
                "시나리오": scenario["name"],
                "대기요청_엔드포인트": scenario["wait_endpoint"],
                "일반요청_엔드포인트": scenario["normal_endpoint"],
                "클라이언트_타입": scenario["client_type"],
                "총처리시간": total_time,
                "대기요청_평균시간": statistics.mean(r["time"] for r in wait_responses),
                "일반요청_평균시간": statistics.mean(
                    r["time"] for r in normal_responses
                ),
                "전체_평균응답시간": statistics.mean(r["time"] for r in responses),
                "초당처리요청": len(responses) / total_time,
            }
            results.append(result)

            print("-" * 80 + "\n")

        except Exception as e:
            print(f"❌ 테스트 중 오류 발생 ({scenario['name']}): {str(e)}")
            continue

    # DataFrame 생성 및 CSV 저장
    df = pd.DataFrame(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"성능테스트결과_{timestamp}.csv"
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"\n💾 결과가 저장됨: {filename}")

    # 결과 분석 및 출력
    print("\n" + " " * 22 + "📊 시나리오별 분석 결과 📊" + " " * 23)
    print("=" * 60)

    if not df.empty:
        best_overall = df.loc[df["총처리시간"].idxmin()]
        worst_overall = df.loc[df["총처리시간"].idxmax()]

        print("\n✨ 가장 좋은 성능:")
        print("-" * 60)
        print(f"🎯 시나리오: {best_overall['시나리오']}")
        print(f"🔹 대기 요청 엔드포인트: {best_overall['대기요청_엔드포인트']}")
        print(f"🔸 일반 요청 엔드포인트: {best_overall['일반요청_엔드포인트']}")
        print(f"📡 클라이언트 실행 방식: {best_overall['클라이언트_타입']}")
        print(f"⏱️  총 처리 시간: {best_overall['총처리시간']:.2f}초")
        print(f"🔄 초당 처리된 요청 수: {best_overall['초당처리요청']:.1f}")

        print("\n❌ 가장 나쁜 성능:")
        print("-" * 60)
        print(f"🎯 시나리오: {worst_overall['시나리오']}")
        print(f"🔹 대기 요청 엔드포인트: {worst_overall['대기요청_엔드포인트']}")
        print(f"🔸 일반 요청 엔드포인트: {worst_overall['일반요청_엔드포인트']}")
        print(f"📡 클라이언트 실행 방식: {worst_overall['클라이언트_타입']}")
        print(f"⏱️  총 처리 시간: {worst_overall['총처리시간']:.2f}초")
        print(f"🔄 초당 처리된 요청 수: {worst_overall['초당처리요청']:.1f}")

        # 성능 차이 계산
        performance_diff = (
            (worst_overall["총처리시간"] - best_overall["총처리시간"])
            / worst_overall["총처리시간"]
            * 100
        )

        print("\n📈 성능 차이:")
        print("-" * 60)
        print(f"✨ 최고 성능이 최저 성능보다 {performance_diff:.1f}% 더 빠름")
        print(f"📊 최고 성능 처리량: {best_overall['초당처리요청']:.1f} 요청/초")
        print(f"📊 최저 성능 처리량: {worst_overall['초당처리요청']:.1f} 요청/초")
    else:
        print("\n❌ 테스트 결과가 없습니다.")

    # 시스템 정보 출력
    print("\n🖥️  시스템 동시성 정보:")
    print("-" * 60)
    system_info = get_system_info()
    for key, value in system_info.items():
        print(f"• {key}: {value}")

    # 동시성 관련 추가 정보
    print("\n🔄 동시성 처리 정보:")
    print("-" * 60)
    print(f"• 총 요청 수: {WAIT_REQUESTS + NORMAL_REQUESTS}")
    print(f"• 서버 워커 프로세스 수: 2")  # uvicorn --workers 2
    print(f"• 동시 비동기 요청 수: {WAIT_REQUESTS + NORMAL_REQUESTS}")
    print(f"• 대기 요청 비율: {WAIT_REQUESTS/(WAIT_REQUESTS + NORMAL_REQUESTS)*100:.1f}%")
    print(f"• 일반 요청 비율: {NORMAL_REQUESTS/(WAIT_REQUESTS + NORMAL_REQUESTS)*100:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
