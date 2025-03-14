import { writable } from 'svelte/store';

// 성능 측정을 위한 store
export const productionMetrics = writable({
    totalTime: 0,
    endpointMetrics: [],
    currentProgress: 0,
    totalRequests: 0,
    scenarioName: ''
});

// API 엔드포인트 타입 정의
export const EndpointType = {
    // 기본 API 엔드포인트
    SYNC_API: {
        path: 'sync-test',
        name: '동기 API'
    },
    ASYNC_API: {
        path: 'async-test',
        name: '비동기 API'
    },
    SYNC_WAIT_API: {
        path: 'sync-test-with-wait',
        name: '동기 대기 API'
    },
    ASYNC_WAIT_API: {
        path: 'async-test-with-await',
        name: '비동기 대기 API'
    },
    // DB 관련 API 엔드포인트
    SYNC_WITH_SYNC_DB: {
        path: 'sync-test-with-sync-db-session',
        name: '동기 메서드 + 동기 DB 세션'
    },
    ASYNC_WITH_ASYNC_DB: {
        path: 'async-test-with-async-db-session',
        name: '비동기 메서드 + 비동기 DB 세션'
    },
    SYNC_WITH_SYNC_DB_MULTIPLE: {
        path: 'sync-test-with-sync-db-session-multiple-queries',
        name: '동기 메서드 + 동기 DB 세션 (다중 쿼리)'
    },
    ASYNC_WITH_ASYNC_DB_MULTIPLE: {
        path: 'async-test-with-async-db-session-multiple-queries',
        name: '비동기 메서드 + 비동기 DB 세션 (다중 쿼리)'
    }
};

// 페이지 요청 타입 정의
export const PageRequestType = {
    SIMPLE_PAGE: {
        name: '단순 페이지',
        description: '몇 개의 간단한 API 요청으로 구성된 페이지',
        endpoints: [
            { type: EndpointType.ASYNC_API, weight: 3 },
            { type: EndpointType.ASYNC_WAIT_API, timeout: 0.5, weight: 2 }
        ]
    },
    MEDIUM_PAGE: {
        name: '중간 복잡도 페이지',
        description: '여러 API 요청과 일부 DB 요청이 필요한 페이지',
        endpoints: [
            { type: EndpointType.ASYNC_API, weight: 2 },
            { type: EndpointType.ASYNC_WAIT_API, timeout: 1, weight: 3 },
            { type: EndpointType.ASYNC_WITH_ASYNC_DB, timeout: 1, weight: 2 }
        ]
    },
    COMPLEX_PAGE: {
        name: '복잡한 페이지',
        description: '많은 API 요청과 복잡한 DB 조회가 필요한 페이지',
        endpoints: [
            { type: EndpointType.ASYNC_API, weight: 1 },
            { type: EndpointType.ASYNC_WAIT_API, timeout: 1.5, weight: 2 },
            { type: EndpointType.ASYNC_WITH_ASYNC_DB, timeout: 2, weight: 3 },
            { type: EndpointType.ASYNC_WITH_ASYNC_DB_MULTIPLE, queryCount: 3, weight: 2 }
        ]
    },
    DASHBOARD_PAGE: {
        name: '대시보드 페이지',
        description: '다양한 데이터를 집계하고 표시하는 복잡한 페이지',
        endpoints: [
            { type: EndpointType.ASYNC_API, weight: 1 },
            { type: EndpointType.ASYNC_WAIT_API, timeout: 0.8, weight: 2 },
            { type: EndpointType.ASYNC_WITH_ASYNC_DB, timeout: 1.5, weight: 2 },
            { type: EndpointType.ASYNC_WITH_ASYNC_DB_MULTIPLE, queryCount: 5, weight: 3 }
        ]
    }
};

