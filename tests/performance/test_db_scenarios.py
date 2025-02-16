import asyncio
import time
import aiohttp
import pandas as pd
from datetime import datetime
import os
import psutil
import multiprocessing
import threading
import statistics
from collections import Counter

"""
DB 세션 성능 테스트 시나리오:

1. 시나리오 1: 동기 메서드 + 동기 DB 세션
   - 동시에 100개의 요청을 보내고 처리 성능 측정

2. 시나리오 2: 비동기 메서드 + 비동기 DB 세션
   - 동시에 100개의 요청을 보내고 처리 성능 측정

3. 시나리오 3: 비동기 메서드 + 동기 DB 세션
   - 동시에 100개의 요청을 보내고 처리 성능 측정

테스트 조건:
- 각 시나리오별로 100개의 동시 요청 수행
- 각 요청은 1초의 대기 시간 포함
- 성능 측정 지표: 초당 처리량, 응답 시간, 성공률
"""

BASE_URL = "http://localhost:7777/api/v1/standard"
CONCURRENT_REQUESTS = 100  # 동시 요청 수
WAIT_TIME = 1  # 대기 시간

async def async_request(session, url):
    start_time = time.time()
    try:
        async with session.get(url) as response:
            result = await response.json()
            end_time = time.time()
            
            message = result.get("data", {}).get("message", "")
            session_info = result.get("data", {}).get("session_info", {})
            
            server_info = {}
            if "PID:" in message:
                info_part = message.split("(")[1].split(")")[0]
                parts = info_part.split(", ")
                server_info = {
                    "server_process_id": parts[0].split(": ")[1],
                    "server_worker_id": parts[1].split(": ")[1],
                    "server_thread_id": parts[2].split(": ")[1]
                }
            
            return {
                "time": end_time - start_time,
                "status": response.status,
                "client_process_id": os.getpid(),
                "total_connections": session_info.get("total_connections", 0),
                "active_connections": session_info.get("active_connections", 0),
                **server_info
            }
    except Exception as e:
        return {
            "time": time.time() - start_time,
            "status": 500,
            "error": str(e),
            "client_process_id": os.getpid()
        }

async def run_scenario_test(endpoint, scenario_name):
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        process_id = os.getpid()
        worker_id = multiprocessing.current_process().name
        thread_id = threading.current_thread().name

        url = f"{BASE_URL}/{endpoint}"
        tasks = [async_request(session, f"{url}?timeout={WAIT_TIME}") for _ in range(CONCURRENT_REQUESTS)]
        responses = await asyncio.gather(*tasks)

        total_time = time.time() - start_time
        success_count = sum(1 for r in responses if r["status"] == 200)
        fail_count = len(responses) - success_count

        print("\n" + "=" * 80)
        print(f"🎯 시나리오: {scenario_name}".center(80))
        print("=" * 80)

        print("\n🔄 실행 정보:")
        print(f"├─ 엔드포인트: {url}")
        print(f"├─ 동시 요청 수: {CONCURRENT_REQUESTS}")
        print(f"└─ 대기 시간: {WAIT_TIME}초")

        print("\n⏱️  성능 측정 결과:")
        print(f"├─ 총 처리 시간: {total_time:.2f}초")
        print(f"├─ 평균 응답 시간: {statistics.mean(r['time'] for r in responses):.2f}초")
        print(f"├─ 최대 응답 시간: {max(r['time'] for r in responses):.2f}초")
        print(f"├─ 최소 응답 시간: {min(r['time'] for r in responses):.2f}초")
        print(f"└─ 초당 처리량: {len(responses)/total_time:.1f} 요청/초")

        print("\n📊 요청 처리 결과:")
        print(f"├─ 성공: {success_count}/{len(responses)} ({success_count/len(responses)*100:.1f}%)")
        print(f"└─ 실패: {fail_count}/{len(responses)} ({fail_count/len(responses)*100:.1f}%)")

        if success_count > 0:
            print("\n📈 DB 연결 상태:")
            max_connections = max(r.get("total_connections", 0) for r in responses if r["status"] == 200)
            max_active = max(r.get("active_connections", 0) for r in responses if r["status"] == 200)
            print(f"├─ 최대 전체 연결 수: {max_connections}")
            print(f"└─ 최대 활성 연결 수: {max_active}")

        # 워커/스레드 통계
        if success_count > 0:
            print("\n🔄 워커/스레드 분포:")
            worker_counts = Counter(r["server_worker_id"] for r in responses if "server_worker_id" in r)
            thread_counts = Counter(r["server_thread_id"] for r in responses if "server_thread_id" in r)
            
            print("├─ 워커 분포:")
            for worker, count in worker_counts.items():
                print(f"│  └─ {worker}: {count}개 요청")
            print("└─ 스레드 분포:")
            for thread, count in thread_counts.items():
                print(f"   └─ {thread}: {count}개 요청")

        return {
            "시나리오": scenario_name,
            "총처리시간": total_time,
            "평균응답시간": statistics.mean(r["time"] for r in responses),
            "성공률": success_count/len(responses)*100,
            "초당처리량": len(responses)/total_time,
            "최대_전체_연결수": max_connections if success_count > 0 else 0,
            "최대_활성_연결수": max_active if success_count > 0 else 0
        }

async def main():
    scenarios = [
        {
            "name": "시나리오 1: 동기 메서드 + 동기 DB 세션",
            "endpoint": "sync-test-with-sync-db-session",
            "description": "동기 메서드에서 동기 DB 세션 사용"
        },
        {
            "name": "시나리오 2: 비동기 메서드 + 비동기 DB 세션",
            "endpoint": "async-test-with-async-db-session",
            "description": "비동기 메서드에서 비동기 DB 세션 사용"
        },
        {
            "name": "시나리오 3: 비동기 메서드 + 동기 DB 세션",
            "endpoint": "async-test-with-async-db-session-with-sync",
            "description": "비동기 메서드에서 동기 DB 세션 사용"
        }
    ]

    print("\n" + "🚀 DB 세션 성능 테스트 시작 🚀".center(80))
    print("=" * 80)
    print(f"• 동시 요청 수: {CONCURRENT_REQUESTS}")
    print(f"• 요청 대기 시간: {WAIT_TIME}초")
    print("=" * 80)

    results = []
    for scenario in scenarios:
        try:
            result = await run_scenario_test(scenario["endpoint"], scenario["name"])
            results.append(result)
        except Exception as e:
            print(f"\n❌ 오류 발생 ({scenario['name']}): {str(e)}")
            continue

    if results:
        df = pd.DataFrame(results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"DB_세션_성능테스트결과_{timestamp}.csv"
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"\n💾 결과가 저장됨: {filename}")

        best_performance = df.loc[df["초당처리량"].idxmax()]
        print("\n🏆 최고 성능 시나리오:")
        print(f"├─ 시나리오: {best_performance['시나리오']}")
        print(f"├─ 초당 처리량: {best_performance['초당처리량']:.1f} 요청/초")
        print(f"├─ 평균 응답 시간: {best_performance['평균응답시간']:.2f}초")
        print(f"└─ 성공률: {best_performance['성공률']:.1f}%")

if __name__ == "__main__":
    asyncio.run(main()) 