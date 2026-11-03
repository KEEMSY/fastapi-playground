# ① async/await

## 목표
FastAPI에서 비동기 코드가 실제로 어떻게 실행되는지 이해하고, 블로킹 코드가 서비스 전체를 멈추게 하는 상황을 직접 재현하고 피할 수 있다.

## 학습 체크리스트

### 개념
- [ ] 이벤트 루프, 코루틴, Task의 관계
- [ ] `await` 지점에서만 제어권이 넘어간다는 의미
- [ ] 블로킹 호출(`time.sleep`, `requests`, 동기 DB 드라이버)이 루프를 막는 원리
- [ ] FastAPI에서 `def` 엔드포인트(스레드풀 실행)와 `async def` 엔드포인트(루프 실행)의 차이
- [ ] `asyncio.gather`, `asyncio.wait_for`(타임아웃), 취소(`CancelledError`)
- [ ] `run_in_threadpool` / `asyncio.to_thread`로 블로킹 코드 감싸기
- [ ] Celery 워커(기본적으로 동기)에서 async 코드를 재사용하는 방법과 주의점

### 실습
- [ ] `async def` + `time.sleep(3)` 엔드포인트와 `async def` + `await asyncio.sleep(3)` 엔드포인트 만들기
- [ ] `def` + `time.sleep(3)` 엔드포인트도 추가해 세 가지 비교
- [ ] `apps/api/HTTP Request.jmx`(JMeter)로 동시 요청 50개를 보내 응답 시간과 처리량 측정
- [ ] `httpx.AsyncClient`로 외부 API 3개를 순차 호출할 때와 `gather`로 호출할 때 비교

## 설명할 수 있어야 할 질문
1. `async def` 안에서 `requests.get()`을 호출하면 무슨 일이 일어나는가?
2. 그렇다면 `def` 엔드포인트에서 `requests.get()`을 호출하는 건 왜 괜찮은가? 한계는 무엇인가?
3. CPU 바운드 작업은 async로 빨라지는가?
4. Celery task 안에서 `asyncio.run()`을 호출하는 방식의 문제점은?

## 실습 결과

| 케이스 | 동시 요청 수 | 평균 응답 시간 | 처리량 |
|--------|-------------|---------------|--------|
| async + time.sleep | | | |
| async + asyncio.sleep | | | |
| def + time.sleep | | | |

## 노트


## 참고 자료
- FastAPI 공식 문서: Concurrency and async / await
- Python 공식 문서: asyncio
