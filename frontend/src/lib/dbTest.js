import { writable } from 'svelte/store';

// 성능 측정을 위한 store
export const performanceMetrics = writable({
    totalTime: 0,
    endpointMetrics: []
});

// API 엔드포인트 타입 정의
export const EndpointType = {
    // DB 세션 요청 타입 수정
    SYNC_WITH_SYNC_DB: {
        path: 'sync-test-with-sync-db-session',
        name: '동기 메서드 + 동기 DB 세션'
    },
    ASYNC_WITH_SYNC_DB: {
        path: 'async-test-with-async-db-session-with-sync',
        name: '비동기 메서드 + 동기 DB 세션'
    },
    ASYNC_WITH_ASYNC_DB: {
        path: 'async-test-with-async-db-session',
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
        name: "기본 시나리오 1: 동기 메서드 + 동기 DB 세션 (10회 요청)",
        description: "전통적인 동기 방식의 DB 세션 처리",
        endpoints: Array(10).fill().map((_, index) => ({
            type: EndpointType.SYNC_WITH_SYNC_DB,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },
    {
        name: "기본 시나리오 2: 비동기 메서드 + 동기 DB 세션 (10회 요청)",
        description: "비동기 메서드에서 동기 DB 세션 사용 (안티패턴)",
        endpoints: Array(10).fill().map((_, index) => ({
            type: EndpointType.ASYNC_WITH_SYNC_DB,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },
    {
        name: "기본 시나리오 3: 비동기 메서드 + 비동기 DB 세션 (10회 요청)",
        description: "이상적인 비동기 DB 세션 처리",
        endpoints: Array(10).fill().map((_, index) => ({
            type: EndpointType.ASYNC_WITH_ASYNC_DB,
            timeout: [1, 2, 3, 2, 1, 3, 2, 1, 3, 2][index % 10]
        })),
        iterations: 1
    },

    // 새로운 심화 시나리오 추가
    {
        name: "심화 시나리오 1: 점진적 부하 - 동기 DB 세션",
        description: "동기 DB 세션의 부하 증가에 따른 성능 변화 측정 (10 -> 30 -> 50 -> 100 동시 요청)",
        endpoints: [
            ...Array(10).fill().map(() => ({ type: EndpointType.SYNC_WITH_SYNC_DB, timeout: 1 })),
            ...Array(30).fill().map(() => ({ type: EndpointType.SYNC_WITH_SYNC_DB, timeout: 1 })),
            ...Array(50).fill().map(() => ({ type: EndpointType.SYNC_WITH_SYNC_DB, timeout: 1 })),
            ...Array(100).fill().map(() => ({ type: EndpointType.SYNC_WITH_SYNC_DB, timeout: 1 }))
        ],
        iterations: 3
    },
    {
        name: "심화 시나리오 2: 점진적 부하 - 비동기 DB 세션",
        description: "비동기 DB 세션의 부하 증가에 따른 성능 변화 측정 (10 -> 30 -> 50 -> 100 동시 요청)",
        endpoints: [
            ...Array(10).fill().map(() => ({ type: EndpointType.ASYNC_WITH_ASYNC_DB, timeout: 1 })),
            ...Array(30).fill().map(() => ({ type: EndpointType.ASYNC_WITH_ASYNC_DB, timeout: 1 })),
            ...Array(50).fill().map(() => ({ type: EndpointType.ASYNC_WITH_ASYNC_DB, timeout: 1 })),
            ...Array(100).fill().map(() => ({ type: EndpointType.ASYNC_WITH_ASYNC_DB, timeout: 1 }))
        ],
        iterations: 3
    },
    {
        name: "심화 시나리오 3: 장기 연결 테스트",
        description: "동기/비동기 DB 세션의 장시간 연결 처리 능력 비교 (각 30개 요청, 5초)",
        endpoints: [
            ...Array(30).fill().map(() => ({ type: EndpointType.SYNC_WITH_SYNC_DB, timeout: 5 })),
            ...Array(30).fill().map(() => ({ type: EndpointType.ASYNC_WITH_ASYNC_DB, timeout: 5 }))
        ],
        iterations: 2
    },
    {
        name: "심화 시나리오 4: 혼합 부하 테스트",
        description: "동기/비동기 DB 세션의 다양한 처리 시간 요청 혼합 처리 능력 비교",
        endpoints: [
            ...Array(20).fill().map(() => ({ type: EndpointType.SYNC_WITH_SYNC_DB, timeout: 1 })),
            ...Array(15).fill().map(() => ({ type: EndpointType.SYNC_WITH_SYNC_DB, timeout: 3 })),
            ...Array(10).fill().map(() => ({ type: EndpointType.SYNC_WITH_SYNC_DB, timeout: 5 })),
            ...Array(20).fill().map(() => ({ type: EndpointType.ASYNC_WITH_ASYNC_DB, timeout: 1 })),
            ...Array(15).fill().map(() => ({ type: EndpointType.ASYNC_WITH_ASYNC_DB, timeout: 3 })),
            ...Array(10).fill().map(() => ({ type: EndpointType.ASYNC_WITH_ASYNC_DB, timeout: 5 }))
        ],
        iterations: 2
    },
    {
        name: "심화 시나리오 5: 극한 부하 테스트",
        description: "동기/비동기 DB 세션의 극한 상황 처리 능력 비교 (각 150개 동시 요청)",
        endpoints: [
            ...Array(150).fill().map(() => ({ type: EndpointType.SYNC_WITH_SYNC_DB, timeout: 1 })),
            ...Array(150).fill().map(() => ({ type: EndpointType.ASYNC_WITH_ASYNC_DB, timeout: 1 }))
        ],
        iterations: 1
    },
    // 실제 환경을 가정한 시나리오는 개선이 필요함: operation 타입에 대한 엔드포인트의 처리가 필요해보임(현재는 타임아웃(대기시간)을 통해 해당 작업의 부하를 가정하였음)
    {
        name: "실제 환경 시나리오 1-A: 동기 컨텍스트 복잡한 쿼리 부하 테스트",
        description: "동기 방식에서의 대용량 데이터 처리와 복잡한 쿼리 성능 측정",
        endpoints: [
            // 복잡한 조인 쿼리 (30개 요청)
            ...Array(30).fill().map(() => ({
                type: EndpointType.SYNC_WITH_SYNC_DB,
                operation: 'complex_join',
                timeout: 3
            })),
            // 대용량 데이터 처리 (20개 요청)
            ...Array(20).fill().map(() => ({
                type: EndpointType.SYNC_WITH_SYNC_DB,
                operation: 'large_dataset',
                timeout: 5
            }))
        ],
        iterations: 2
    },
    {
        name: "실제 환경 시나리오 1-B: 비동기 컨텍스트 복잡한 쿼리 부하 테스트",
        description: "비동기 방식에서의 대용량 데이터 처리와 복잡한 쿼리 성능 측정",
        endpoints: [
            // 복잡한 조인 쿼리 (30개 요청)
            ...Array(30).fill().map(() => ({
                type: EndpointType.ASYNC_WITH_ASYNC_DB,
                operation: 'complex_join',
                timeout: 3
            })),
            // 대용량 데이터 처리 (20개 요청)
            ...Array(20).fill().map(() => ({
                type: EndpointType.ASYNC_WITH_ASYNC_DB,
                operation: 'large_dataset',
                timeout: 5
            }))
        ],
        iterations: 2
    },
    {
        name: "실제 환경 시나리오 2-A: 동기 컨텍스트 혼합 워크로드 테스트",
        description: "동기 방식에서의 다양한 유형의 데이터베이스 작업 처리",
        endpoints: [
            // 읽기 작업 (30개)
            ...Array(30).fill().map(() => ({
                type: EndpointType.SYNC_WITH_SYNC_DB,
                operation: 'read',
                timeout: 1
            })),
            // 쓰기 작업 (20개)
            ...Array(20).fill().map(() => ({
                type: EndpointType.SYNC_WITH_SYNC_DB,
                operation: 'write',
                timeout: 2
            })),
            // 분석 작업 (10개)
            ...Array(10).fill().map(() => ({
                type: EndpointType.SYNC_WITH_SYNC_DB,
                operation: 'analysis',
                timeout: 5
            }))
        ],
        iterations: 2
    },
    {
        name: "실제 환경 시나리오 2-B: 비동기 컨텍스트 혼합 워크로드 테스트",
        description: "비동기 방식에서의 다양한 유형의 데이터베이스 작업 처리",
        endpoints: [
            // 읽기 작업 (30개)
            ...Array(30).fill().map(() => ({
                type: EndpointType.ASYNC_WITH_ASYNC_DB,
                operation: 'read',
                timeout: 1
            })),
            // 쓰기 작업 (20개)
            ...Array(20).fill().map(() => ({
                type: EndpointType.ASYNC_WITH_ASYNC_DB,
                operation: 'write',
                timeout: 2
            })),
            // 분석 작업 (10개)
            ...Array(10).fill().map(() => ({
                type: EndpointType.ASYNC_WITH_ASYNC_DB,
                operation: 'analysis',
                timeout: 5
            }))
        ],
        iterations: 2
    }
];

// 시나리오 실행 함수
export async function runScenario(scenarioConfig) {
    console.log('Starting scenario:', scenarioConfig.name);
    const startTime = performance.now();
    let allResults = [];
    let iterationTimes = [];
    let totalExpectedTime = 0;
    let currentProgress = 0;
    const totalRequests = scenarioConfig.endpoints.length * scenarioConfig.iterations;

    // DB 세션 메트릭스 배열 초기화
    let sessionMetrics = [];
    let poolMetrics = [];

    scenarioConfig.endpoints.forEach(endpoint => {
        totalExpectedTime += endpoint.timeout;
    });

    for (let i = 0; i < scenarioConfig.iterations; i++) {
        console.log(`Starting iteration ${i + 1} of ${scenarioConfig.iterations}`);
        const iterationStartTime = performance.now();

        try {
            const results = await Promise.all(
                scenarioConfig.endpoints.map(async (endpoint, endpointIndex) => {
                    const response = await callEndpoint(endpoint.type, endpoint.timeout);
                    // 진행 상황 업데이트
                    currentProgress = (i * scenarioConfig.endpoints.length) + endpointIndex + 1;
                    performanceMetrics.update(metrics => ({
                        ...metrics,
                        currentProgress,
                        totalRequests,
                        scenarioName: scenarioConfig.name
                    }));
                    return response;
                })
            );

            const iterationTime = performance.now() - iterationStartTime;
            iterationTimes.push(iterationTime);

            // DB 세션 정보 수집
            results.forEach(response => {
                // 수정된 데이터 접근 경로
                const responseData = response.data?.data;  // response.data.data로 접근
                console.log('Processing response data:', responseData);

                if (responseData?.session_info) {
                    sessionMetrics.push({
                        iterationNumber: i + 1,
                        timestamp: new Date().toISOString(),
                        total_connections: parseInt(responseData.session_info.total_connections) || 0,
                        active_connections: parseInt(responseData.session_info.active_connections) || 0,
                        threads_connected: parseInt(responseData.session_info.threads_connected) || 0,
                        threads_running: parseInt(responseData.session_info.threads_running) || 0,
                        max_used_connections: parseInt(responseData.session_info.max_used_connections) || 0
                    });
                }
                if (responseData?.pool_info) {
                    poolMetrics.push({
                        iterationNumber: i + 1,
                        timestamp: new Date().toISOString(),
                        max_connections: parseInt(responseData.pool_info.max_connections) || 0,
                        current_connections: parseInt(responseData.pool_info.current_connections) || 0,
                        available_connections: parseInt(responseData.pool_info.available_connections) || 0,
                        wait_timeout: parseInt(responseData.pool_info.wait_timeout) || 0
                    });
                }
            });

            allResults = [...allResults, ...results];

            console.log(`Iteration ${i + 1} completed`);
        } catch (error) {
            console.error(`Error in iteration ${i + 1}:`, error);
        }
    }

    // 메트릭스 로깅
    console.log('Session Metrics:', sessionMetrics);
    console.log('Pool Metrics:', poolMetrics);

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
        overhead: (totalTime / scenarioConfig.iterations) - theoreticalTimeMs,
        dbMetrics: {
            session: sessionMetrics.length > 0 ? {
                averageTotalConnections: sessionMetrics.reduce((acc, m) => acc + m.total_connections, 0) / sessionMetrics.length,
                averageActiveConnections: sessionMetrics.reduce((acc, m) => acc + m.active_connections, 0) / sessionMetrics.length,
                maxThreadsConnected: Math.max(...sessionMetrics.map(m => m.threads_connected)),
                maxThreadsRunning: Math.max(...sessionMetrics.map(m => m.threads_running)),
                maxUsedConnections: Math.max(...sessionMetrics.map(m => m.max_used_connections)),
                timeline: sessionMetrics
            } : null,
            pool: poolMetrics.length > 0 ? {
                maxConnections: poolMetrics[0]?.max_connections || 0,
                averageCurrentConnections: poolMetrics.reduce((acc, m) => acc + m.current_connections, 0) / poolMetrics.length,
                averageAvailableConnections: poolMetrics.reduce((acc, m) => acc + m.available_connections, 0) / poolMetrics.length,
                waitTimeout: poolMetrics[0]?.wait_timeout || 0,
                timeline: poolMetrics
            } : null
        }
    };

    console.log('Final Metrics:', metrics);  // 최종 메트릭스 로깅

    // 분석 메트릭스 추가
    return analyzeResults(metrics);
}

// 결과 분석을 위한 메트릭스 수정
function analyzeResults(metrics) {
    return {
        ...metrics,
        analysis: {
            // 연결 효율성 = (사용 중인 연결 수 / 최대 연결 수) × 100
            connectionEfficiency: ((metrics.dbMetrics.pool.maxConnections - metrics.dbMetrics.pool.averageAvailableConnections) / metrics.dbMetrics.pool.maxConnections),
            connectionUtilization: metrics.dbMetrics.session.averageActiveConnections / metrics.dbMetrics.session.averageTotalConnections,
            throughput: metrics.totalRequests / (metrics.totalTime / 1000),
            averageResponseTime: metrics.totalTime / metrics.totalRequests,
            concurrencyImpact: metrics.dbMetrics.session.maxThreadsRunning / metrics.dbMetrics.session.maxThreadsConnected,
            resourceEfficiency: {
                connectionReuse: metrics.totalRequests / metrics.dbMetrics.session.averageTotalConnections,
                connectionStability: 1 - (Math.abs(metrics.dbMetrics.session.maxThreadsConnected - metrics.dbMetrics.session.averageActiveConnections) / metrics.dbMetrics.session.maxThreadsConnected)
            }
        }
    };
} 