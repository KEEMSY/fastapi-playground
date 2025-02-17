import pytest
from fastapi.testclient import TestClient
import asyncio

########## 동기 API 테스트 ##########

def test_sync_test_endpoint(client):
    """단순 동기 API 테스트"""
    response = client.get("/api/v1/standard/sync-test")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "message" in data["data"]
    assert "test" in data["data"]["message"]

def test_sync_test_with_wait(client):
    """동기 대기 API 테스트"""
    timeout = 2
    response = client.get(f"/api/v1/standard/sync-test-with-wait?timeout={timeout}")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "message" in data["data"]

########## 비동기 API 테스트 ##########

@pytest.mark.asyncio
async def test_async_test_endpoint(async_client):
    """단순 비동기 API 테스트"""
    response = await async_client.get("/api/v1/standard/async-test")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "message" in data["data"]

@pytest.mark.asyncio
async def test_async_test_with_await(async_client):
    """비동기 대기 API 테스트"""
    timeout = 2
    response = await async_client.get(f"/api/v1/standard/async-test-with-await?timeout={timeout}")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "message" in data["data"]

########## DB 세션 테스트 ##########

def test_sync_db_session(client):
    """동기 DB 세션 테스트"""
    timeout = 1
    response = client.get(f"/api/v1/standard/sync-test-with-sync-db-session?timeout={timeout}")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_async_db_session(async_client):
    """비동기 DB 세션 테스트"""
    timeout = 1
    response = await async_client.get(f"/api/v1/standard/async-test-with-async-db-session?timeout={timeout}")
    assert response.status_code == 200

########## 동시성 테스트 ##########

@pytest.mark.asyncio
async def test_concurrent_requests(async_client):
    """동시 요청 처리 테스트"""
    async def make_request():
        response = await async_client.get("/api/v1/standard/async-test")
        return response.status_code

    tasks = [make_request() for _ in range(10)]
    results = await asyncio.gather(*tasks)
    assert all(status == 200 for status in results)

########## 에러 처리 테스트 ##########

def test_invalid_timeout(client):
    """잘못된 타임아웃 값 테스트"""
    # 허용 범위를 벗어난 타임아웃 값
    timeout = 11
    response = client.get(f"/api/v1/standard/sync-test-with-wait?timeout={timeout}")
    assert response.status_code == 422  # Validation Error

def test_sync_standard_create(client):
    """동기 Standard 생성 테스트"""
    response = client.get("/api/v1/standard/sync-test-with-sync-db-session")
    assert response.status_code == 200

def test_sync_standard_get(client):
    """동기 Standard 조회 테스트"""
    # 먼저 데이터 생성
    create_response = client.post("/api/v1/standard", json={
        "name": "test standard",
        "description": "test description"
    })
    standard_id = create_response.json()["data"]["id"]
    
    # 생성된 데이터 조회
    response = client.get(f"/api/v1/standard/{standard_id}")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"]["name"] == "test standard"

@pytest.mark.asyncio
async def test_async_standard_create(async_client):
    """비동기 Standard 생성 테스트"""
    response = await async_client.get("/api/v1/standard/async-test-with-async-db-session")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_async_standard_get(async_client):
    """비동기 Standard 조회 테스트"""
    # 먼저 데이터 생성
    create_response = await async_client.post("/api/v1/standard/async", json={
        "name": "async test standard",
        "description": "async test description"
    })
    standard_id = create_response.json()["data"]["id"]
    
    # 생성된 데이터 조회
    response = await async_client.get(f"/api/v1/standard/async/{standard_id}")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"]["name"] == "async test standard"