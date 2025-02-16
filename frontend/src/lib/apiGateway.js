import { writable } from 'svelte/store';

// 성능 측정을 위한 store
export const performanceMetrics = writable({
    totalTime: 0,
    endpointMetrics: []
});

// API 엔드포인트 타입 정의
export const EndpointType = {
    // 대기 요청 타입
    ASYNC_WITH_ASYNC_WAIT: {
        path: 'async-test-with-await-with-async',
        name: '비동기 메서드 + 비동기 대기'
    },
    ASYNC_WITH_SYNC_WAIT: {
        path: 'async-test-with-await-with-sync',
        name: '비동기 메서드 + 동기 대기'
    },
    SYNC_WITH_WAIT: {
        path: 'sync-test-with-wait',
        name: '동기 메서드 + 동기 대기'
    },

    // DB 세션 요청 타입 수정
    SYNC_WITH_SYNC_DB: {
        path: 'sync-test-with-sync-db-session',  // 이미 구현된 엔드포인트와 일치
        name: '동기 메서드 + 동기 DB 세션'
    },
    ASYNC_WITH_SYNC_DB: {
        path: 'async-test-with-async-db-session-with-sync',  // 이미 구현된 엔드포인트와 일치
        name: '비동기 메서드 + 동기 DB 세션'
    },
    ASYNC_WITH_ASYNC_DB: {
        path: 'async-test-with-async-db-session',  // 이미 구현된 엔드포인트와 일치
        name: '비동기 메서드 + 비동기 DB 세션'
    }
};

// 개별 API 호출 함수
async function callEndpoint(endpoint, timeout = null) {
    const startTime = performance.now();
    const url = new URL(`http://localhost:7777/api/v1/standard/${endpoint.path}`);

    if (timeout !== null) {
        url.searchParams.append('timeout', timeout);
    }

    try {
        const response = await fetch(url);
        const data = await response.json();
        const endTime = performance.now();

        return {
            endpoint: endpoint.name,
            path: endpoint.path,
            timeout: timeout,
            success: true,
            time: endTime - startTime,
            data
        };
    } catch (error) {
        const endTime = performance.now();
        return {
            endpoint: endpoint.name,
            path: endpoint.path,
            timeout: timeout,
            success: false,
            time: endTime - startTime,
            error: error.message
        };
    }
}

