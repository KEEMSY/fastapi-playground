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
        path: 'sync-test-with-await',
        name: '동기 메서드 + 동기 대기'
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
        name: "시나리오 1: 비동기 메서드 + 비동기 대기 (3회 반복)",
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
        name: "시나리오 2: 비동기 메서드 + 동기 대기 (3회 반복)",
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
        name: "시나리오 3: 동기 메서드 + 동기 대기 (3회 반복)",
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
        name: "시나리오 4: 대규모 동시 요청 (비동기+비동기, 50개)",
        description: "단일 시점에 50개의 요청을 비동기 방식으로 처리 (이상적인 비동기 처리)",
        endpoints: Array(50).fill().map(() => (
            { type: EndpointType.ASYNC_WITH_ASYNC_WAIT, timeout: 2 }
        )),
        iterations: 1
    },
    {
        name: "시나리오 5: 대규모 동시 요청 (비동기+동기, 50개)",
        description: "단일 시점에 50개의 요청을 비동기+동기 방식으로 처리 (스레드 블로킹)",
        endpoints: Array(50).fill().map(() => (
            { type: EndpointType.ASYNC_WITH_SYNC_WAIT, timeout: 2 }
        )),
        iterations: 1
    },
    {
        name: "시나리오 6: 대규모 동시 요청 (동기+동기, 50개)",
        description: "단일 시점에 50개의 요청을 동기 방식으로 처리 (전통적인 블로킹 방식)",
        endpoints: Array(50).fill().map(() => (
            { type: EndpointType.SYNC_WITH_WAIT, timeout: 2 }
        )),
        iterations: 1
    }
];

// 시나리오 실행 함수
export async function runScenario(scenarioConfig) {
    const startTime = performance.now();
    let allResults = [];
    let iterationTimes = [];  // 각 반복의 실행 시간 저장
    let totalExpectedTime = 0;

    // 이론적인 총 대기 시간 계산
    scenarioConfig.endpoints.forEach(endpoint => {
        totalExpectedTime += endpoint.timeout;
    });

    for (let i = 0; i < scenarioConfig.iterations; i++) {
        const iterationStartTime = performance.now();

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
    }

    const endTime = performance.now();
    const totalTime = endTime - startTime;
    const theoreticalTimeMs = totalExpectedTime * 1000;  // 1회당 이론적 시간 (ms)
    const totalTheoreticalTime = theoreticalTimeMs * scenarioConfig.iterations;

    // 효율성 = (이론적 시간 / 실제 시간) * 100
    // 예: 이론적으로 20초 걸리는 작업이 10초만에 완료되면 200% 효율
    const efficiency = (theoreticalTimeMs / (totalTime / scenarioConfig.iterations)) * 100;

    const metrics = {
        scenarioName: scenarioConfig.name,
        description: scenarioConfig.description,
        totalTime,                                       // 전체 실제 실행 시간 (ms)
        theoreticalTimePerIteration: theoreticalTimeMs,  // 1회당 이론적 시간 (ms)
        totalTheoreticalTime,                           // 전체 이론적 시간 (ms)
        endpointResults: allResults,
        averageIterationTime: iterationTimes.reduce((acc, time) => acc + time, 0) / scenarioConfig.iterations,  // 반복당 평균 시간 (전체 요청 세트)
        averageRequestTime: allResults.reduce((acc, result) => acc + result.time, 0) / allResults.length,  // 개별 요청의 평균 시간
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