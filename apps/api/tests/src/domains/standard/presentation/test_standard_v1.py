"""
테스트 실행 방법:

1. 전체 테스트 실행:
    pytest tests/src/domains/standard/presentation/test_standard_v1.py -v

2. 계층별 테스트 실행:
    - Presentation 계층: pytest -m presentation
    - Repository 계층: pytest -m repository

3. 동기/비동기 테스트 실행:
    - 동기 테스트: pytest -m sync_test
    - 비동기 테스트: pytest -m async_test

4. 복합 조건 테스트 실행:
    - 동기 Presentation 테스트: pytest -m "presentation and sync_test"
    - 비동기 Repository 테스트: pytest -m "repository and async_test"

5. 특정 테스트 함수 실행:
    - pytest tests/src/domains/standard/presentation/test_standard_v1.py::test_sync_standard_create -v
    - pytest tests/src/domains/standard/presentation/test_standard_v1.py::test_async_standard_create -v
"""

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

@pytest.mark.presentation
@pytest.mark.sync_test
def test_sync_standard_create(client):
    """동기 db 세션 api 테스트"""
    response = client.get("/api/v1/standard/sync-test-with-sync-db-session")
    assert response.status_code == 200


@pytest.mark.presentation
@pytest.mark.async_test
@pytest.mark.asyncio
async def test_async_standard_create(async_client):
    """비동기 db 세션 api 테스트"""
    response = await async_client.get("/api/v1/standard/async-test-with-async-db-session")
    assert response.status_code == 200


@pytest.mark.repository
@pytest.mark.sync_test
def test_sync_database_connection(db_session):
    """동기 데이터베이스 연결 테스트"""
    # 현재 연결된 데이터베이스 정보 확인
    result = db_session.execute(text("""
        SELECT current_database(), current_user, inet_server_addr()::text, inet_server_port()
    """))
    db_info = result.fetchone()
    
    print(f"\nSync Database Connection Info:")
    print(f"Database Name: {db_info[0]}")
    print(f"Current User: {db_info[1]}")
    print(f"Server Host: {db_info[2]}")
    print(f"Server Port: {db_info[3]}")
    
    # 기본 연결 테스트
    result = db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.repository
@pytest.mark.async_test
@pytest.mark.asyncio
async def test_async_database_connection(async_db_session):
    """비동기 데이터베이스 연결 테스트"""
    result = await async_db_session.execute(text("""
        SELECT current_database(), current_user, inet_server_addr()::text, inet_server_port()
    """))
    db_info = result.fetchone()
    
    print(f"\nAsync Database Connection Info:")
    print(f"Database Name: {db_info[0]}")
    print(f"Current User: {db_info[1]}")
    print(f"Server Host: {db_info[2]}")
    print(f"Server Port: {db_info[3]}")
    
    # 기본 연결 테스트
    result = await async_db_session.execute(text("SELECT 1"))
    value = result.scalar()
    assert value == 1