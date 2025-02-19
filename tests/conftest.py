
### 테스트 관련 픽스쳐 ###
# - 픽스처를 파일별로 구분하고, conftest.py 에서 호출하는 방식으로 테스트 환경 세팅 진행 할 것
#   - 2025.02.14 기준 시작
from .fixtures.db_fixtures import test_db_container, db_session, db_inspector, async_db_session 
from .fixtures.client_fixtures import client, async_client
from .fixtures.eventloop_fixture import event_loop
from .fixtures.redis_fixture import redis_client
###

# os.environ["ENVIRONMENT"] = "TESTING"
# SYNC_SQLALCHEMY_DATABASE_URL = os.environ["SYNC_SQLALCHEMY_TEST_DATABASE_URL"]


# def sync_create_database():
#     engine = create_engine(SYNC_SQLALCHEMY_DATABASE_URL.rsplit("/", 1)[0])
#     with engine.connect() as conn:
#         conn.execute(text("CREATE DATABASE IF NOT EXISTS fastapi_test"))


# async def async_create_database():
#     engine = create_async_engine(ASYNC_SQLALCHEMY_DATABASE_URL.rsplit("/", 1)[0])
#     async with engine.begin() as conn:
#         await conn.execute(text("CREATE DATABASE IF NOT EXISTS fastapi_test"))
#     await engine.dispose()


# # sync_engine = create_engine(SYNC_SQLALCHEMY_DATABASE_URL, echo=True)
# sync_engine = create_engine(SYNC_SQLALCHEMY_DATABASE_URL)
# TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# from src.main import app


# @pytest_asyncio.fixture(scope="session")
# async def apply_migrations(async_setup_database):
#     config = Config("alembic.ini")
#     command.upgrade(config, "head")
#     yield
#     command.downgrade(config, "base")


# @pytest.fixture
# def sync_session(setup_database):
#     Base.metadata.create_all(bind=sync_engine)
#     db = TestingSessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
#         Base.metadata.drop_all(bind=sync_engine)


# @pytest.fixture
# def sync_client(sync_session):
#     def override_get_db():
#         try:
#             yield sync_session
#         finally:
#             sync_session.close()

#     # app에서 사용하는 DB를 오버라이드하는 부분
#     app.dependency_overrides[get_db] = override_get_db

#     yield TestClient(app)


# ASYNC_SQLALCHEMY_DATABASE_URL = os.environ["ASYNC_SQLALCHEMY_TEST_DATABASE_URL"]
# # async_engine = create_async_engine(ASYNC_SQLALCHEMY_DATABASE_URL, echo=True)
# async_engine = create_async_engine(ASYNC_SQLALCHEMY_DATABASE_URL)

# AsyncTestingSessionLocal = sessionmaker(
#     autocommit=False, autoflush=False, bind=async_engine, class_=AsyncSession
# )




# # Session scope 으로 설정하여, 전체 테스트를 실행하는 동안 한번의 데이터베이스 스키마를 생성하도록 설정한다.
# @pytest_asyncio.fixture(scope="session")
# def setup_database():
#     sync_create_database()
#     yield
#     # 여기에 데이터베이스 정리 로직을 추가할 수 있습니다.


# @pytest_asyncio.fixture(scope="session")
# async def async_setup_database():
#     await async_create_database()
#     yield
#     # 여기에 비동기 데이터베이스 정리 로직을 추가할 수 있습니다.


# @pytest_asyncio.fixture
# async def async_session(async_setup_database):
#     async with async_engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     async with AsyncTestingSessionLocal() as session:
#         yield session
#     async with async_engine.begin() as conn:
#         await conn.run_sync(Base.metadata.drop_all)


# @pytest_asyncio.fixture
# async def async_example_repository():
#     return AsyncExamplePersistenceAdapter(async_session)


# @pytest_asyncio.fixture
# async def get_async_example_repository(async_session):
#     app.dependency_overrides[get_async_example_repository] = async_example_repository
#     return AsyncExamplePersistenceAdapter(async_session)


# @pytest_asyncio.fixture
# async def async_client(async_session):
#     async def override_get_db():
#         yield async_session

#     app.dependency_overrides[get_async_db] = override_get_db
#     async with AsyncClient(
#         transport=ASGITransport(app=app), base_url="http://test"
#     ) as client:
#         yield client




# @pytest_asyncio.fixture()
# async def async_example_redis(redis_client):
#     return AsyncExampleRedis(redis_url="redis://:myStrongPassword@localhost:16379")


# async def async_cleanup_database(session: AsyncSession):
#     """
#     [ 모든 테이블의 데이터를 삭제 ]
#     1. 외래 키 제약조건을 비활성화합니다.(테이블 연관 관계로 인한 데이터 삭제 오류 방지)
#     2. 모든 테이블의 데이터를 삭제한다.
#     3. 외래 키 제약조건을 다시 활성화한다.
#     """
#     # 1. 외래 키 제약조건 비활성화 (PostgreSQL과 MySQL에 맞게 조절)
#     if "postgresql" in ASYNC_SQLALCHEMY_DATABASE_URL:
#         await session.execute(text("SET session_replication_role = REPLICA;"))
#     elif "mysql" in ASYNC_SQLALCHEMY_DATABASE_URL:
#         await session.execute(text("SET foreign_key_checks = 0;"))

#     # 2. 모든 테이블의 데이터를 삭제
#     for table in reversed(Base.metadata.sorted_tables):
#         await session.execute(table.delete())

#     # 3. 외래 키 제약조건을 다시 활성화
#     if "postgresql" in ASYNC_SQLALCHEMY_DATABASE_URL:
#         await session.execute(text("SET session_replication_role = DEFAULT;"))
#     elif "mysql" in ASYNC_SQLALCHEMY_DATABASE_URL:
#         await session.execute(text("SET foreign_key_checks = 1;"))

#     await session.commit()  # 변경 사항을 적용