// 성능 비교를 위한 시나리오 정의
export const TestScenarios = [
    {
        name: "시나리오 1: 비동기 메서드 + 비동기 대기 (1 Loop 당 요청 10회, 3 Loop 반복)",
        description: "비동기 메서드에서 비동기 대기를 사용하는 경우 (이상적인 비동기 처리)",
        endpoints: [
            { type: EndpointType.ASYNC_WITH_ASYNC_WAIT, timeout: 1 },
            { type: EndpointType.ASYNC_WITH_ASYNC_WAIT, timeout: 2 },
            { type: EndpointType.ASYNC_WITH_ASYNC_WAIT, timeout: 3 },
            { type: EndpointType.ASYNC_WITH_ASYNC_WAIT, timeout: 2 },
            { type: EndpointType.ASYNC_WITH_ASYNC_WAIT, timeout: 1 },
            { type: EndpointType.ASYNC_WITH_ASYNC_WAIT, timeout: 3 },
            { type: EndpointType.ASYNC_WITH_ASYNC_WAIT, timeout: 2 },
            { type: EndpointType.ASYNC_WITH_ASYNC_WAIT, timeout: 1 },
            { type: EndpointType.ASYNC_WITH_ASYNC_WAIT, timeout: 3 },
            { type: EndpointType.ASYNC_WITH_ASYNC_WAIT, timeout: 2 }
        ],
        iterations: 3
    },
    {
        name: "시나리오 2: 비동기 메서드 + 동기 대기 (1 Loop 당 요청 10회, 3 Loop 반복)",
        description: "비동기 메서드에서 동기 대기를 사용하는 경우 (스레드 블로킹)",
        endpoints: [
            { type: EndpointType.ASYNC_WITH_SYNC_WAIT, timeout: 1 },
            { type: EndpointType.ASYNC_WITH_SYNC_WAIT, timeout: 2 },
            { type: EndpointType.ASYNC_WITH_SYNC_WAIT, timeout: 3 },
            { type: EndpointType.ASYNC_WITH_SYNC_WAIT, timeout: 2 },
            { type: EndpointType.ASYNC_WITH_SYNC_WAIT, timeout: 1 },
            { type: EndpointType.ASYNC_WITH_SYNC_WAIT, timeout: 3 },
            { type: EndpointType.ASYNC_WITH_SYNC_WAIT, timeout: 2 },
            { type: EndpointType.ASYNC_WITH_SYNC_WAIT, timeout: 1 },
            { type: EndpointType.ASYNC_WITH_SYNC_WAIT, timeout: 3 },
            { type: EndpointType.ASYNC_WITH_SYNC_WAIT, timeout: 2 }
        ],
        iterations: 3
    },
    {
        name: "시나리오 3: 동기 메서드 + 동기 대기 (1 Loop 당 요청 10회, 3 Loop 반복)",
        description: "동기 메서드에서 동기 대기를 사용하는 경우 (전통적인 블로킹 방식)",
        endpoints: [
            { type: EndpointType.SYNC_WITH_WAIT, timeout: 1 },
            { type: EndpointType.SYNC_WITH_WAIT, timeout: 2 },
            { type: EndpointType.SYNC_WITH_WAIT, timeout: 3 },
            { type: EndpointType.SYNC_WITH_WAIT, timeout: 2 },
            { type: EndpointType.SYNC_WITH_WAIT, timeout: 1 },
            { type: EndpointType.SYNC_WITH_WAIT, timeout: 3 },
            { type: EndpointType.SYNC_WITH_WAIT, timeout: 2 },
            { type: EndpointType.SYNC_WITH_WAIT, timeout: 1 },
            { type: EndpointType.SYNC_WITH_WAIT, timeout: 3 },
            { type: EndpointType.SYNC_WITH_WAIT, timeout: 2 }
        ],
        iterations: 3
    },
    {
        name: "시나리오 4: 대규모 동시 요청 (비동기 메서드 + 비동기 대기, 50개)",
        description: "단일 시점에 50개의 요청을 비동기 메서드 + 비동기 대기 방식으로 처리 (이상적인 비동기 처리)",
        endpoints: Array(50).fill().map((_, index) => ({
            type: EndpointType.ASYNC_WITH_ASYNC_WAIT,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },
    {
        name: "시나리오 5: 대규모 동시 요청 (비동기 메서드 + 동기 대기, 50개)",
        description: "단일 시점에 50개의 요청을 비동기 메서드 + 동기 대기 방식으로 처리 (스레드 블로킹)",
        endpoints: Array(50).fill().map((_, index) => ({
            type: EndpointType.ASYNC_WITH_SYNC_WAIT,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },
    {
        name: "시나리오 6: 대규모 동시 요청 (동기 메서드 + 동기 대기, 50개)",
        description: "단일 시점에 50개의 요청을 동기 메서드 + 동기 대기 방식으로 처리 (전통적인 블로킹 방식)",
        endpoints: Array(50).fill().map((_, index) => ({
            type: EndpointType.SYNC_WITH_WAIT,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },
    // DB 세션 시나리오 수정 및 추가
    {
        name: "시나리오 7: 동기 메서드 + 동기 DB 세션 (10회 요청)",
        description: "전통적인 동기 방식의 DB 세션 처리",
        endpoints: Array(10).fill().map((_, index) => ({
            type: EndpointType.SYNC_WITH_SYNC_DB,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },
    {
        name: "시나리오 8: 비동기 메서드 + 동기 DB 세션 (10회 요청)",
        description: "비동기 메서드에서 동기 DB 세션 사용 (안티패턴)",
        endpoints: Array(10).fill().map((_, index) => ({
            type: EndpointType.ASYNC_WITH_SYNC_DB,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },
    {
        name: "시나리오 9: 비동기 메서드 + 비동기 DB 세션 (10회 요청)",
        description: "이상적인 비동기 DB 세션 처리",
        endpoints: Array(10).fill().map((_, index) => ({
            type: EndpointType.ASYNC_WITH_ASYNC_DB,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },
    {
        name: "시나리오 10: 대규모 동시 요청 - 동기 DB (50개)",
        description: "대규모 동시 요청에서의 동기 DB 세션 성능",
        endpoints: Array(50).fill().map((_, index) => ({
            type: EndpointType.SYNC_WITH_SYNC_DB,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },
    {
        name: "시나리오 11: 대규모 동시 요청 - 비동기 메서드 + 동기 DB (50개)",
        description: "대규모 동시 요청에서의 비동기-동기 혼합 DB 세션 성능 (안티패턴)",
        endpoints: Array(50).fill().map((_, index) => ({
            type: EndpointType.ASYNC_WITH_SYNC_DB,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },
    {
        name: "시나리오 12: 대규모 동시 요청 - 비동기 DB (50개)",
        description: "대규모 동시 요청에서의 비동기 DB 세션 성능 (이상적인 패턴)",
        endpoints: Array(50).fill().map((_, index) => ({
            type: EndpointType.ASYNC_WITH_ASYNC_DB,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },
    {
        name: "시나리오 13: 초대규모 동시 요청 - 동기 DB (100개)",
        description: "초대규모 동시 요청에서의 동기 DB 세션 한계 테스트",
        endpoints: Array(100).fill().map((_, index) => ({
            type: EndpointType.SYNC_WITH_SYNC_DB,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },
    {
        name: "시나리오 14: 초대규모 동시 요청 - 비동기 DB (100개)",
        description: "초대규모 동시 요청에서의 비동기 DB 세션 한계 테스트",
        endpoints: Array(100).fill().map((_, index) => ({
            type: EndpointType.ASYNC_WITH_ASYNC_DB,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },
    {
        name: "시나리오 15: 초대규모 동시 요청 - 비동기 메서드 + 동기 DB (100개)",
        description: "초대규모 동시 요청에서의 비동기-동기 혼합 DB 세션 한계 테스트",
        endpoints: Array(100).fill().map((_, index) => ({
            type: EndpointType.ASYNC_WITH_SYNC_DB,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },
];

// 시나리오 실행 함수
export async function runScenario(scenarioConfig) {
    console.log('Starting scenario:', scenarioConfig.name); // 시나리오 시작 로그
    const startTime = performance.now();
    let allResults = [];
    let iterationTimes = [];
    let totalExpectedTime = 0;

    // 이론적인 총 대기 시간 계산
    scenarioConfig.endpoints.forEach(endpoint => {
        totalExpectedTime += endpoint.timeout;
    });

    for (let i = 0; i < scenarioConfig.iterations; i++) {
        console.log(`Starting iteration ${i + 1} of ${scenarioConfig.iterations}`); // 반복 시작 로그
        const iterationStartTime = performance.now();

        try {
            const results = await Promise.all(
                scenarioConfig.endpoints.map(endpoint =>
                    callEndpoint(endpoint.type, endpoint.timeout)
                )
            );

            const iterationTime = performance.now() - iterationStartTime;
            iterationTimes.push(iterationTime);

            allResults = [...allResults, ...results.map(r => ({
                ...r,
                iterationNumber: i + 1,
                iterationTime
            }))];

            console.log(`Iteration ${i + 1} completed`); // 반복 완료 로그
        } catch (error) {
            console.error(`Error in iteration ${i + 1}:`, error); // 반복 에러 로그
        }
    }

    const endTime = performance.now();
    const totalTime = endTime - startTime;
    const theoreticalTimeMs = totalExpectedTime * 1000;
    const totalTheoreticalTime = theoreticalTimeMs * scenarioConfig.iterations;
    const efficiency = (theoreticalTimeMs / (totalTime / scenarioConfig.iterations)) * 100;

    const metrics = {
        scenarioName: scenarioConfig.name,
        description: scenarioConfig.description,
        totalTime,
        theoreticalTimePerIteration: theoreticalTimeMs,
        totalTheoreticalTime,
        endpointResults: allResults,
        averageIterationTime: iterationTimes.reduce((acc, time) => acc + time, 0) / scenarioConfig.iterations,
        averageRequestTime: allResults.reduce((acc, result) => acc + result.time, 0) / allResults.length,
        averageTimeout: allResults.reduce((acc, result) => acc + (result.timeout * 1000), 0) / allResults.length,
        successRate: allResults.filter(r => r.success).length / allResults.length,
        iterations: scenarioConfig.iterations,
        totalRequests: scenarioConfig.endpoints.length * scenarioConfig.iterations,
        iterationTimes,
        efficiency,
        overhead: (totalTime / scenarioConfig.iterations) - theoreticalTimeMs
    };

    performanceMetrics.update(current => ({
        ...current,
        endpointMetrics: [...current.endpointMetrics, metrics]
    }));

    return metrics;
} 