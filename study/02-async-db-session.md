# ② 비동기 DB 세션 관리

## 목표
SQLAlchemy AsyncSession의 수명 주기와 트랜잭션 경계를 설계할 수 있고, k8s 환경에서 커넥션 풀 크기를 근거를 갖고 정할 수 있다.

## 학습 체크리스트

### 개념
- [ ] AsyncEngine, AsyncSession, Connection, Transaction의 관계
- [ ] 요청 단위 세션(request-scoped)과 FastAPI `yield` 의존성의 동작 방식
- [ ] 트랜잭션 경계를 어디에 둘지 (라우터, 서비스, 리포지토리)
- [ ] autobegin 동작과 `session.begin()`, `begin_nested()`(savepoint)
- [ ] `expire_on_commit=False`가 필요한 이유
- [ ] lazy loading을 쓰면 `MissingGreenlet` 에러가 나는 이유와 `selectinload` / `joinedload`
- [ ] AsyncSession 하나를 여러 태스크가 동시에 쓰면 안 되는 이유 (`gather` + 같은 세션)
- [ ] 커넥션 풀 옵션: `pool_size`, `max_overflow`, `pool_timeout`, `pool_pre_ping`, `pool_recycle`
- [ ] k8s 관점: `Pod 수 × (pool_size + max_overflow) ≤ DB max_connections` (HPA로 Pod가 늘어날 때 포함)
- [ ] Celery 워커처럼 HTTP 요청이 없는 곳에서 세션을 열고 닫는 방법

### 현재 코드 분석 (`apps/api/src/database.py`)
- [ ] `get_async_db()`의 retry 루프가 의도대로 동작하지 않는 이유 분석
  - 힌트: yield 의존성 제너레이터에 예외가 던져진 뒤 다시 `yield`하면 어떻게 되는가?
  - 재시도는 어느 계층에서 하는 게 맞는가?
- [ ] `AsyncTransactionManager.transaction()`의 `await self.async_db.begin()` 문제 분석
  - 앞에서 이미 쿼리를 실행해 autobegin된 경우
  - `@async_transactional` 메서드가 다른 `@async_transactional` 메서드를 호출하는 경우
- [ ] 개선안 작성 및 테스트 추가

### 실습
- [ ] `gather`에서 같은 세션을 공유해 에러를 재현해 보기
- [ ] lazy loading으로 `MissingGreenlet` 재현 후 수정
- [ ] `pool_size=2, max_overflow=0`으로 설정하고 동시 요청을 보내 `pool_timeout` 에러 재현
- [ ] 트랜잭션 중첩 시나리오 테스트 작성

## 설명할 수 있어야 할 질문
1. 요청 처리 중 예외가 나면 세션과 커넥션은 각각 어떻게 정리되는가?
2. 커밋은 라우터, 서비스, 리포지토리 중 어디서 해야 하고, 그 이유는?
3. Pod가 10개이고 `pool_size=10, max_overflow=20`이면 DB 입장에서 최대 커넥션 수는? 이게 왜 위험한가?
4. 같은 요청 안에서 두 서비스 메서드를 하나의 트랜잭션으로 묶으려면 어떻게 하는가?

## 내 개선안


## 노트


## 참고 자료
- SQLAlchemy 2.0 문서: Asynchronous I/O (asyncio)
- SQLAlchemy 2.0 문서: Connection Pooling
