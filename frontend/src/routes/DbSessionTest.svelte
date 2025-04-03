<script>
    import { onMount } from "svelte";
    import {
        performanceMetrics,
        TestScenarios,
        runScenario,
        LoadTestScenarios,
        runLoadTest,
    } from "../lib/dbTest";
    import Chart from "chart.js/auto";
    import ScrollTestArea from "../components/ScrollTestArea.svelte";

    let charts = {};
    let results = []; // 여러 결과를 저장하기 위한 배열
    let selectedScenario = null;
    let showMetricsHelp = false;
    let activeTab = "basic";

    // 전체 시나리오 사용 (이전에는 3개만 사용)
    const dbScenarios = TestScenarios;
    // 부하 테스트 시나리오 추가
    const loadTestScenarios = LoadTestScenarios;

    let runningScenarios = new Set();
    let progress = {};

    let activeScrollTest = null;

    // performanceMetrics 구독 추가
    performanceMetrics.subscribe((metrics) => {
        if (metrics.scenarioName && metrics.currentProgress !== undefined) {
            progress[metrics.scenarioName] = {
                current: metrics.currentProgress,
                total: metrics.totalRequests,
                status: "실행 중...",
            };
            progress = { ...progress }; // Svelte 반응성 트리거
        }
    });

    function updateCombinedDbMetricsChart() {
        const canvasId = "combinedDbMetricsChart";

        if (charts[canvasId]) {
            charts[canvasId].destroy();
        }

        const ctx = document.getElementById(canvasId)?.getContext("2d");
        if (!ctx) return;

        const colors = [
            { main: "rgb(75, 192, 192)", light: "rgba(75, 192, 192, 0.2)" },
            { main: "rgb(255, 99, 132)", light: "rgba(255, 99, 132, 0.2)" },
            { main: "rgb(54, 162, 235)", light: "rgba(54, 162, 235, 0.2)" },
        ];

        const datasets = results.flatMap((result, idx) => [
            {
                label: `${result.scenarioName} - 총 연결 수`,
                data: result.dbMetrics.session.timeline.map(
                    (m) => m.total_connections,
                ),
                borderColor: colors[idx].main,
                backgroundColor: colors[idx].light,
                borderWidth: 2,
                tension: 0.4,
                pointRadius: 3,
                pointHoverRadius: 6,
                fill: false,
            },
            {
                label: `${result.scenarioName} - 활성 연결 수`,
                data: result.dbMetrics.session.timeline.map(
                    (m) => m.active_connections,
                ),
                borderColor: colors[idx].main,
                backgroundColor: colors[idx].light,
                borderWidth: 2,
                borderDash: [5, 5],
                tension: 0.4,
                pointRadius: 3,
                pointHoverRadius: 6,
                fill: false,
            },
            {
                label: `${result.scenarioName} - 가용 연결 수`,
                data: result.dbMetrics.pool.timeline.map(
                    (m) => m.available_connections,
                ),
                borderColor: colors[idx].main,
                backgroundColor: colors[idx].light,
                borderWidth: 2,
                borderDash: [2, 2],
                tension: 0.4,
                pointRadius: 3,
                pointHoverRadius: 6,
                fill: false,
            },
        ]);

        charts[canvasId] = new Chart(ctx, {
            type: "line",
            data: {
                labels:
                    results[0]?.dbMetrics.session.timeline.map(
                        (m) => m.iterationNumber,
                    ) || [],
                datasets: datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: "nearest",
                    axis: "x",
                    intersect: false,
                },
                plugins: {
                    title: {
                        display: true,
                        text: "시나리오 비교 - DB 연결 메트릭스",
                        font: {
                            size: 16,
                            weight: "bold",
                        },
                        padding: 20,
                    },
                    legend: {
                        position: "top",
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: {
                                size: 12,
                            },
                        },
                    },
                    tooltip: {
                        backgroundColor: "rgba(255, 255, 255, 0.9)",
                        titleColor: "#000",
                        titleFont: {
                            size: 14,
                            weight: "bold",
                        },
                        bodyColor: "#000",
                        bodyFont: {
                            size: 13,
                        },
                        borderColor: "#ddd",
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true,
                        callbacks: {
                            title: (tooltipItems) => {
                                return `반복 횟수: ${tooltipItems[0].label}`;
                            },
                            label: (context) => {
                                return ` ${context.dataset.label}: ${context.parsed.y}개`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: "반복 횟수",
                            font: {
                                size: 14,
                                weight: "bold",
                            },
                        },
                        grid: {
                            display: false,
                        },
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "연결 수",
                            font: {
                                size: 14,
                                weight: "bold",
                            },
                        },
                        grid: {
                            color: "rgba(0, 0, 0, 0.1)",
                        },
                    },
                },
            },
        });
    }

    async function executeAllScenarios() {
        results = [];
        for (const scenario of dbScenarios) {
            await executeScenario(scenario);
        }
    }

    async function executeScenario(scenario) {
        runningScenarios.add(scenario.name);
        progress[scenario.name] = {
            current: 0,
            total: scenario.endpoints.length * scenario.iterations,
            status: "준비 중...",
        };
        runningScenarios = runningScenarios; // Svelte 반응성 트리거
        progress = { ...progress }; // Svelte 반응성 트리거

        try {
            const result = await runScenario(scenario);
            results = results.filter(
                (r) => r.scenarioName !== result.scenarioName,
            );
            results = [...results, result];

            setTimeout(() => {
                updateCombinedDbMetricsChart();
            }, 0);
        } catch (error) {
            console.error("시나리오 실행 중 오류:", error);
            progress[scenario.name].status = "오류 발생";
            progress = { ...progress }; // Svelte 반응성 트리거
        } finally {
            runningScenarios.delete(scenario.name);
            runningScenarios = runningScenarios; // Svelte 반응성 트리거
        }
    }

    // 부하 테스트 실행 함수 추가
    async function executeLoadTest(scenario) {
        runningScenarios.add(scenario.name);
        progress[scenario.name] = {
            current: 0,
            total: scenario.numberOfUsers * scenario.iterations,
            status: "준비 중...",
        };
        runningScenarios = runningScenarios; // Svelte 반응성 트리거
        progress = { ...progress }; // Svelte 반응성 트리거

        try {
            const result = await runLoadTest(scenario);
            // 결과를 기존 결과 형식에 맞게 변환
            const formattedResult = {
                scenarioName: scenario.name,
                description: scenario.description,
                totalTime: result.totalTime,
                averageRequestTime: result.averageResponseTime,
                successRate: result.successRate,
                totalRequests: result.totalRequests,
                analysis: {
                    throughput:
                        result.totalRequests / (result.totalTime / 1000),
                    averageResponseTime: result.averageResponseTime,
                    // 부하 테스트는 DB 메트릭스가 없으므로 임의 값 사용
                    connectionEfficiency: 0,
                    connectionUtilization: 0,
                    concurrencyImpact: 0,
                    resourceEfficiency: {
                        connectionReuse: 0,
                        connectionStability: 0,
                    },
                },
                // 빈 DB 메트릭스 제공
                dbMetrics: {
                    session: {
                        averageTotalConnections: 0,
                        averageActiveConnections: 0,
                        maxThreadsConnected: 0,
                        maxThreadsRunning: 0,
                        maxUsedConnections: 0,
                        timeline: [],
                    },
                    pool: {
                        maxConnections: 0,
                        averageCurrentConnections: 0,
                        averageAvailableConnections: 0,
                        waitTimeout: 0,
                        timeline: [],
                    },
                },
            };

            results = results.filter(
                (r) => r.scenarioName !== formattedResult.scenarioName,
            );
            results = [...results, formattedResult];
        } catch (error) {
            console.error("부하 테스트 실행 중 오류:", error);
            progress[scenario.name].status = "오류 발생";
            progress = { ...progress }; // Svelte 반응성 트리거
        } finally {
            runningScenarios.delete(scenario.name);
            runningScenarios = runningScenarios; // Svelte 반응성 트리거
        }
    }

    function updateDbMetricsChart(metrics, scenarioName) {
        const canvasId = `dbMetricsChart-${scenarioName}`;

        if (charts[canvasId]) {
            charts[canvasId].destroy();
        }

        const ctx = document.getElementById(canvasId)?.getContext("2d");
        if (!ctx) return;

        charts[canvasId] = new Chart(ctx, {
            type: "line",
            data: {
                labels: metrics.dbMetrics.session.timeline.map(
                    (m) => m.iterationNumber,
                ),
                datasets: [
                    {
                        label: "총 연결 수",
                        data: metrics.dbMetrics.session.timeline.map(
                            (m) => m.total_connections,
                        ),
                        borderColor: "rgb(75, 192, 192)",
                        tension: 0.1,
                    },
                    {
                        label: "활성 연결 수",
                        data: metrics.dbMetrics.session.timeline.map(
                            (m) => m.active_connections,
                        ),
                        borderColor: "rgb(255, 99, 132)",
                        tension: 0.1,
                    },
                    {
                        label: "가용 연결 수",
                        data: metrics.dbMetrics.pool.timeline.map(
                            (m) => m.available_connections,
                        ),
                        borderColor: "rgb(54, 162, 235)",
                        tension: 0.1,
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: "DB 연결 메트릭스",
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                    },
                },
            },
        });
    }

    function showScenarioDetails(result) {
        console.log("Showing details for scenario:", result); // 디버깅용
        selectedScenario = result;
        setTimeout(() => {
            updateModalChart(result);
        }, 100); // 시간 약간 증가
    }

    function updateModalChart(result) {
        const canvasId = `dbMetricsChart-modal-${result.scenarioName}`;

        if (charts[canvasId]) {
            charts[canvasId].destroy();
        }

        const ctx = document.getElementById(canvasId)?.getContext("2d");
        if (!ctx) return;

        charts[canvasId] = new Chart(ctx, {
            type: "line",
            data: {
                labels: result.dbMetrics.session.timeline.map(
                    (m) => m.iterationNumber,
                ),
                datasets: [
                    {
                        label: "총 연결 수",
                        data: result.dbMetrics.session.timeline.map(
                            (m) => m.total_connections,
                        ),
                        borderColor: "rgb(75, 192, 192)",
                        backgroundColor: "rgba(75, 192, 192, 0.2)",
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 3,
                        pointHoverRadius: 6,
                    },
                    {
                        label: "활성 연결 수",
                        data: result.dbMetrics.session.timeline.map(
                            (m) => m.active_connections,
                        ),
                        borderColor: "rgb(255, 99, 132)",
                        backgroundColor: "rgba(255, 99, 132, 0.2)",
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 3,
                        pointHoverRadius: 6,
                    },
                    {
                        label: "가용 연결 수",
                        data: result.dbMetrics.pool.timeline.map(
                            (m) => m.available_connections,
                        ),
                        borderColor: "rgb(54, 162, 235)",
                        backgroundColor: "rgba(54, 162, 235, 0.2)",
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 3,
                        pointHoverRadius: 6,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: "index",
                    intersect: false,
                },
                plugins: {
                    title: {
                        display: true,
                        text: `${result.scenarioName} - DB 연결 메트릭스`,
                        font: {
                            size: 16,
                            weight: "bold",
                        },
                    },
                    tooltip: {
                        backgroundColor: "rgba(255, 255, 255, 0.9)",
                        titleColor: "#000",
                        bodyColor: "#000",
                        borderColor: "#ddd",
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true,
                        callbacks: {
                            title: (tooltipItems) => {
                                return `반복 횟수: ${tooltipItems[0].label}`;
                            },
                            label: (context) => {
                                return ` ${context.dataset.label}: ${context.parsed.y}개`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: "반복 횟수",
                        },
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "연결 수",
                        },
                    },
                },
            },
        });
    }

    function closeScenarioDetails() {
        selectedScenario = null;
    }

    // 결과 테이블에 새로운 메트릭스 추가
    function formatMetric(value) {
        return typeof value === "number" ? value.toFixed(2) : "0";
    }

    // 스크롤 테스트 시작 함수
    function startScrollTest(scenario) {
        console.log("Starting scroll test for:", scenario.name);
        activeScrollTest = scenario;
    }

    // 스크롤 이벤트 핸들러
    async function handleScroll() {
        if (activeScrollTest) {
            console.log("Executing scroll test");
            // 결과를 results 배열에 추가하지 않고 단순히 실행만 합니다
            await runScenario(activeScrollTest);

            // 테스트 완료 후 스크롤 영역 제거
            setTimeout(() => {
                activeScrollTest = null;
            }, 1000);
        }
    }
</script>

<div class="container mt-4">
    <!-- 테스트 개요 및 메트릭스 설명 섹션 -->
    <div class="overview-section mb-4">
        <div class="card">
            <div
                class="card-header d-flex justify-content-between align-items-center"
            >
                <h5 class="mb-0">DB 세션 테스트 개요</h5>
                <button
                    class="btn btn-sm btn-outline-primary"
                    on:click={() => (showMetricsHelp = !showMetricsHelp)}
                >
                    {showMetricsHelp ? "설명 닫기" : "설명 보기"}
                </button>
            </div>

            {#if showMetricsHelp}
                <div class="card-body">
                    <!-- 테스트 목적 설명 -->
                    <div class="test-purpose mb-4">
                        <h6>📋 테스트 목적</h6>
                        <ul>
                            <li>
                                동기/비동기 컨텍스트에서의 DB 세션 처리 성능
                                비교
                            </li>
                            <li>각 컨텍스트별 DB 연결 관리 효율성 측정</li>
                            <li>부하 상황에서의 시스템 동작 특성 분석</li>
                        </ul>
                    </div>

                    <!-- 성능 메트릭스 설명 -->
                    <div class="metrics-explanation">
                        <h6>📊 성능 메트릭스 상세 설명</h6>
                        <div class="metrics-grid">
                            <div class="metric-explanation-item">
                                <h6>처리량 (req/s)</h6>
                                <p>초당 처리된 요청 수를 나타냅니다.</p>
                                <ul>
                                    <li>
                                        계산 방법: 총 요청 수 ÷ 총 실행 시간(초)
                                    </li>
                                    <li>
                                        높을수록 더 많은 요청을 빠르게 처리함을
                                        의미
                                    </li>
                                    <li>
                                        비동기 처리가 일반적으로 더 높은
                                        처리량을 보임
                                    </li>
                                </ul>
                            </div>

                            <div class="metric-explanation-item">
                                <h6>평균 응답 시간 (ms)</h6>
                                <p>
                                    각 요청당 평균 처리 시간을 밀리초 단위로
                                    나타냅니다.
                                </p>
                                <ul>
                                    <li>
                                        계산 방법: 총 실행 시간(ms) ÷ 총 요청 수
                                    </li>
                                    <li>
                                        낮을수록 개별 요청이 더 빠르게 처리됨을
                                        의미
                                    </li>
                                    <li>
                                        부하가 증가하면 일반적으로 증가하는 경향
                                    </li>
                                </ul>
                            </div>

                            <div class="metric-explanation-item">
                                <h6>연결 효율성 (%)</h6>
                                <p>
                                    사용 가능한 DB 연결이 얼마나 효율적으로
                                    관리되는지 나타냅니다.
                                </p>
                                <ul>
                                    <li>
                                        계산 방법: (가용 연결 수 ÷ 최대 연결 수)
                                        × 100
                                    </li>
                                    <li>
                                        높을수록 연결 풀이 효율적으로 관리됨을
                                        의미
                                    </li>
                                    <li>
                                        적정 범위: 20-40% (예비 연결 유지 필요)
                                    </li>
                                </ul>
                            </div>

                            <div class="metric-explanation-item">
                                <h6>연결 활용도 (%)</h6>
                                <p>
                                    생성된 연결이 얼마나 활발하게 사용되는지
                                    나타냅니다.
                                </p>
                                <ul>
                                    <li>
                                        계산 방법: (활성 연결 수 ÷ 총 연결 수) ×
                                        100
                                    </li>
                                    <li>
                                        높을수록 연결이 적극적으로 사용됨을 의미
                                    </li>
                                    <li>
                                        이상적인 범위: 60-80% (여유 확보 필요)
                                    </li>
                                </ul>
                            </div>

                            <div class="metric-explanation-item">
                                <h6>동시성 영향도</h6>
                                <p>
                                    동시 요청이 시스템 성능에 미치는 영향을
                                    나타냅니다.
                                </p>
                                <ul>
                                    <li>
                                        계산 방법: 실행 중인 스레드 수 ÷ 연결된
                                        스레드 수
                                    </li>
                                    <li>
                                        1에 가까울수록 효율적인 동시성 처리를
                                        의미
                                    </li>
                                    <li>
                                        비동기 처리가 일반적으로 더 좋은 점수를
                                        보임
                                    </li>
                                </ul>
                            </div>
                        </div>

                        <div class="metrics-tips mt-4">
                            <h6>💡 성능 분석 가이드</h6>
                            <div class="tips-grid">
                                <div class="tip-item">
                                    <h7>기본 패턴</h7>
                                    <ul>
                                        <li>
                                            처리량과 응답 시간은 일반적으로
                                            반비례 관계
                                        </li>
                                        <li>
                                            연결 효율성과 활용도는 상황에 따라
                                            적절한 균형 필요
                                        </li>
                                    </ul>
                                </div>
                                <div class="tip-item">
                                    <h7>최적화 포인트</h7>
                                    <ul>
                                        <li>
                                            높은 처리량이 필요한 경우 비동기
                                            처리 권장
                                        </li>
                                        <li>
                                            연결 풀 크기는 예상 최대 동시 요청의
                                            1.5배 권장
                                        </li>
                                    </ul>
                                </div>
                                <div class="tip-item">
                                    <h7>주의 사항</h7>
                                    <ul>
                                        <li>
                                            연결 활용도가 90% 이상이면 병목 위험
                                        </li>
                                        <li>
                                            응답 시간 증가는 성능 저하의 조기
                                            경고 신호
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            {/if}
        </div>
    </div>

    <!-- 시나리오 목록 -->
    <div class="scenarios mb-4">
        <div class="card">
            <div class="card-header">
                <div
                    class="d-flex justify-content-between align-items-center mb-3"
                >
                    <h5 class="mb-0">DB 세션 테스트 시나리오</h5>
                    <button
                        class="btn btn-primary"
                        on:click={executeAllScenarios}
                    >
                        전체 시나리오 실행
                    </button>
                </div>

                <!-- 시나리오 타입 탭 - 부하 테스트 탭 추가 -->
                <ul class="nav nav-tabs">
                    <li class="nav-item">
                        <a
                            class="nav-link {activeTab === 'basic'
                                ? 'active'
                                : ''}"
                            href="#"
                            on:click|preventDefault={() =>
                                (activeTab = "basic")}
                        >
                            기본 시나리오
                        </a>
                    </li>
                    <li class="nav-item">
                        <a
                            class="nav-link {activeTab === 'advanced'
                                ? 'active'
                                : ''}"
                            href="#"
                            on:click|preventDefault={() =>
                                (activeTab = "advanced")}
                        >
                            심화 시나리오
                        </a>
                    </li>
                    <li class="nav-item">
                        <a
                            class="nav-link {activeTab === 'real'
                                ? 'active'
                                : ''}"
                            href="#"
                            on:click|preventDefault={() => (activeTab = "real")}
                        >
                            실제 시나리오
                        </a>
                    </li>
                    <!-- 부하 테스트 탭 추가 -->
                    <li class="nav-item">
                        <a
                            class="nav-link {activeTab === 'loadtest'
                                ? 'active'
                                : ''}"
                            href="#"
                            on:click|preventDefault={() =>
                                (activeTab = "loadtest")}
                        >
                            <span class="badge bg-danger me-1">NEW</span>
                            부하 테스트
                        </a>
                    </li>
                </ul>
            </div>

            <div class="card-body">
                <!-- 기본 시나리오 그리드 -->
                {#if activeTab === "basic"}
                    <div class="scenarios-grid">
                        {#each dbScenarios.filter((s) => !s.name.includes("심화") && !s.name.includes("실제")) as scenario}
                            <div class="scenario-card">
                                <div class="scenario-content">
                                    <h6>{scenario.name}</h6>
                                    <p>{scenario.description}</p>
                                    <div class="scenario-meta">
                                        <span class="badge bg-info">
                                            {scenario.endpoints.length}개 요청
                                        </span>
                                        <span class="badge bg-secondary">
                                            {scenario.iterations}회 반복
                                        </span>
                                    </div>

                                    <!-- 스크롤 테스트 영역 -->
                                    {#if scenario.isScrollTest}
                                        <div class="scroll-test-controls">
                                            <button
                                                class="btn btn-primary mb-2"
                                                on:click={() =>
                                                    startScrollTest(scenario)}
                                                disabled={runningScenarios.has(
                                                    scenario.name,
                                                )}
                                            >
                                                {#if runningScenarios.has(scenario.name)}
                                                    스크롤 테스트 중...
                                                {:else}
                                                    스크롤 테스트 시작
                                                {/if}
                                            </button>
                                        </div>

                                        {#if activeScrollTest === scenario}
                                            <div class="scroll-test-container">
                                                <div class="alert alert-info">
                                                    스크롤하여 테스트를
                                                    실행하세요. 최하단 도달 시
                                                    자동으로 최상단으로
                                                    이동합니다.
                                                </div>
                                                <ScrollTestArea
                                                    height="300px"
                                                    itemCount={50}
                                                    onScroll={() =>
                                                        executeScenario(
                                                            scenario,
                                                        )}
                                                />
                                            </div>
                                        {/if}
                                    {:else}
                                        <!-- 기존 시나리오 실행 버튼 -->
                                        <button
                                            class="btn btn-primary"
                                            on:click={() =>
                                                executeScenario(scenario)}
                                            disabled={runningScenarios.has(
                                                scenario.name,
                                            )}
                                        >
                                            실행
                                        </button>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                {:else if activeTab === "advanced"}
                    <div class="scenarios-grid">
                        {#each dbScenarios.filter( (s) => s.name.includes("심화"), ) as scenario}
                            <div class="scenario-card">
                                <div class="scenario-content">
                                    <h6>{scenario.name}</h6>
                                    <p>{scenario.description}</p>
                                    <div class="scenario-meta">
                                        <span class="badge bg-info">
                                            {scenario.endpoints.length}개 요청
                                        </span>
                                        <span class="badge bg-secondary">
                                            {scenario.iterations}회 반복
                                        </span>
                                    </div>

                                    <!-- 스크롤 테스트 영역 -->
                                    {#if scenario.isScrollTest}
                                        <div class="scroll-test-controls">
                                            <button
                                                class="btn btn-primary mb-2"
                                                on:click={() =>
                                                    startScrollTest(scenario)}
                                                disabled={runningScenarios.has(
                                                    scenario.name,
                                                )}
                                            >
                                                {#if runningScenarios.has(scenario.name)}
                                                    스크롤 테스트 중...
                                                {:else}
                                                    스크롤 테스트 시작
                                                {/if}
                                            </button>
                                        </div>

                                        {#if activeScrollTest === scenario}
                                            <div class="scroll-test-container">
                                                <div class="alert alert-info">
                                                    스크롤하여 테스트를
                                                    실행하세요. 최하단 도달 시
                                                    자동으로 최상단으로
                                                    이동합니다.
                                                </div>
                                                <ScrollTestArea
                                                    height="300px"
                                                    itemCount={50}
                                                    onScroll={() =>
                                                        executeScenario(
                                                            scenario,
                                                        )}
                                                />
                                            </div>
                                        {/if}
                                    {:else}
                                        <!-- 기존 시나리오 실행 버튼 -->
                                        <button
                                            class="btn btn-primary"
                                            on:click={() =>
                                                executeScenario(scenario)}
                                            disabled={runningScenarios.has(
                                                scenario.name,
                                            )}
                                        >
                                            실행
                                        </button>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                {:else if activeTab === "real"}
                    <div class="scenarios-grid">
                        {#each dbScenarios.filter( (s) => s.name.includes("실제"), ) as scenario}
                            <div class="scenario-card">
                                <div class="scenario-content">
                                    <h6>{scenario.name}</h6>
                                    <p>{scenario.description}</p>
                                    <div class="scenario-meta">
                                        <span class="badge bg-info">
                                            {scenario.endpoints.length}개 요청
                                        </span>
                                        <span class="badge bg-secondary">
                                            {scenario.iterations}회 반복
                                        </span>
                                    </div>

                                    <!-- 스크롤 테스트 영역 -->
                                    {#if scenario.isScrollTest}
                                        <div class="scroll-test-controls">
                                            <button
                                                class="btn btn-primary mb-2"
                                                on:click={() =>
                                                    startScrollTest(scenario)}
                                                disabled={runningScenarios.has(
                                                    scenario.name,
                                                )}
                                            >
                                                {#if runningScenarios.has(scenario.name)}
                                                    스크롤 테스트 중...
                                                {:else}
                                                    스크롤 테스트 시작
                                                {/if}
                                            </button>
                                        </div>

                                        {#if activeScrollTest === scenario}
                                            <div class="scroll-test-container">
                                                <div class="alert alert-info">
                                                    스크롤하여 테스트를
                                                    실행하세요. 최하단 도달 시
                                                    자동으로 최상단으로
                                                    이동합니다.
                                                </div>
                                                <ScrollTestArea
                                                    height="300px"
                                                    itemCount={50}
                                                    onScroll={() =>
                                                        executeScenario(
                                                            scenario,
                                                        )}
                                                />
                                            </div>
                                        {/if}
                                    {:else}
                                        <!-- 기존 시나리오 실행 버튼 -->
                                        <button
                                            class="btn btn-primary"
                                            on:click={() =>
                                                executeScenario(scenario)}
                                            disabled={runningScenarios.has(
                                                scenario.name,
                                            )}
                                        >
                                            실행
                                        </button>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                {:else if activeTab === "loadtest"}
                    <div class="row mb-3">
                        <div class="col-12">
                            <div class="alert alert-info" role="alert">
                                <i class="bi bi-info-circle-fill me-2"></i>
                                부하 테스트는 다수의 사용자가 동시에 여러 쿼리를
                                요청하는 상황을 시뮬레이션합니다. 사용자 수와 쿼리
                                수가 많을수록 서버의 부하가 증가합니다.
                            </div>
                        </div>
                    </div>
                    <div class="scenarios-grid">
                        {#each loadTestScenarios as scenario}
                            <div class="scenario-card">
                                <div class="scenario-content">
                                    <h6>{scenario.name}</h6>
                                    <p>{scenario.description}</p>
                                    <div class="scenario-meta">
                                        <span class="badge bg-danger">
                                            {scenario.numberOfUsers}명 사용자
                                        </span>
                                        <span class="badge bg-warning">
                                            요청당 {scenario.queryCount}개 쿼리
                                        </span>
                                        <span class="badge bg-secondary">
                                            총 {scenario.numberOfUsers *
                                                scenario.iterations}개 요청
                                        </span>
                                    </div>

                                    <!-- 실행 상태 표시 - 실행 중일 때만 표시되도록 조건 수정 -->
                                    {#if runningScenarios.has(scenario.name) && progress[scenario.name]}
                                        <div class="progress-container">
                                            <div
                                                class="progress"
                                                style="height: 10px;"
                                            >
                                                <div
                                                    class="progress-bar progress-bar-striped progress-bar-animated"
                                                    role="progressbar"
                                                    style="width: {(progress[
                                                        scenario.name
                                                    ].current /
                                                        progress[scenario.name]
                                                            .total) *
                                                        100}%"
                                                ></div>
                                            </div>
                                            <div class="progress-status">
                                                <small>
                                                    {progress[scenario.name]
                                                        .status}
                                                    ({progress[scenario.name]
                                                        .current}/{progress[
                                                        scenario.name
                                                    ].total})
                                                </small>
                                            </div>
                                        </div>
                                    {/if}
                                </div>
                                <div class="scenario-footer">
                                    <button
                                        class="btn btn-danger w-100"
                                        on:click={() =>
                                            executeLoadTest(scenario)}
                                        disabled={runningScenarios.has(
                                            scenario.name,
                                        )}
                                    >
                                        {#if runningScenarios.has(scenario.name)}
                                            <span
                                                class="spinner-border spinner-border-sm me-2"
                                                role="status"
                                            ></span>
                                            실행 중...
                                        {:else}
                                            부하 테스트 실행
                                        {/if}
                                    </button>
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>
    </div>

    <!-- 통합 결과 차트 -->
    {#if results.length > 0}
        <div class="card mb-4">
            <div class="card-header">
                <h5>시나리오 비교</h5>
            </div>
            <div class="card-body">
                <div
                    class="chart-container"
                    style="position: relative; height:60vh; width:100%"
                >
                    <canvas id="combinedDbMetricsChart"></canvas>
                </div>
            </div>
        </div>

        <!-- 통합 결과 테이블 -->
        <div class="card mb-4">
            <div class="card-header">
                <h5>시나리오 결과 비교</h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>시나리오</th>
                                <th>처리량 (req/s)</th>
                                <th>평균 응답 시간 (ms)</th>
                                <th>연결 효율성 (%)</th>
                                <th>연결 활용도 (%)</th>
                                <th>동시성 영향도</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each results as result}
                                <tr
                                    class="cursor-pointer"
                                    on:click={() => showScenarioDetails(result)}
                                >
                                    <td>{result.scenarioName}</td>
                                    <td
                                        >{formatMetric(
                                            result.analysis.throughput,
                                        )}</td
                                    >
                                    <td
                                        >{formatMetric(
                                            result.analysis.averageResponseTime,
                                        )}</td
                                    >
                                    <td
                                        >{formatMetric(
                                            result.analysis
                                                .connectionEfficiency * 100,
                                        )}%</td
                                    >
                                    <td
                                        >{formatMetric(
                                            result.analysis
                                                .connectionUtilization * 100,
                                        )}%</td
                                    >
                                    <td
                                        >{formatMetric(
                                            result.analysis.concurrencyImpact,
                                        )}</td
                                    >
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    {/if}

    <!-- 개별 결과 카드들 제거 -->
</div>

<!-- 시나리오 상세 정보 모달 -->
{#if selectedScenario}
    <div class="modal-backdrop" on:click={closeScenarioDetails}></div>
    <div class="modal-container">
        <div class="modal-content">
            <div class="modal-header">
                <h4>{selectedScenario.scenarioName} 상세 정보</h4>
                <button
                    type="button"
                    class="btn-close"
                    on:click={closeScenarioDetails}
                ></button>
            </div>
            <div class="modal-body">
                <div class="row">
                    <!-- 성능 메트릭스 카드 추가 -->
                    <div class="col-md-12 mb-4">
                        <div class="card">
                            <div class="card-header bg-light">
                                <h6 class="mb-0">성능 메트릭스</h6>
                            </div>
                            <div class="card-body">
                                <div class="metrics-grid">
                                    <div class="metric-item">
                                        <span class="label">처리량</span>
                                        <span class="value"
                                            >{formatMetric(
                                                selectedScenario.analysis
                                                    .throughput,
                                            )} req/s</span
                                        >
                                    </div>
                                    <div class="metric-item">
                                        <span class="label">평균 응답 시간</span
                                        >
                                        <span class="value"
                                            >{formatMetric(
                                                selectedScenario.analysis
                                                    .averageResponseTime,
                                            )} ms</span
                                        >
                                    </div>
                                    <div class="metric-item">
                                        <span class="label">연결 효율성</span>
                                        <span class="value"
                                            >{formatMetric(
                                                selectedScenario.analysis
                                                    .connectionEfficiency * 100,
                                            )}%</span
                                        >
                                    </div>
                                    <div class="metric-item">
                                        <span class="label">연결 재사용률</span>
                                        <span class="value"
                                            >{formatMetric(
                                                selectedScenario.analysis
                                                    .resourceEfficiency
                                                    .connectionReuse,
                                            )}</span
                                        >
                                    </div>
                                    <div class="metric-item">
                                        <span class="label">연결 안정성</span>
                                        <span class="value"
                                            >{formatMetric(
                                                selectedScenario.analysis
                                                    .resourceEfficiency
                                                    .connectionStability * 100,
                                            )}%</span
                                        >
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 세션 정보 카드 -->
                    <div class="col-md-6 mb-4">
                        <div class="card h-100">
                            <div class="card-header bg-light">
                                <h6 class="mb-0">세션 정보</h6>
                            </div>
                            <div class="card-body">
                                <div class="info-grid">
                                    <div class="info-item">
                                        <span class="label">총 연결 수</span>
                                        <span class="value"
                                            >{selectedScenario.dbMetrics.session.averageTotalConnections?.toFixed(
                                                0,
                                            ) || "0"}</span
                                        >
                                    </div>
                                    <div class="info-item">
                                        <span class="label">활성 연결 수</span>
                                        <span class="value"
                                            >{selectedScenario.dbMetrics.session.averageActiveConnections?.toFixed(
                                                0,
                                            ) || "0"}</span
                                        >
                                    </div>
                                    <div class="info-item">
                                        <span class="label">연결 스레드</span>
                                        <span class="value"
                                            >{selectedScenario.dbMetrics.session
                                                .maxThreadsConnected ||
                                                "0"}</span
                                        >
                                    </div>
                                    <div class="info-item">
                                        <span class="label">실행 스레드</span>
                                        <span class="value"
                                            >{selectedScenario.dbMetrics.session
                                                .maxThreadsRunning || "0"}</span
                                        >
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 풀 정보 카드 -->
                    <div class="col-md-6 mb-4">
                        <div class="card h-100">
                            <div class="card-header bg-light">
                                <h6 class="mb-0">커넥션 풀 정보</h6>
                            </div>
                            <div class="card-body">
                                <div class="info-grid">
                                    <div class="info-item">
                                        <span class="label">최대 연결 수</span>
                                        <span class="value"
                                            >{selectedScenario.dbMetrics.pool
                                                .maxConnections || "0"}</span
                                        >
                                    </div>
                                    <div class="info-item">
                                        <span class="label">현재 연결 수</span>
                                        <span class="value"
                                            >{selectedScenario.dbMetrics.pool.averageCurrentConnections?.toFixed(
                                                0,
                                            ) || "0"}</span
                                        >
                                    </div>
                                    <div class="info-item">
                                        <span class="label">가용 연결 수</span>
                                        <span class="value"
                                            >{selectedScenario.dbMetrics.pool.averageAvailableConnections?.toFixed(
                                                0,
                                            ) || "0"}</span
                                        >
                                    </div>
                                    <div class="info-item">
                                        <span class="label">대기 시간 제한</span
                                        >
                                        <span class="value"
                                            >{selectedScenario.dbMetrics.pool
                                                .waitTimeout || "0"}s</span
                                        >
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 모달 차트 -->
                <div class="modal-chart-container">
                    <canvas
                        id="dbMetricsChart-modal-{selectedScenario.scenarioName}"
                    ></canvas>
                </div>
            </div>
        </div>
    </div>
{/if}

<style>
    .chart-container {
        margin: 20px 0;
        padding: 10px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .test-type-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }

    .test-type-card h6 {
        color: #0d6efd;
        margin-bottom: 0.5rem;
    }

    .test-type-card ul {
        padding-left: 1.2rem;
        margin-bottom: 0;
    }

    .test-type-card li {
        margin-bottom: 0.2rem;
    }

    .badge {
        font-size: 0.9rem;
        padding: 0.5em 1em;
    }

    .table th {
        font-weight: 600;
    }

    .card {
        background: #fff;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }

    .card-header {
        background-color: #f8f9fa;
        border-bottom: 1px solid rgba(0, 0, 0, 0.125);
        padding: 1rem;
    }

    .card-header h5 {
        margin: 0;
        color: #495057;
    }

    .card-body {
        padding: 1.25rem;
    }

    .cursor-pointer {
        cursor: pointer;
    }

    .cursor-pointer:hover {
        background-color: #f8f9fa;
    }

    .modal-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: rgba(0, 0, 0, 0.5);
        z-index: 1050;
    }

    .modal-container {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 90%;
        max-width: 1200px;
        max-height: 90vh;
        overflow-y: auto;
        z-index: 1051;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }

    .modal-content {
        background: transparent;
        border: none;
        box-shadow: none;
    }

    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem;
        border-bottom: 1px solid #dee2e6;
    }

    .modal-body {
        padding: 1.5rem;
    }

    .modal-chart-container {
        height: 400px;
        margin-top: 2rem;
        padding: 1rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .info-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 0.5rem;
    }

    .info-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem;
        background-color: #f8f9fa;
        border-radius: 4px;
    }

    .info-item .label {
        color: #666;
        font-size: 0.9rem;
    }

    .info-item .value {
        font-weight: bold;
        color: #333;
    }

    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        margin-top: 1rem;
    }

    .metric-explanation-item {
        background: white;
        padding: 1.2rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        border: 1px solid #e9ecef;
    }

    .metric-explanation-item h6 {
        color: #0d6efd;
        margin-bottom: 0.8rem;
        font-weight: 600;
    }

    .metric-explanation-item p {
        color: #495057;
        margin-bottom: 0.8rem;
    }

    .metric-explanation-item ul {
        padding-left: 1.2rem;
        margin-bottom: 0;
    }

    .metric-explanation-item li {
        color: #6c757d;
        margin-bottom: 0.4rem;
    }

    .metrics-tips {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
    }

    .tips-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1rem;
        margin-top: 1rem;
    }

    .tip-item {
        background: white;
        padding: 1rem;
        border-radius: 6px;
        border-left: 3px solid #0d6efd;
    }

    .tip-item h7 {
        font-weight: 600;
        color: #0d6efd;
        display: block;
        margin-bottom: 0.5rem;
    }

    .test-purpose {
        background: #e8f4ff;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 2rem;
    }

    .test-purpose h6 {
        color: #0d6efd;
        margin-bottom: 0.8rem;
    }

    .test-purpose ul {
        margin-bottom: 0;
        padding-left: 1.2rem;
    }

    .test-purpose li {
        color: #495057;
        margin-bottom: 0.4rem;
    }

    .scenarios-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 1.5rem;
        padding: 1rem 0;
    }

    .scenario-card {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        height: 100%;
        transition:
            transform 0.2s,
            box-shadow 0.2s;
    }

    .scenario-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }

    .scenario-content {
        padding: 1.25rem;
        flex-grow: 1;
    }

    .scenario-content h6 {
        color: #0d6efd;
        margin-bottom: 0.75rem;
        font-weight: 600;
    }

    .scenario-content p {
        color: #6c757d;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }

    .scenario-meta {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }

    .scenario-footer {
        padding: 1rem;
        background: #f8f9fa;
        border-top: 1px solid #dee2e6;
        border-radius: 0 0 8px 8px;
    }

    .nav-tabs {
        border-bottom: 1px solid #dee2e6;
    }

    .nav-tabs .nav-link {
        color: #495057;
        border: 1px solid transparent;
        border-top-left-radius: 0.25rem;
        border-top-right-radius: 0.25rem;
        padding: 0.5rem 1rem;
    }

    .nav-tabs .nav-link.active {
        color: #0d6efd;
        background-color: #fff;
        border-color: #dee2e6 #dee2e6 #fff;
    }

    .badge {
        font-weight: 500;
        padding: 0.5em 0.75em;
    }

    .progress-container {
        margin-top: 1rem;
    }

    .progress {
        margin-bottom: 0.5rem;
        background-color: #e9ecef;
        border-radius: 0.25rem;
    }

    .progress-bar {
        background-color: #0d6efd;
        border-radius: 0.25rem;
    }

    .progress-status {
        display: flex;
        justify-content: space-between;
        color: #6c757d;
        font-size: 0.875rem;
    }

    .scenario-card {
        position: relative;
    }

    /* 실행 중인 카드 스타일 */
    .scenario-card.running {
        border-color: #0d6efd;
        box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.1);
    }

    /* 버튼 비활성화 스타일 */
    .btn:disabled {
        cursor: not-allowed;
        opacity: 0.8;
    }

    /* 스피너 스타일 */
    .spinner-border {
        width: 1rem;
        height: 1rem;
        border-width: 0.15em;
    }

    /* 부하 테스트 관련 스타일 추가 */
    .badge.bg-danger {
        background-color: #dc3545 !important;
    }

    .badge.bg-warning {
        background-color: #ffc107 !important;
        color: #212529;
    }

    .btn-danger {
        background-color: #dc3545;
        border-color: #dc3545;
    }

    .btn-danger:hover {
        background-color: #bb2d3b;
        border-color: #b02a37;
    }

    .alert-info {
        background-color: #cff4fc;
        border-color: #b6effb;
        color: #055160;
    }

    .scroll-test-container {
        margin: 1rem 0;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 4px;
        border: 1px solid #dee2e6;
    }

    .scroll-info {
        margin-bottom: 1rem;
        text-align: center;
        font-size: 0.9rem;
    }
</style>
