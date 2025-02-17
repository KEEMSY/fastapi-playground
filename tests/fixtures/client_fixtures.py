import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from src.main import app
from tests.fixtures.db_fixtures import (
    test_db_container, 
    db_session, 
    db_inspector, 
    async_db_session, 
    async_db_inspector
)

@pytest.fixture
def client(db_session):
    """동기 테스트 클라이언트 생성"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides["get_db"] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def async_client(async_db_session):
    """비동기 테스트 클라이언트 생성"""
    async def override_get_async_db():
        try:
            yield async_db_session
        finally:
            pass

    app.dependency_overrides["get_async_db"] = override_get_async_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test"
    ) as client:
        yield client
    
    app.dependency_overrides.clear()


########################################################
# 인증이 추가될 경우 사용
########################################################
# @pytest.fixture
# def authenticated_client(client, create_test_user):
#     """인증된 동기 테스트 클라이언트"""
#     response = client.post(
#         "/api/v1/auth/login",
#         json={"username": "testuser", "password": "testpass"}
#     )
#     token = response.json()["access_token"]
#     client.headers = {"Authorization": f"Bearer {token}"}
#     return client

# @pytest.fixture
# async def authenticated_async_client(async_client, create_test_user):
#     """인증된 비동기 테스트 클라이언트"""
#     response = async_client.post(
#         "/api/v1/auth/login",
#         json={"username": "testuser", "password": "testpass"}
#     )
#     token = response.json()["access_token"]
#     async_client.headers = {"Authorization": f"Bearer {token}"}
#     return async_client