// API 요청 타입 정의
export const RequestType = {
    // 단순 읽기 작업 (빠른 응답)
    SIMPLE_READ: {
        path: 'sync-test-with-sync-db-session-multiple-queries',
        name: '단순 조회',
        queryCount: 2,
        avgResponseTime: 500, // 예상 응답 시간 (ms)
        complexity: 'low'
    },
    // 복잡한 읽기 작업 (중간 응답 시간)
    COMPLEX_READ: {
        path: 'sync-test-with-sync-db-session-multiple-queries',
        name: '복잡한 조회',
        queryCount: 5,
        avgResponseTime: 1200,
        complexity: 'medium'
    },
    // 쓰기 작업 (중간 응답 시간)
    WRITE_OPERATION: {
        path: 'sync-test-with-sync-db-session-multiple-queries',
        name: '데이터 저장',
        queryCount: 3,
        avgResponseTime: 800,
        complexity: 'medium'
    },
    // 복잡한 분석 작업 (느린 응답)
    ANALYTICS: {
        path: 'sync-test-with-sync-db-session-multiple-queries',
        name: '데이터 분석',
        queryCount: 8,
        avgResponseTime: 2500,
        complexity: 'high'
    },
    // 비동기 단순 조회
    ASYNC_SIMPLE_READ: {
        path: 'async-test-with-async-db-session-multiple-queries',
        name: '비동기 단순 조회',
        queryCount: 2,
        avgResponseTime: 500,
        complexity: 'low'
    },
    // 비동기 복잡 조회
    ASYNC_COMPLEX_READ: {
        path: 'async-test-with-async-db-session-multiple-queries',
        name: '비동기 복잡 조회',
        queryCount: 5,
        avgResponseTime: 1200,
        complexity: 'medium'
    },
    // 비동기 데이터 저장
    ASYNC_WRITE_OPERATION: {
        path: 'async-test-with-async-db-session-multiple-queries',
        name: '비동기 데이터 저장',
        queryCount: 3,
        avgResponseTime: 800,
        complexity: 'medium'
    },
    // 비동기 데이터 분석
    ASYNC_ANALYTICS: {
        path: 'async-test-with-async-db-session-multiple-queries',
        name: '비동기 데이터 분석',
        queryCount: 8,
        avgResponseTime: 2500,
        complexity: 'high'
    }
};

// 페이지 로드 패턴 정의
export const PageLoadPattern = {
    PRODUCT_LISTING: {
        name: '상품 목록 페이지',
        description: '상품 목록을 표시하는 페이지 (경량 조회)',
        requests: [
            { type: RequestType.SIMPLE_READ, weight: 0.7 },
            { type: RequestType.COMPLEX_READ, weight: 0.3 }
        ]
    },
    PRODUCT_DETAIL: {
        name: '상품 상세 페이지',
        description: '상품 상세 정보, 리뷰, 추천 상품을 표시하는 페이지 (중량 조회)',
        requests: [
            { type: RequestType.SIMPLE_READ, weight: 0.4 },
            { type: RequestType.COMPLEX_READ, weight: 0.4 },
            { type: RequestType.ANALYTICS, weight: 0.2 }
        ]
    },
    CHECKOUT: {
        name: '결제 페이지',
        description: '결제 처리 및 주문 확인을 위한 페이지 (쓰기 작업 포함)',
        requests: [
            { type: RequestType.SIMPLE_READ, weight: 0.3 },
            { type: RequestType.WRITE_OPERATION, weight: 0.6 },
            { type: RequestType.COMPLEX_READ, weight: 0.1 }
        ]
    },
    DASHBOARD: {
        name: '관리자 대시보드',
        description: '관리자를 위한 데이터 분석 및 모니터링 페이지 (복잡한 쿼리)',
        requests: [
            { type: RequestType.COMPLEX_READ, weight: 0.4 },
            { type: RequestType.ANALYTICS, weight: 0.6 }
        ]
    },
    PRODUCT_LISTING_ASYNC: {
        name: '비동기 상품 목록 페이지',
        description: '상품 목록을 표시하는 페이지 (비동기 경량 조회)',
        requests: [
            { type: RequestType.ASYNC_SIMPLE_READ, weight: 0.7 },
            { type: RequestType.ASYNC_COMPLEX_READ, weight: 0.3 }
        ]
    },
    PRODUCT_DETAIL_ASYNC: {
        name: '비동기 상품 상세 페이지',
        description: '상품 상세 정보, 리뷰, 추천 상품을 표시하는 페이지 (비동기 중량 조회)',
        requests: [
            { type: RequestType.ASYNC_SIMPLE_READ, weight: 0.4 },
            { type: RequestType.ASYNC_COMPLEX_READ, weight: 0.4 },
            { type: RequestType.ASYNC_ANALYTICS, weight: 0.2 }
        ]
    },
    CHECKOUT_ASYNC: {
        name: '비동기 결제 페이지',
        description: '결제 처리 및 주문 확인을 위한 페이지 (비동기 쓰기 작업 포함)',
        requests: [
            { type: RequestType.ASYNC_SIMPLE_READ, weight: 0.3 },
            { type: RequestType.ASYNC_WRITE_OPERATION, weight: 0.6 },
            { type: RequestType.ASYNC_COMPLEX_READ, weight: 0.1 }
        ]
    },
    DASHBOARD_ASYNC: {
        name: '비동기 관리자 대시보드',
        description: '관리자를 위한 데이터 분석 및 모니터링 페이지 (비동기 복잡 쿼리)',
        requests: [
            { type: RequestType.ASYNC_COMPLEX_READ, weight: 0.4 },
            { type: RequestType.ASYNC_ANALYTICS, weight: 0.6 }
        ]
    }
};

