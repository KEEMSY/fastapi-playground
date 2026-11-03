import { writable } from 'svelte/store';

// 성능 측정을 위한 store
export const performanceMetrics = writable({
    totalTime: 0,
    endpointMetrics: []
});

// 스크롤 테스트 상태 관리를 위한 store 추가
export const scrollTestStore = writable({
    activeScrollTest: null,
    scrollTestCompleted: false
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
    },
    // 새로운 다중 쿼리 엔드포인트 추가
    SYNC_WITH_SYNC_DB_MULTIPLE: {
        path: 'sync-test-with-sync-db-session-multiple-queries',
        name: '동기 메서드 + 동기 DB 세션 (다중 쿼리)'
    },
    ASYNC_WITH_SYNC_DB_MULTIPLE: {
        path: 'async-test-with-sync-db-session-multiple-queries',
        name: '비동기 메서드 + 동기 DB 세션 (다중 쿼리)'
    },
    ASYNC_WITH_ASYNC_DB_MULTIPLE: {
        path: 'async-test-with-async-db-session-multiple-queries',
        name: '비동기 메서드 + 비동기 DB 세션 (다중 쿼리)'
    }
};

// 개별 API 호출 함수
async function callEndpoint(endpoint, timeout = null, queryCount = null) {
    const startTime = performance.now();
    const url = new URL(`http://localhost:7777/api/v1/standard/${endpoint.path}`);

    if (timeout !== null) {
        url.searchParams.append('timeout', timeout);
    }

    if (queryCount !== null) {
        url.searchParams.append('query_count', queryCount);
    }

    try {
        const response = await fetch(url);
        const data = await response.json();
        const endTime = performance.now();

        return {
            endpoint: endpoint.name,
            path: endpoint.path,
            timeout: timeout,
            queryCount: queryCount,
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
            queryCount: queryCount,
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
    },
    // 스크롤 테스트 시나리오 추가
    {
        name: "스크롤 테스트 - 동기 DB 세션",
        description: "스크롤 이벤트마다 동기 DB 세션 요청 실행",
        endpoints: [
            {
                type: EndpointType.SYNC_WITH_SYNC_DB,
                timeout: 1
            }
        ],
        iterations: 1,
        isScrollTest: true
    },
    {
        name: "스크롤 테스트 - 비동기 DB 세션",
        description: "스크롤 이벤트마다 비동기 DB 세션 요청 실행",
        endpoints: [
            {
                type: EndpointType.ASYNC_WITH_ASYNC_DB,
                timeout: 1
            }
        ],
        iterations: 1,
        isScrollTest: true
    }
];

// 스크롤 이벤트 핸들러 수정
async function handleScroll() {
    scrollTestStore.update(state => {
        if (!state.scrollTestCompleted && state.activeScrollTest) {
            console.log("테스트 실행 시작");
            state.scrollTestCompleted = true;
            runScenario(state.activeScrollTest);

            setTimeout(() => {
                scrollTestStore.set({
                    activeScrollTest: null,
                    scrollTestCompleted: false
                });
            }, 2000);
        }
        return state;
    });
}

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
    // 스크롤 테스트인 경우 분석 메트릭스를 생략
    if (metrics.scenarioConfig?.isScrollTest) {
        return {
            ...metrics,
            analysis: null
        };
    }

    // 일반 테스트인 경우 기존 분석 수행
    return {
        ...metrics,
        analysis: {
            connectionEfficiency: metrics.dbMetrics?.pool ?
                ((metrics.dbMetrics.pool.maxConnections - metrics.dbMetrics.pool.averageAvailableConnections) / metrics.dbMetrics.pool.maxConnections) : 0,
            connectionUtilization: metrics.dbMetrics?.session ?
                (metrics.dbMetrics.session.averageActiveConnections / metrics.dbMetrics.session.averageTotalConnections) : 0,
            throughput: metrics.totalRequests / (metrics.totalTime / 1000),
            averageResponseTime: metrics.totalTime / metrics.totalRequests,
            concurrencyImpact: metrics.dbMetrics?.session ?
                (metrics.dbMetrics.session.maxThreadsRunning / metrics.dbMetrics.session.maxThreadsConnected) : 0,
            resourceEfficiency: {
                connectionReuse: metrics.dbMetrics?.session ?
                    (metrics.totalRequests / metrics.dbMetrics.session.averageTotalConnections) : 0,
                connectionStability: metrics.dbMetrics?.session ?
                    (1 - Math.abs(metrics.dbMetrics.session.maxThreadsConnected - metrics.dbMetrics.session.averageActiveConnections) / metrics.dbMetrics.session.maxThreadsConnected) : 0
            }
        }
    };
}

