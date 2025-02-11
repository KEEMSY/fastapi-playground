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
- 대기 요청은 10초의 대기 시간 포함
- 일반 요청은 대기 시간 없음
"""

BASE_URL = "http://localhost:7777"
WAIT_REQUESTS = 50  # 대기 요청 수
NORMAL_REQUESTS = 50  # 일반 요청 수

async def async_request(session, url, payload):
    start_time = time.time()
    async with session.post(url, json=payload) as response:
        result = await response.json()
        end_time = time.time()
        return end_time - start_time

def sync_request(url, payload):
    start_time = time.time()
    response = requests.post(url, json=payload)
    result = response.json()
    end_time = time.time()
    return end_time - start_time

async def run_mixed_async_test(wait_endpoint, normal_endpoint, wait_payload, normal_payload):
    async with aiohttp.ClientSession() as session:
        # 대기 요청과 일반 요청을 모두 포함
        wait_tasks = [async_request(session, f"{BASE_URL}/{wait_endpoint}", wait_payload) 
                     for _ in range(WAIT_REQUESTS)]
        normal_tasks = [async_request(session, f"{BASE_URL}/{normal_endpoint}", normal_payload) 
                       for _ in range(NORMAL_REQUESTS)]
        all_tasks = wait_tasks + normal_tasks
        return await asyncio.gather(*all_tasks)

def run_mixed_sync_test(wait_endpoint, normal_endpoint, wait_payload, normal_payload):
    with ThreadPoolExecutor(max_workers=WAIT_REQUESTS + NORMAL_REQUESTS) as executor:
        # 대기 요청과 일반 요청을 모두 포함
        wait_futures = [executor.submit(sync_request, f"{BASE_URL}/{wait_endpoint}", wait_payload) 
                       for _ in range(WAIT_REQUESTS)]
        normal_futures = [executor.submit(sync_request, f"{BASE_URL}/{normal_endpoint}", normal_payload) 
                         for _ in range(NORMAL_REQUESTS)]
        all_futures = wait_futures + normal_futures
        return [f.result() for f in all_futures]

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
        "현재 프로세스 메모리 사용": f"{process.memory_info().rss / 1024 / 1024:.1f} MB"
    }

async def main():
    results = {
        "시나리오": [],
        "대기요청_엔드포인트": [],
        "일반요청_엔드포인트": [],
        "클라이언트_실행방식": [],
        "총처리시간": [],
        "대기요청평균": [],
        "일반요청평균": [],
        "전체평균응답": [],
        "테스트시각": []
    }

    # 테스트 시나리오 정의
    scenarios = [
        # 1. 비동기 엔드포인트 + 비동기 대기
        ("[비동기 엔드포인트 + 비동기 대기] + 단순 동기", 
         "async-example/async-wait", "sync-example", "비동기 클라이언트",
         {"name": "비동기 대기", "description": "10초 대기"},
         {"name": "일반 요청", "description": "대기 없음"}),
        ("[비동기 엔드포인트 + 비동기 대기] + 단순 비동기", 
         "async-example/async-wait", "async-example", "비동기 클라이언트",
         {"name": "비동기 대기", "description": "10초 대기"},
         {"name": "일반 요청", "description": "대기 없음"}),

        # 2. 비동기 엔드포인트 + 동기 대기
        ("[비동기 엔드포인트 + 동기 대기] + 단순 동기", 
         "async-example/sync-wait", "sync-example", "비동기 클라이언트",
         {"name": "동기 대기", "description": "10초 대기"},
         {"name": "일반 요청", "description": "대기 없음"}),
        ("[비동기 엔드포인트 + 동기 대기] + 단순 비동기", 
         "async-example/sync-wait", "async-example", "비동기 클라이언트",
         {"name": "동기 대기", "description": "10초 대기"},
         {"name": "일반 요청", "description": "대기 없음"}),

        # 3. 동기 엔드포인트 + 동기 대기
        ("[동기 엔드포인트 + 동기 대기] + 단순 동기", 
         "sync-example/sync-wait", "sync-example", "동기 클라이언트",
         {"name": "동기 대기", "description": "10초 대기"},
         {"name": "일반 요청", "description": "대기 없음"}),
        ("[동기 엔드포인트 + 동기 대기] + 단순 비동기", 
         "sync-example/sync-wait", "async-example", "동기 클라이언트",
         {"name": "동기 대기", "description": "10초 대기"},
         {"name": "일반 요청", "description": "대기 없음"})
    ]

    print("\n" + "🚀 성능 테스트 시작 🚀".center(60))
    print("=" * 60)
    print(f"📊 대기 요청 수: {WAIT_REQUESTS}")
    print(f"📊 일반 요청 수: {NORMAL_REQUESTS}")
    print(f"⏱️  대기 시간: 10초")
    print("=" * 60)

    for scenario_name, wait_endpoint, normal_endpoint, client_type, wait_payload, normal_payload in scenarios:
        print("\n" + "▼" * 60)
        print(f"📌 테스트 시나리오: {scenario_name}".center(60))
        print("▲" * 60)
        print(f"🔹 대기 요청 엔드포인트: {wait_endpoint}")
        print(f"🔸 일반 요청 엔드포인트: {normal_endpoint}")
        print(f"📡 클라이언트 실행 방식: {client_type}")
        print("-" * 60)
        
        try:
            start_time = time.time()
            
            if "비동기" in client_type:
                print("⚡ 비동기 클라이언트로 요청 실행 중 (동시 처리)")
                times = await run_mixed_async_test(wait_endpoint, normal_endpoint, 
                                                 wait_payload, normal_payload)
            else:
                print("🔄 동기 클라이언트로 요청 실행 중 (스레드풀 사용)")
                times = run_mixed_sync_test(wait_endpoint, normal_endpoint, 
                                          wait_payload, normal_payload)

            total_time = time.time() - start_time
            
            wait_times = times[:WAIT_REQUESTS]
            normal_times = times[WAIT_REQUESTS:]
            
            results["시나리오"].append(scenario_name)
            results["대기요청_엔드포인트"].append(wait_endpoint)
            results["일반요청_엔드포인트"].append(normal_endpoint)
            results["클라이언트_실행방식"].append(client_type)
            results["총처리시간"].append(total_time)
            results["대기요청평균"].append(sum(wait_times) / len(wait_times))
            results["일반요청평균"].append(sum(normal_times) / len(normal_times))
            results["전체평균응답"].append(sum(times) / len(times))
            results["테스트시각"].append(datetime.now())

            print("\n📊 테스트 결과:")
            print(f"⏱️  총 처리 시간: {total_time:.2f}초")
            print(f"🔹 대기 요청 평균: {sum(wait_times) / len(wait_times):.2f}초")
            print(f"🔸 일반 요청 평균: {sum(normal_times) / len(normal_times):.2f}초")
            print(f"📈 전체 평균 응답: {sum(times) / len(times):.2f}초")
        
        except Exception as e:
            print(f"❌ 테스트 중 오류 발생 ({scenario_name}): {str(e)}")
            continue

    # 결과를 DataFrame으로 변환하고 CSV로 저장
    df = pd.DataFrame(results)
    filename = f"성능테스트결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    print(f"\n💾 결과가 저장됨: {filename}")

    # 시나리오별 분석 출력
    print("\n" + "📊 시나리오별 분석 결과 📊".center(60))
    print("=" * 60)
    for scenario in df['시나리오'].unique():
        scenario_df = df[df['시나리오'] == scenario]
        best_case = scenario_df.loc[scenario_df['총처리시간'].idxmin()]
        print("\n" + f"🎯 시나리오: {scenario}".center(60))
        print("-" * 60)
        print("✨ 최적 성능:")
        print(f"🎯 시나리오: {best_case['시나리오']}")
        print(f"🔹 대기 요청 엔드포인트: {best_case['대기요청_엔드포인트']}")
        print(f"🔸 일반 요청 엔드포인트: {best_case['일반요청_엔드포인트']}")
        print(f"📡 클라이언트 실행 방식: {best_case['클라이언트_실행방식']}")
        print(f"⏱️  총 처리 시간: {best_case['총처리시간']:.2f}초")

    # 전체 최고/최저 성능 비교
    print("\n" + "🏆 전체 성능 비교 🏆".center(60))
    print("=" * 60)
    
    # 시스템 정보 출력
    print("\n🖥️  시스템 동시성 정보:")
    print("-" * 60)
    system_info = get_system_info()
    for key, value in system_info.items():
        print(f"• {key}: {value}")
    
    best_overall = df.loc[df['총처리시간'].idxmin()]
    worst_overall = df.loc[df['총처리시간'].idxmax()]
    
    print("\n✨ 가장 좋은 성능:")
    print("-" * 60)
    print(f"🎯 시나리오: {best_overall['시나리오']}")
    print(f"🔹 대기 요청 엔드포인트: {best_overall['대기요청_엔드포인트']}")
    print(f"🔸 일반 요청 엔드포인트: {best_overall['일반요청_엔드포인트']}")
    print(f"📡 클라이언트 실행 방식: {best_overall['클라이언트_실행방식']}")
    print(f"⏱️  총 처리 시간: {best_overall['총처리시간']:.2f}초")
    print(f"📊 동시 처리된 총 요청 수: {WAIT_REQUESTS + NORMAL_REQUESTS}")
    print(f"🔄 초당 처리된 요청 수: {(WAIT_REQUESTS + NORMAL_REQUESTS) / best_overall['총처리시간']:.1f}")
    
    print("\n❌ 가장 나쁜 성능:")
    print("-" * 60)
    print(f"🎯 시나리오: {worst_overall['시나리오']}")
    print(f"🔹 대기 요청 엔드포인트: {worst_overall['대기요청_엔드포인트']}")
    print(f"🔸 일반 요청 엔드포인트: {worst_overall['일반요청_엔드포인트']}")
    print(f"📡 클라이언트 실행 방식: {worst_overall['클라이언트_실행방식']}")
    print(f"⏱️  총 처리 시간: {worst_overall['총처리시간']:.2f}초")
    print(f"📊 동시 처리된 총 요청 수: {WAIT_REQUESTS + NORMAL_REQUESTS}")
    print(f"🔄 초당 처리된 요청 수: {(WAIT_REQUESTS + NORMAL_REQUESTS) / worst_overall['총처리시간']:.1f}")

    improvement = (worst_overall['총처리시간'] - best_overall['총처리시간']) / worst_overall['총처리시간'] * 100
    print("\n📈 성능 차이:")
    print("-" * 60)
    print(f"✨ 최고 성능이 최저 성능보다 {improvement:.1f}% 더 빠름")
    print(f"📊 최고 성능 처리량: {(WAIT_REQUESTS + NORMAL_REQUESTS) / best_overall['총처리시간']:.1f} 요청/초")
    print(f"📊 최저 성능 처리량: {(WAIT_REQUESTS + NORMAL_REQUESTS) / worst_overall['총처리시간']:.1f} 요청/초")

    # 동시성 관련 추가 정보
    print("\n🔄 동시성 처리 정보:")
    print("-" * 60)
    print(f"• 스레드풀 최대 작업자 수: {WAIT_REQUESTS + NORMAL_REQUESTS}")
    print(f"• 비동기 클라이언트 동시 요청 수: {WAIT_REQUESTS + NORMAL_REQUESTS}")
    print(f"• 대기 요청 비율: {WAIT_REQUESTS/(WAIT_REQUESTS + NORMAL_REQUESTS)*100:.1f}%")
    print(f"• 일반 요청 비율: {NORMAL_REQUESTS/(WAIT_REQUESTS + NORMAL_REQUESTS)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(main()) 