// 개별 API 호출 함수
async function callEndpoint(requestType) {
    const startTime = performance.now();
    const url = new URL(`http://localhost:7777/api/v1/standard/${requestType.path}`);

    // 쿼리 카운트 설정
    url.searchParams.append('query_count', requestType.queryCount);

    try {
        const response = await fetch(url);
        const data = await response.json();
        const endTime = performance.now();

        return {
            requestType: requestType.name,
            path: requestType.path,
            complexity: requestType.complexity,
            queryCount: requestType.queryCount,
            success: true,
            time: endTime - startTime,
            data
        };
    } catch (error) {
        const endTime = performance.now();
        return {
            requestType: requestType.name,
            path: requestType.path,
            complexity: requestType.complexity,
            queryCount: requestType.queryCount,
            success: false,
            time: endTime - startTime,
            error: error.message
        };
    }
}

// 페이지 로드 시뮬레이션 함수
async function simulatePageLoad(pagePattern) {
    // 페이지 패턴에 따라 요청 생성
    const requestsToMake = [];

    pagePattern.requests.forEach(req => {
        // 가중치를 기반으로 요청 횟수 결정 (최소 1개)
        const count = Math.max(1, Math.round(req.weight * 10));
        for (let i = 0; i < count; i++) {
            requestsToMake.push(req.type);
        }
    });

    // 모든 요청 병렬 실행
    const startTime = performance.now();
    const results = await Promise.all(requestsToMake.map(req => callEndpoint(req)));
    const endTime = performance.now();

    return {
        pageName: pagePattern.name,
        totalTime: endTime - startTime,
        requests: results,
        totalRequests: results.length,
        successRate: results.filter(r => r.success).length / results.length,
        averageResponseTime: results.reduce((acc, r) => acc + r.time, 0) / results.length
    };
}