// 부하 테스트를 위한 함수
export async function runLoadTest(config) {
    const {
        endpointType, // 테스트할 엔드포인트 타입
        numberOfUsers, // 동시 사용자 수
        queryCount, // 각 요청에서 실행할 쿼리 수
        iterations = 1 // 테스트 반복 횟수
    } = config;

    console.log(`Starting load test: ${numberOfUsers} users, ${queryCount} queries per request, ${iterations} iterations`);
    const startTime = performance.now();
    let allResults = [];
    let currentRequests = 0;

    // 전체 요청 수 계산
    const totalRequests = numberOfUsers * iterations;

    // 부하 테스트 중 진행 상황 업데이트를 위한 함수
    const updateProgress = (completed) => {
        performanceMetrics.update(metrics => ({
            ...metrics,
            currentProgress: completed,
            totalRequests,
            scenarioName: `부하 테스트: ${numberOfUsers}명 사용자, 요청당 ${queryCount}개 쿼리, ${iterations}회 반복`
        }));
    };

    // 각 반복마다 요청 실행
    for (let iter = 0; iter < iterations; iter++) {
        console.log(`Starting iteration ${iter + 1}/${iterations}`);

        // 모든 사용자의 요청을 동시에 실행
        const userPromises = Array(numberOfUsers).fill().map(async (_, index) => {
            const response = await callEndpoint(endpointType, null, queryCount);
            currentRequests++;

            // 진행 상황 업데이트
            if (currentRequests % Math.max(1, Math.floor(numberOfUsers / 10)) === 0) {
                updateProgress(currentRequests);
            }

            return response;
        });

        // 모든 사용자 요청 동시 실행
        const results = await Promise.all(userPromises);
        allResults = [...allResults, ...results];
    }

    const endTime = performance.now();
    const totalTime = endTime - startTime;

    // 결과 분석
    const metrics = {
        testName: `부하 테스트: ${numberOfUsers}명 사용자, 요청당 ${queryCount}개 쿼리, ${iterations}회 반복`,
        numberOfUsers,
        queryCount,
        totalRequests,
        totalTime,
        successRate: allResults.filter(r => r.success).length / allResults.length,
        averageResponseTime: allResults.reduce((acc, result) => acc + result.time, 0) / allResults.length,
        minResponseTime: Math.min(...allResults.map(r => r.time)),
        maxResponseTime: Math.max(...allResults.map(r => r.time)),
        iterations,
        // 쿼리 실행 정보 분석 추가
        queryExecutions: allResults.flatMap(r => r.data?.data?.query_executions || []),
        endpointResults: allResults
    };

    // 쿼리 실행 정보 분석
    if (metrics.queryExecutions.length > 0) {
        metrics.queryAnalysis = {
            totalQueries: metrics.queryExecutions.length,
            averageQueryDelay: metrics.queryExecutions.reduce((acc, q) => acc + q.delay_seconds, 0) / metrics.queryExecutions.length,
            averageQueryDuration: metrics.queryExecutions.reduce((acc, q) => acc + q.actual_duration_seconds, 0) / metrics.queryExecutions.length,
            maxQueryDuration: Math.max(...metrics.queryExecutions.map(q => q.actual_duration_seconds)),
            minQueryDuration: Math.min(...metrics.queryExecutions.map(q => q.actual_duration_seconds))
        };
    }

    console.log('Load Test Results:', metrics);
    return metrics;
}

