<script>
    import { onDestroy } from "svelte";

    export let onScroll;
    export let height = "500px";
    export let itemCount = 100;
    export let maxRequests = 1000;
    export let autoTest = false;

    let scrollContainer;
    let requestCount = 0;
    let responseCount = 0;
    let startTime = null;
    let lastRequestTime = null;
    let endTime = null;
    let isTestCompleted = false;
    let currentTime = performance.now();
    let openScenarios = new Set(); // 열린 시나리오들을 추적하기 위한 Set

    // 실시간 시간 업데이트를 위한 타이머 설정
    let timer = setInterval(() => {
        if (startTime && !isTestCompleted) {
            currentTime = performance.now();
        }
    }, 100);

    // 컴포넌트 제거 시 타이머 정리
    onDestroy(() => {
        clearInterval(timer);
    });

    const items = Array(itemCount)
        .fill()
        .map((_, i) => `아이템 ${i + 1}`);

    async function handleScroll() {
        if (!isTestCompleted && requestCount < maxRequests) {
            if (requestCount === 0) {
                startTime = performance.now();
                console.log("테스트 시작:", new Date().toISOString());
            }

            requestCount++;
            lastRequestTime = performance.now();

            try {
                await onScroll(requestCount);
                responseCount++;

                if (responseCount >= maxRequests) {
                    endTime = performance.now();
                    isTestCompleted = true;
                    clearInterval(timer);

                    console.log(`
                        테스트 완료:
                        - 총 요청 수: ${requestCount}
                        - 총 응답 수: ${responseCount}
                        - 시작 시간: ${new Date(startTime).toISOString()}
                        - 마지막 요청 시간: ${new Date(lastRequestTime).toISOString()}
                        - 마지막 응답 시간: ${new Date(endTime).toISOString()}
                        - 요청 전송 완료 시간: ${((lastRequestTime - startTime) / 1000).toFixed(2)}초
                        - 전체 완료 시간: ${((endTime - startTime) / 1000).toFixed(2)}초
                        - 응답 처리 시간: ${((endTime - lastRequestTime) / 1000).toFixed(2)}초
                    `);

                    dispatchEvent(
                        new CustomEvent("testComplete", {
                            detail: {
                                requestCount,
                                responseCount,
                                requestsCompletionTime:
                                    (lastRequestTime - startTime) / 1000,
                                totalCompletionTime:
                                    (endTime - startTime) / 1000,
                                startTime,
                                lastRequestTime,
                                endTime,
                            },
                        }),
                    );
                }
            } catch (error) {
                console.error("요청 처리 중 오류:", error);
            }

            if (scrollContainer) {
                const { scrollTop, scrollHeight, clientHeight } =
                    scrollContainer;
                if (
                    scrollTop + clientHeight >= scrollHeight &&
                    !isTestCompleted
                ) {
                    scrollContainer.scrollTop = 0;
                }
            }
        }
    }

    // 자동 테스트를 위한 함수 수정
    async function startAutoTest() {
        if (autoTest && !isTestCompleted) {
            startTime = performance.now();
            console.log("자동 테스트 시작:", new Date().toISOString());

            // 모든 요청을 한번에 생성
            const requests = Array.from(
                { length: maxRequests },
                (_, i) => i + 1,
            );
            requestCount = maxRequests;
            lastRequestTime = performance.now();

            try {
                // 모든 요청을 동시에 실행
                await Promise.all(
                    requests.map(async (reqNum) => {
                        try {
                            await onScroll(reqNum);
                            responseCount++;

                            if (responseCount >= maxRequests) {
                                endTime = performance.now();
                                isTestCompleted = true;
                                clearInterval(timer);

                                console.log(`
                                    자동 테스트 완료:
                                    - 총 요청 수: ${requestCount}
                                    - 총 응답 수: ${responseCount}
                                    - 시작 시간: ${new Date(startTime).toISOString()}
                                    - 마지막 요청 시간: ${new Date(lastRequestTime).toISOString()}
                                    - 마지막 응답 시간: ${new Date(endTime).toISOString()}
                                    - 요청 전송 완료 시간: ${((lastRequestTime - startTime) / 1000).toFixed(2)}초
                                    - 전체 완료 시간: ${((endTime - startTime) / 1000).toFixed(2)}초
                                    - 응답 처리 시간: ${((endTime - lastRequestTime) / 1000).toFixed(2)}초
                                    - 초당 처리된 요청 수: ${(maxRequests / ((endTime - startTime) / 1000)).toFixed(2)}개
                                `);

                                dispatchEvent(
                                    new CustomEvent("testComplete", {
                                        detail: {
                                            requestCount,
                                            responseCount,
                                            requestsCompletionTime:
                                                (lastRequestTime - startTime) /
                                                1000,
                                            totalCompletionTime:
                                                (endTime - startTime) / 1000,
                                            startTime,
                                            lastRequestTime,
                                            endTime,
                                            requestsPerSecond:
                                                maxRequests /
                                                ((endTime - startTime) / 1000),
                                        },
                                    }),
                                );
                            }
                        } catch (error) {
                            console.error(
                                `요청 ${reqNum} 처리 중 오류:`,
                                error,
                            );
                        }
                    }),
                );
            } catch (error) {
                console.error("전체 테스트 처리 중 오류:", error);
            }
        }
    }

    // autoTest prop이 변경될 때 자동 테스트 시작
    $: if (autoTest) {
        startAutoTest();
    }

    $: elapsedTime = startTime ? (currentTime - startTime) / 1000 : 0;
    $: requestTime = lastRequestTime ? (lastRequestTime - startTime) / 1000 : 0;
    $: responseTime = lastRequestTime
        ? (currentTime - lastRequestTime) / 1000
        : 0;

    function toggleScenario(scenarioName) {
        if (openScenarios.has(scenarioName)) {
            openScenarios.delete(scenarioName);
        } else {
            openScenarios.add(scenarioName);
        }
        openScenarios = openScenarios; // Svelte 반응성 트리거
    }