// 사용자 액션 시뮬레이션 (여러 페이지 접근)
export const UserActions = {
    BROWSE_PRODUCTS: {
        name: '상품 검색 및 조회',
        description: '사용자가 상품을 검색하고 상세 페이지를 확인하는 행동',
        pages: [
            PageLoadPattern.PRODUCT_LISTING,
            PageLoadPattern.PRODUCT_DETAIL,
            PageLoadPattern.PRODUCT_DETAIL
        ]
    },
    PURCHASE_FLOW: {
        name: '구매 프로세스',
        description: '사용자가 상품을 검색, 조회하고 구매하는 전체 흐름',
        pages: [
            PageLoadPattern.PRODUCT_LISTING,
            PageLoadPattern.PRODUCT_DETAIL,
            PageLoadPattern.CHECKOUT
        ]
    },
    ADMIN_WORK: {
        name: '관리자 작업',
        description: '관리자가 대시보드를 확인하고 상품을 관리하는 흐름',
        pages: [
            PageLoadPattern.DASHBOARD,
            PageLoadPattern.PRODUCT_LISTING,
            PageLoadPattern.PRODUCT_DETAIL
        ]
    },
    BROWSE_PRODUCTS_ASYNC: {
        name: '비동기 상품 검색 및 조회',
        description: '사용자가 상품을 검색하고 상세 페이지를 확인하는 행동 (비동기)',
        pages: [
            PageLoadPattern.PRODUCT_LISTING_ASYNC,
            PageLoadPattern.PRODUCT_DETAIL_ASYNC,
            PageLoadPattern.PRODUCT_DETAIL_ASYNC
        ]
    },
    PURCHASE_FLOW_ASYNC: {
        name: '비동기 구매 프로세스',
        description: '사용자가 상품을 검색, 조회하고 구매하는 전체 흐름 (비동기)',
        pages: [
            PageLoadPattern.PRODUCT_LISTING_ASYNC,
            PageLoadPattern.PRODUCT_DETAIL_ASYNC,
            PageLoadPattern.CHECKOUT_ASYNC
        ]
    },
    ADMIN_WORK_ASYNC: {
        name: '비동기 관리자 작업',
        description: '관리자가 대시보드를 확인하고 상품을 관리하는 흐름 (비동기)',
        pages: [
            PageLoadPattern.DASHBOARD_ASYNC,
            PageLoadPattern.PRODUCT_LISTING_ASYNC,
            PageLoadPattern.PRODUCT_DETAIL_ASYNC
        ]
    }
};

// 사용자 행동 시뮬레이션
async function simulateUserAction(actionPattern) {
    const results = [];

    // 순차적으로 페이지 로드 (실제 사용자의 탐색 흐름 시뮬레이션)
    for (const page of actionPattern.pages) {
        const pageResult = await simulatePageLoad(page);
        results.push(pageResult);
    }

    // 전체 결과 종합
    const totalTime = results.reduce((acc, r) => acc + r.totalTime, 0);
    const allRequests = results.flatMap(r =>
        r.requests
    );

    return {
        actionName: actionPattern.name,
        pages: results,
        totalTime,
        totalRequests: allRequests.length,
        successRate: allRequests.filter(r => r.success).length / allRequests.length,
        averageResponseTime: allRequests.reduce((acc, r) => acc + r.time, 0) / allRequests.length
    };
}

