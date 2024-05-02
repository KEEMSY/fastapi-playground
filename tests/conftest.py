import pytest
from starlette.testclient import TestClient

from src.database import Base, get_db
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