</script>

<div class="scroll-test-info">
    {#if !isTestCompleted}
        <div class="progress-info">
            <div class="metric-row">
                <span class="metric-label">요청 진행률:</span>
                <span class="metric-value">
                    {((requestCount / maxRequests) * 100).toFixed(1)}% ({requestCount}/{maxRequests})
                </span>
            </div>
            <div class="metric-row">
                <span class="metric-label">응답 진행률:</span>
                <span class="metric-value">
                    {((responseCount / maxRequests) * 100).toFixed(1)}% ({responseCount}/{maxRequests})
                </span>
            </div>
            {#if startTime}
                <div class="metric-row">
                    <span class="metric-label">총 경과 시간:</span>
                    <span class="metric-value">{elapsedTime.toFixed(2)}초</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">요청 전송 시간:</span>
                    <span class="metric-value">{requestTime.toFixed(2)}초</span>
                </div>
                {#if lastRequestTime}
                    <div class="metric-row">
                        <span class="metric-label">응답 대기 시간:</span>
                        <span class="metric-value"
                            >{responseTime.toFixed(2)}초</span
                        >
                    </div>
                {/if}
            {/if}
        </div>
    {:else}
        <div class="complete-info">
            <div>테스트 완료!</div>
            <div>
                요청 전송 완료: {((lastRequestTime - startTime) / 1000).toFixed(
                    2,
                )}초
            </div>
            <div>전체 완료: {((endTime - startTime) / 1000).toFixed(2)}초</div>
            <div>
                응답 처리: {((endTime - lastRequestTime) / 1000).toFixed(2)}초
            </div>
        </div>
    {/if}
</div>

<div
    class="scroll-container"
    bind:this={scrollContainer}
    on:scroll={handleScroll}
    style="height: {height};"
>
    {#each items as item}
        <div class="scroll-item">{item}</div>
    {/each}
</div>

<style>
    .scroll-container {
        overflow-y: auto;
        border: 1px solid #ccc;
        border-radius: 4px;
        background: #fff;
    }

    .scroll-item {
        padding: 1rem;
        border-bottom: 1px solid #eee;
    }

    .scroll-item:last-child {
        border-bottom: none;
    }

    .scroll-test-info {
        margin-bottom: 1rem;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 4px;
    }

    .progress-info,
    .complete-info {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .metric-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem;
        background: rgba(13, 110, 253, 0.1);
        border-radius: 4px;
    }

    .metric-label {
        color: #495057;
        font-weight: 500;
    }

    .metric-value {
        color: #0d6efd;
        font-weight: bold;
    }

    .complete-info {
        color: #198754;
        font-weight: bold;
    }
</style>
