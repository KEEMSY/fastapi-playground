---
name: add-test
description: This skill should be used when the user asks to "add test", "create test", "generate test", "테스트 추가", "테스트 생성", "테스트 만들어줘", or wants to scaffold pytest test cases for a domain.
version: 1.0.0
---

# Add Test Generator

FastAPI 도메인의 라우터·서비스 코드를 분석해 엣지케이스를 포함한 pytest 테스트 케이스를 자동 스캐폴드합니다.

## 사용 시점

- 새 도메인 생성 후 테스트 커버리지 확보
- 기존 도메인에 테스트 추가
- 예: "question 테스트 만들어줘", "/add-test product"

## 실행 플로우

### 1단계: 정보 수집

```yaml
질문 1: 도메인명은?
  - 예: question, product, answer

질문 2: 테스트 대상 엔드포인트?
  - 전체(list/detail/create/update/delete/vote) | 선택
  - 기본: 전체

질문 3: 테스트 DB 전략?
  - SQLite in-memory (기본, 빠름)
  - 실제 DB (docker-compose-dev.yml 필요)
```

### 2단계: 기존 코드 분석

```python
# 분석 대상
src/domains/{domain}/router.py   # 엔드포인트·파라미터 파악
src/domains/{domain}/service.py  # 비즈니스 로직 파악
src/domains/{domain}/schemas.py  # 입출력 스키마 파악
src/domains/{domain}/models.py   # DB 모델 파악
```

### 3단계: 파일 생성

