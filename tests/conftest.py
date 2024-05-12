import asyncio
import os

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from starlette.testclient import TestClient

from src.database import Base, get_db, get_async_db

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ['ENVIRONMENT'] = 'TESTING'
SYNC_SQLALCHEMY_DATABASE_URL = os.environ["SYNC_SQLALCHEMY_TEST_DATABASE_URL"]

# sync_engine = create_engine(SYNC_SQLALCHEMY_DATABASE_URL, echo=True)
sync_engine = create_engine(SYNC_SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

from src.main import app


@pytest.fixture
def sync_session():
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sync_client(sync_session):
    def override_get_db():
        try:
            yield sync_session
        finally:
            sync_session.close()

    # app에서 사용하는 DB를 오버라이드하는 부분
    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)


ASYNC_SQLALCHEMY_DATABASE_URL = os.environ["ASYNC_SQLALCHEMY_TEST_DATABASE_URL"]
# async_engine = create_async_engine(ASYNC_SQLALCHEMY_DATABASE_URL, echo=True)
async_engine = create_async_engine(ASYNC_SQLALCHEMY_DATABASE_URL)

AsyncTestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=async_engine, class_=AsyncSession
)

"""
pytest_asyncio 의 기본 event_loop fixture 는 scope 가 Function 이며,
이 때문에 매 번 테스트 함수가 실행될 때 마다 기존 루프가 닫히고 새로운 루프가 생겨 다른 테스트의 session is closed 문제 발생.
이를 해결하기 위해, 전체 테스트를 싱행하는 동안 Loop를 하나만 사용하도록 session scope 의 event loop fixture 를 새로 정의한다.

참고 자료
- https://stackoverflow.com/questions/61022713/pytest-asyncio-has-a-closed-event-loop-but-only-when-running-all-tests
- https://arc.net/l/quote/obnyijxk
"""


# 방법 1,
# @pytest_asyncio.fixture(autouse=True, scope="session")
# def event_loop():
#     try:
#         loop = asyncio.get_running_loop()
#     except RuntimeError:
#         loop = asyncio.new_event_loop()
#     yield loop
#     loop.close()

# 방법 2.
# @pytest.fixture
# def event_loop():
#     yield asyncio.get_event_loop()
#
# def pytest_sessionfinish(session, exitstatus):
#     asyncio.get_event_loop().close()

# 방법 3.
@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Override pytest-asyncio's event loop fixture to session scope."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# Session scope 으로 설정하여, 전체 테스트를 실행하는 동안 한번의 데이터베이스 스키마를 생성하도록 설정한다.
@pytest_asyncio.fixture(scope="session")
async def setup_database():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def async_session():
    async_session = AsyncTestingSessionLocal()
    try:
        yield async_session
    finally:
        await async_session.close()


@pytest_asyncio.fixture
async def async_client(async_session, event_loop):
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_async_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