// 프로덕션 테스트 시나리오 정의
export const ProductionTestScenarios = [
    {
        name: "낮은 트래픽 시나리오: 10명 동시 사용자",
        description: "오프 피크 시간대를 가정한 낮은 트래픽 상황",
        concurrentUsers: 10,
        userActions: [
            { action: UserActions.BROWSE_PRODUCTS, weight: 0.6 },
            { action: UserActions.PURCHASE_FLOW, weight: 0.4 }
        ]
    },
    {
        name: "중간 트래픽 시나리오: 50명 동시 사용자",
        description: "일반적인 영업 시간대를 가정한 중간 트래픽 상황",
        concurrentUsers: 50,
        userActions: [
            { action: UserActions.BROWSE_PRODUCTS, weight: 0.5 },
            { action: UserActions.PURCHASE_FLOW, weight: 0.4 },
            { action: UserActions.ADMIN_WORK, weight: 0.1 }
        ]
    },
    {
        name: "높은 트래픽 시나리오: 100명 동시 사용자",
        description: "프로모션이나 세일 기간을 가정한 높은 트래픽 상황",
        concurrentUsers: 100,
        userActions: [
            { action: UserActions.BROWSE_PRODUCTS, weight: 0.7 },
            { action: UserActions.PURCHASE_FLOW, weight: 0.3 }
        ]
    },
    {
        name: "피크 트래픽 시나리오: 200명 동시 사용자",
        description: "블랙 프라이데이와 같은 극심한 트래픽 상황",
        concurrentUsers: 200,
        userActions: [
            { action: UserActions.BROWSE_PRODUCTS, weight: 0.6 },
            { action: UserActions.PURCHASE_FLOW, weight: 0.4 }
        ]
    },
    {
        name: "동기 vs 비동기 비교: 낮은 트래픽 (50명)",
        description: "동기 및 비동기 처리 방식의 성능 비교 (낮은 트래픽)",
        concurrentUsers: 50,
        userActions: [
            { action: UserActions.BROWSE_PRODUCTS, weight: 0.5 },
            { action: UserActions.BROWSE_PRODUCTS_ASYNC, weight: 0.5 }
        ]
    },
    {
        name: "동기 vs 비동기 비교: 높은 트래픽 (100명)",
        description: "동기 및 비동기 처리 방식의 성능 비교 (높은 트래픽)",
        concurrentUsers: 100,
        userActions: [
            { action: UserActions.PURCHASE_FLOW, weight: 0.5 },
            { action: UserActions.PURCHASE_FLOW_ASYNC, weight: 0.5 }
        ]
    }
];

// 시나리오 별 사용자 정의 설정 (사용자 지정 테스트용)
export const CustomTestConfigurations = {
    userCount: [10, 20, 50, 100, 200, 500],
    actionTypes: Object.values(UserActions),
    trafficPatterns: [
        { name: "균일 분포", distribution: "uniform" },
        { name: "점진적 증가", distribution: "gradual" },
        { name: "버스트 트래픽", distribution: "burst" }
    ]
};

