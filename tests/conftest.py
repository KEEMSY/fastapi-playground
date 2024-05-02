import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from starlette.testclient import TestClient

from src.database import Base, get_db, get_async_db
from src.main import app

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SYNC_SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:test@localhost:3306/fastapi_test"

# sync_engine = create_engine(SYNC_SQLALCHEMY_DATABASE_URL, echo=True)
sync_engine = create_engine(SYNC_SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


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


ASYNC_SQLALCHEMY_DATABASE_URL = "mysql+asyncmy://root:test@localhost:3306/fastapi_test"
# async_engine = create_async_engine(ASYNC_SQLALCHEMY_DATABASE_URL, echo=True)
async_engine = create_async_engine(ASYNC_SQLALCHEMY_DATABASE_URL)

AsyncTestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=async_engine, class_=AsyncSession
)


@pytest_asyncio.fixture
async def async_session():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async_session = AsyncTestingSessionLocal()
    try:
        yield async_session
    finally:
        await async_session.close()


@pytest_asyncio.fixture
async def async_client(async_session):
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_async_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