// 새로운 다중 쿼리 부하 테스트 시나리오 추가
export const LoadTestScenarios = [
    {
        name: "다중 쿼리 부하 테스트 1: 동기 DB 세션 (10명 사용자)",
        description: "10명의 사용자가 각각 5개의 쿼리를 동시에 요청 (동기 DB 세션)",
        endpointType: EndpointType.SYNC_WITH_SYNC_DB_MULTIPLE,
        numberOfUsers: 10,
        queryCount: 5,
        iterations: 1
    },
    {
        name: "다중 쿼리 부하 테스트 2: 비동기 DB 세션 (10명 사용자)",
        description: "10명의 사용자가 각각 5개의 쿼리를 동시에 요청 (비동기 DB 세션)",
        endpointType: EndpointType.ASYNC_WITH_ASYNC_DB_MULTIPLE,
        numberOfUsers: 10,
        queryCount: 5,
        iterations: 1
    },
    {
        name: "다중 쿼리 부하 테스트 3: 동기 DB 세션 (30명 사용자)",
        description: "30명의 사용자가 각각 5개의 쿼리를 동시에 요청 (동기 DB 세션)",
        endpointType: EndpointType.SYNC_WITH_SYNC_DB_MULTIPLE,
        numberOfUsers: 30,
        queryCount: 5,
        iterations: 1
    },
    {
        name: "다중 쿼리 부하 테스트 4: 비동기 DB 세션 (30명 사용자)",
        description: "30명의 사용자가 각각 5개의 쿼리를 동시에 요청 (비동기 DB 세션)",
        endpointType: EndpointType.ASYNC_WITH_ASYNC_DB_MULTIPLE,
        numberOfUsers: 30,
        queryCount: 5,
        iterations: 1
    },
    {
        name: "다중 쿼리 부하 테스트 5: 동기 DB 세션 (50명 사용자)",
        description: "50명의 사용자가 각각 5개의 쿼리를 동시에 요청 (동기 DB 세션)",
        endpointType: EndpointType.SYNC_WITH_SYNC_DB_MULTIPLE,
        numberOfUsers: 50,
        queryCount: 5,
        iterations: 1
    },
    {
        name: "다중 쿼리 부하 테스트 6: 비동기 DB 세션 (50명 사용자)",
        description: "50명의 사용자가 각각 5개의 쿼리를 동시에 요청 (비동기 DB 세션)",
        endpointType: EndpointType.ASYNC_WITH_ASYNC_DB_MULTIPLE,
        numberOfUsers: 50,
        queryCount: 5,
        iterations: 1
    },
    {
        name: "다중 쿼리 부하 테스트 7: 동기 DB 세션 (70명 사용자)",
        description: "70명의 사용자가 각각 5개의 쿼리를 동시에 요청 (동기 DB 세션)",
        endpointType: EndpointType.SYNC_WITH_SYNC_DB_MULTIPLE,
        numberOfUsers: 70,
        queryCount: 5,
        iterations: 1
    },
    {
        name: "다중 쿼리 부하 테스트 8: 비동기 DB 세션 (70명 사용자)",
        description: "70명의 사용자가 각각 5개의 쿼리를 동시에 요청 (비동기 DB 세션)",
        endpointType: EndpointType.ASYNC_WITH_ASYNC_DB_MULTIPLE,
        numberOfUsers: 70,
        queryCount: 5,
        iterations: 1
    },
    {
        name: "다중 쿼리 부하 테스트 9: 동기 DB 세션 (100명 사용자)",
        description: "100명의 사용자가 각각 5개의 쿼리를 동시에 요청 (동기 DB 세션)",
        endpointType: EndpointType.SYNC_WITH_SYNC_DB_MULTIPLE,
        numberOfUsers: 100,
        queryCount: 5,
        iterations: 1
    },
    {
        name: "다중 쿼리 부하 테스트 10: 비동기 DB 세션 (100명 사용자)",
        description: "100명의 사용자가 각각 5개의 쿼리를 동시에 요청 (비동기 DB 세션)",
        endpointType: EndpointType.ASYNC_WITH_ASYNC_DB_MULTIPLE,
        numberOfUsers: 100,
        queryCount: 5,
        iterations: 1
    },
    {
        name: "비동기 vs 동기 DB 세션 비교 (비동기 메서드에서)",
        description: "비동기 메서드에서 동기/비동기 DB 세션의 성능 비교 (50명 사용자)",
        endpointType: EndpointType.ASYNC_WITH_SYNC_DB_MULTIPLE,
        numberOfUsers: 50,
        queryCount: 5,
        iterations: 1
    }
]; 