// 테스트 실행 함수
export async function runProductionTest(scenario) {
    console.log(`Starting production test: ${scenario.name}`);
    const startTime = performance.now();

    // 시나리오에 따른 동시 사용자 수
    const concurrentUsers = scenario.concurrentUsers;

    // 사용자 행동 가중치에 따라 사용자별 행동 할당
    const userActions = [];
    scenario.userActions.forEach(actionConfig => {
        const count = Math.round(actionConfig.weight * concurrentUsers);
        for (let i = 0; i < count; i++) {
            userActions.push(actionConfig.action);
        }
    });

    // 가중치로 인한 사용자 수 조정 후 실제 사용자 수 계산
    const actualUserCount = userActions.length;

    // 진행 상황 추적용 변수
    let completedUsers = 0;

    // 모든 사용자 행동 병렬 시뮬레이션
    const userPromises = userActions.map(async (action, userIndex) => {
        const result = await simulateUserAction(action);

        // 진행 상황 업데이트
        completedUsers++;
        productionMetrics.update(metrics => ({
            ...metrics,
            currentProgress: completedUsers,
            totalRequests: actualUserCount,
            scenarioName: scenario.name
        }));

        return {
            userIndex,
            ...result
        };
    });

    // 모든 사용자 시뮬레이션 완료 대기
    const results = await Promise.all(userPromises);

    const endTime = performance.now();
    const totalTime = endTime - startTime;

    // 모든 요청을 배열로 변환
    const allRequests = results.flatMap(r =>
        r.pages.flatMap(p => p.requests)
    );

    // 페이지별 평균 로드 시간 계산
    const pageLoadTimes = {};
    results.forEach(userResult => {
        userResult.pages.forEach(page => {
            if (!pageLoadTimes[page.pageName]) {
                pageLoadTimes[page.pageName] = [];
            }
            pageLoadTimes[page.pageName].push(page.totalTime);
        });
    });

    const averagePageLoadTimes = {};
    Object.entries(pageLoadTimes).forEach(([pageName, times]) => {
        averagePageLoadTimes[pageName] = times.reduce((acc, t) => acc + t, 0) / times.length;
    });

    // 복잡도별 응답 시간 분석
    const complexityTimes = {
        low: [],
        medium: [],
        high: []
    };

    allRequests.forEach(req => {
        if (req.complexity && complexityTimes[req.complexity]) {
            complexityTimes[req.complexity].push(req.time);
        }
    });

    const averageComplexityTimes = {};
    Object.entries(complexityTimes).forEach(([complexity, times]) => {
        if (times.length > 0) {
            averageComplexityTimes[complexity] = times.reduce((acc, t) => acc + t, 0) / times.length;
        }
    });

    // 성공/실패 통계
    const successfulRequests = allRequests.filter(r => r.success);
    const failedRequests = allRequests.filter(r => !r.success);

    // 응답 시간 분포 분석
    const responseTimes = allRequests.map(r => r.time).sort((a, b) => a - b);
    const p50 = responseTimes[Math.floor(responseTimes.length * 0.5)];
    const p90 = responseTimes[Math.floor(responseTimes.length * 0.9)];
    const p95 = responseTimes[Math.floor(responseTimes.length * 0.95)];
    const p99 = responseTimes[Math.floor(responseTimes.length * 0.99)];

    return {
        scenarioName: scenario.name,
        description: scenario.description,
        concurrentUsers: actualUserCount,
        totalTime,
        totalRequests: allRequests.length,
        successRate: successfulRequests.length / allRequests.length,
        failureRate: failedRequests.length / allRequests.length,
        averageResponseTime: allRequests.reduce((acc, r) => acc + r.time, 0) / allRequests.length,
        maxResponseTime: Math.max(...allRequests.map(r => r.time)),
        minResponseTime: Math.min(...allRequests.map(r => r.time)),
        userActions: results,
        pageAnalysis: {
            averagePageLoadTimes,
            pageTimeline: Object.entries(pageLoadTimes).map(([name, times]) => ({
                name,
                times,
                average: times.reduce((acc, t) => acc + t, 0) / times.length,
                min: Math.min(...times),
                max: Math.max(...times)
            }))
        },
        complexityAnalysis: {
            averageComplexityTimes,
            distribution: {
                low: complexityTimes.low.length / allRequests.length,
                medium: complexityTimes.medium.length / allRequests.length,
                high: complexityTimes.high.length / allRequests.length
            }
        },
        responseTimeDistribution: {
            p50,
            p90,
            p95,
            p99,
            mean: allRequests.reduce((acc, r) => acc + r.time, 0) / allRequests.length,
            stdDev: Math.sqrt(
                allRequests.map(r => r.time)
                    .reduce((acc, t) => acc + Math.pow(t - (allRequests.reduce((a, r) => a + r.time, 0) / allRequests.length), 2), 0)
                / allRequests.length
            )
        },
        throughput: allRequests.length / (totalTime / 1000), // 초당 요청 수
        errorAnalysis: failedRequests.length > 0 ? {
            count: failedRequests.length,
            rate: failedRequests.length / allRequests.length,
            errorTypes: failedRequests.reduce((acc, req) => {
                const errorType = req.error || 'Unknown';
                acc[errorType] = (acc[errorType] || 0) + 1;
                return acc;
            }, {})
        } : null
    };
}

// 사용자 정의 테스트 실행 함수
export async function runCustomProductionTest(config) {
    const {
        userCount,
        actions,
        trafficPattern
    } = config;

    console.log(`Starting custom production test: ${userCount} users, ${actions.length} action types`);

    // 시나리오 구성
    const customScenario = {
        name: `사용자 정의 테스트: ${userCount}명, ${trafficPattern.name} 트래픽 패턴`,
        description: `사용자 정의 테스트 설정으로 실행`,
        concurrentUsers: userCount,
        userActions: actions.map(action => ({
            action,
            // 각 액션에 균등한 가중치 할당
            weight: 1 / actions.length
        }))
    };

    // 트래픽 패턴에 따른 처리 로직 추가
    if (trafficPattern.distribution === "gradual") {
        // 점진적으로 사용자를 늘리는 로직 구현
        return runGradualTrafficTest(customScenario);
    } else if (trafficPattern.distribution === "burst") {
        // 버스트 트래픽 패턴 구현
        return runBurstTrafficTest(customScenario);
    } else {
        // 기본 균일 분포 테스트
        return runProductionTest(customScenario);
    }
}