#### 3.1 conftest.py (없으면 생성)

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.database.database import Base, get_async_db
from main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_async_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def auth_headers(client):
    """테스트용 사용자 생성 및 JWT 토큰 반환."""
    await client.post("/api/user/create", json={
        "username": "testuser",
        "password1": "testpass123",
        "password2": "testpass123",
        "email": "test@test.com"
    })
    resp = await client.post("/api/user/login", data={
        "username": "testuser",
        "password": "testpass123"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

#### 3.2 tests/domains/test_{domain}.py 생성

```python
# tests/domains/test_{domain}.py
import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE_URL = "/api/{domain}"


class TestGet{Domain}List:
    """GET /api/{domain}/list"""

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient):
        """빈 목록 반환."""
        resp = await client.get(f"{BASE_URL}/list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["{domain}_list"] == []

    @pytest.mark.asyncio
    async def test_list_with_data(self, client: AsyncClient, auth_headers: dict):
        """데이터 있을 때 목록 반환."""
        # 데이터 생성
        await client.post(f"{BASE_URL}/create", json={사용자_입력_필드}, headers=auth_headers)
        resp = await client.get(f"{BASE_URL}/list")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_list_pagination(self, client: AsyncClient, auth_headers: dict):
        """페이지네이션 동작 확인."""
        # 3개 생성 후 size=2로 요청
        for i in range(3):
            await client.post(f"{BASE_URL}/create", json={...}, headers=auth_headers)
        resp = await client.get(f"{BASE_URL}/list?page=0&size=2")
        assert resp.status_code == 200
        assert len(resp.json()["{domain}_list"]) == 2

    @pytest.mark.asyncio
    async def test_list_keyword_search(self, client: AsyncClient, auth_headers: dict):
        """키워드 검색 동작 확인."""
        await client.post(f"{BASE_URL}/create", json={"title": "FastAPI 강의"}, headers=auth_headers)
        resp = await client.get(f"{BASE_URL}/list?keyword=FastAPI")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestGet{Domain}Detail:
    """GET /api/{domain}/detail/{id}"""

    @pytest.mark.asyncio
    async def test_detail_success(self, client: AsyncClient, auth_headers: dict):
        """정상 상세 조회."""
        create_resp = await client.post(f"{BASE_URL}/create", json={...}, headers=auth_headers)
        # 생성 후 list에서 id 확인
        list_resp = await client.get(f"{BASE_URL}/list")
        domain_id = list_resp.json()["{domain}_list"][0]["id"]

        resp = await client.get(f"{BASE_URL}/detail/{domain_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_detail_not_found(self, client: AsyncClient):
        """존재하지 않는 ID 조회 → 404."""
        resp = await client.get(f"{BASE_URL}/detail/99999")
        assert resp.status_code == 404


class TestCreate{Domain}:
    """POST /api/{domain}/create"""

    @pytest.mark.asyncio
    async def test_create_success(self, client: AsyncClient, auth_headers: dict):
        """정상 생성 → 204."""
        resp = await client.post(
            f"{BASE_URL}/create",
            json={정상_데이터},
            headers=auth_headers
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_create_unauthenticated(self, client: AsyncClient):
        """인증 없이 생성 → 401."""
        resp = await client.post(f"{BASE_URL}/create", json={정상_데이터})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_empty_field(self, client: AsyncClient, auth_headers: dict):
        """필수 필드 빈값 → 422."""
        resp = await client.post(
            f"{BASE_URL}/create",
            json={"title": "  "},  # 공백만 있는 경우
            headers=auth_headers
        )
        assert resp.status_code == 422


class TestUpdate{Domain}:
    """PUT /api/{domain}/update"""

    @pytest.mark.asyncio
    async def test_update_success(self, client: AsyncClient, auth_headers: dict):
        """정상 수정 → 204."""
        ...

    @pytest.mark.asyncio
    async def test_update_no_permission(self, client: AsyncClient, auth_headers: dict):
        """다른 사용자가 수정 → 400."""
        ...

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        """존재하지 않는 항목 수정 → 400."""
        resp = await client.put(
            f"{BASE_URL}/update",
            json={"{domain}_id": 99999},
            headers=auth_headers
        )
        assert resp.status_code == 400


class TestDelete{Domain}:
    """DELETE /api/{domain}/delete"""

    @pytest.mark.asyncio
    async def test_delete_success(self, client: AsyncClient, auth_headers: dict):
        """정상 삭제 → 204."""
        ...

    @pytest.mark.asyncio
    async def test_delete_no_permission(self, client: AsyncClient, auth_headers: dict):
        """다른 사용자가 삭제 → 400."""
        ...


class TestVote{Domain}:
    """POST /api/{domain}/vote"""

    @pytest.mark.asyncio
    async def test_vote_success(self, client: AsyncClient, auth_headers: dict):
        """정상 투표 → 204."""
        ...

    @pytest.mark.asyncio
    async def test_vote_unauthenticated(self, client: AsyncClient):
        """인증 없이 투표 → 401."""
        resp = await client.post(f"{BASE_URL}/vote", json={"{domain}_id": 1})
        assert resp.status_code == 401
```

### 4단계: 완료 리포트

```
✅ {Domain} 테스트 스캐폴드 완료!

생성된 파일:
- tests/domains/test_{domain}.py ({N}개 테스트 케이스)
- tests/conftest.py (공통 픽스처)

테스트 실행:
  docker compose -f docker-compose-dev.yml exec fastapi pytest tests/domains/test_{domain}.py -v

커버리지 포함:
  pytest tests/domains/test_{domain}.py -v --cov=src/domains/{domain} --cov-report=term-missing
```

## 엣지케이스 체크리스트

생성된 테스트가 반드시 포함해야 할 케이스:

- [ ] 빈 목록 (total=0)
- [ ] 인증 없이 보호된 엔드포인트 접근 → 401
- [ ] 존재하지 않는 ID 조회 → 404 or 400
- [ ] 필수 필드 빈값 → 422 (Pydantic validation)
- [ ] 다른 사용자가 수정/삭제 → 400 (권한 없음)
- [ ] 페이지네이션 경계값 (size=0, 음수)
- [ ] 키워드 검색 (매칭/비매칭)
- [ ] 중복 투표 처리