// 점진적 트래픽 증가 테스트
async function runGradualTrafficTest(scenario) {
    const totalUsers = scenario.concurrentUsers;
    const batches = 4; // 4단계로 나누어 점진적 증가
    const results = [];

    for (let i = 1; i <= batches; i++) {
        // 각 단계별 사용자 수 계산
        const batchUsers = Math.ceil((totalUsers * i) / batches);

        // 현재 단계 시나리오 생성
        const batchScenario = {
            ...scenario,
            name: `${scenario.name} - 단계 ${i}/${batches} (${batchUsers}명)`,
            concurrentUsers: batchUsers
        };

        // 현재 단계 테스트 실행
        const batchResult = await runProductionTest(batchScenario);
        results.push(batchResult);
    }

    // 종합 결과 계산
    const allRequests = results.flatMap(r =>
        r.userActions.flatMap(user =>
            user.pages.flatMap(page => page.requests)
        )
    );

    return {
        scenarioName: `점진적 증가 테스트: ${scenario.name}`,
        description: `사용자 수를 ${batches}단계로 점진적으로 증가시키며 테스트`,
        batches: results,
        totalUsers,
        totalRequests: allRequests.length,
        averageResponseTime: allRequests.reduce((acc, r) => acc + r.time, 0) / allRequests.length,
        successRate: allRequests.filter(r => r.success).length / allRequests.length,
        // 단계별 응답 시간 비교
        stageComparison: results.map(r => ({
            name: r.scenarioName,
            userCount: r.concurrentUsers,
            averageResponseTime: r.averageResponseTime,
            p95: r.responseTimeDistribution.p95,
            throughput: r.throughput
        }))
    };
}

// 버스트 트래픽 패턴 테스트
async function runBurstTrafficTest(scenario) {
    const totalUsers = scenario.concurrentUsers;

    // 버스트 패턴: 25%-100%-50% 사용자 수 분포
    const burstPattern = [
        { name: "초기 부하", percentage: 0.25 },
        { name: "최대 부하", percentage: 1.0 },
        { name: "감소 부하", percentage: 0.5 }
    ];

    const results = [];

    for (const phase of burstPattern) {
        // 각 단계별 사용자 수 계산
        const phaseUsers = Math.ceil(totalUsers * phase.percentage);

        // 현재 단계 시나리오 생성
        const phaseScenario = {
            ...scenario,
            name: `${scenario.name} - ${phase.name} (${phaseUsers}명)`,
            concurrentUsers: phaseUsers
        };

        // 현재 단계 테스트 실행
        const phaseResult = await runProductionTest(phaseScenario);
        results.push(phaseResult);
    }

    // 종합 결과 계산
    const allRequests = results.flatMap(r =>
        r.userActions.flatMap(user =>
            user.pages.flatMap(page => page.requests)
        )
    );

    return {
        scenarioName: `버스트 트래픽 테스트: ${scenario.name}`,
        description: `트래픽 버스트 패턴을 시뮬레이션하는 테스트`,
        phases: results,
        totalUsers,
        totalRequests: allRequests.length,
        averageResponseTime: allRequests.reduce((acc, r) => acc + r.time, 0) / allRequests.length,
        successRate: allRequests.filter(r => r.success).length / allRequests.length,
        // 단계별 부하 비교
        phaseComparison: results.map(r => ({
            name: r.scenarioName,
            userCount: r.concurrentUsers,
            averageResponseTime: r.averageResponseTime,
            p95: r.responseTimeDistribution.p95,
            throughput: r.throughput,
            successRate: r.successRate
        }))
    };
} 