import pytest
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from src.database.database import Base
from src.database.models import *  # 모든 모델을 import
from tests.utils.docker_utils import start_database_container
from tests.config import get_test_settings
from alembic import command
from alembic.config import Config
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import async_sessionmaker
import pytest_asyncio


########### 공통 ############


@pytest.fixture(scope="session", autouse=True)
def test_db_container():
    """테스트 데이터베이스 컨테이너 관리 fixture"""
    container = start_database_container()

    # PostgreSQL이 완전히 시작될 때까지 대기
    import time

    time.sleep(3)

    yield container

    # 테스트 종료 후 컨테이너 정리
    container.stop()


########## 동기 세션 ##########


def print_alembic_info():
    """Alembic 설정 및 마이그레이션 파일 정보 출력"""
    try:
        migrations_dir = Path("migrations/versions")
        print("\nAlembic Migration Files:")
        for migration_file in migrations_dir.glob("*.py"):
            print(f"- {migration_file.name}")

        # alembic.ini 파일 확인
        alembic_ini = Path("alembic.ini")
        if alembic_ini.exists():
            print("\nAlembic.ini configuration:")
            with open(alembic_ini) as f:
                print(f.read())
    except Exception as e:
        print(f"Error reading alembic info: {e}")


@pytest.fixture(scope="session")
def db_session(test_db_container):
    """동기 데이터베이스 세션 fixture"""
    settings = get_test_settings()
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=20,           # 비동기 설정과 동일하게 조정
        max_overflow=30,
        pool_timeout=10,
        pool_recycle=3600,
        pool_pre_ping=True,
        echo=False
    )

    print("\nRegistered models in Base.metadata:")
    for table in Base.metadata.tables:
        print(f"- {table}")

    with engine.connect() as connection:
        # uuid-ossp 확장 설치
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        connection.commit()

        # 기존 테이블 삭제 (필요한 경우)
        connection.execute(text("DROP TABLE IF EXISTS studies CASCADE"))
        connection.commit()

        print_alembic_info()

        # 모든 테이블 생성
        Base.metadata.create_all(engine)
        connection.commit()

        # 테이블 생성 확인
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\nCreated tables: {tables}")

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False  # 세션 일관성을 위해 추가
    )
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        engine.dispose()  # 엔진 리소스 정리 추가


@pytest.fixture(scope="session")
def db_inspector(db_session):
    """데이터베이스 검사를 위한 inspector fixture"""
    engine = db_session.get_bind()
    inspector = inspect(engine)
    return inspector


########## 비동기 세션 (디버깅이 필요함)##########

# @pytest_asyncio.fixture(scope="function") -- 성공
# @pytest_asyncio.fixture(scope="session") -- 실패
# @pytest_asyncio.fixture # -- 성공 
# async def async_db_session(test_db_container):
#     """비동기 데이터베이스 세션 fixture"""
#     settings = get_test_settings()
#     async_engine = create_async_engine(
#         settings.ASYNC_DATABASE_URL,
#         pool_size=5,
#         max_overflow=10,
#         pool_timeout=30,
#         pool_recycle=1800,
#         pool_pre_ping=True,
#         echo=True,
#         future=True
#     )

#     # 세션 팩토리 생성
#     async_session_factory = async_sessionmaker(
#         async_engine,
#         class_=AsyncSession,
#         expire_on_commit=False,
#         autocommit=False,
#         autoflush=False
#     )

#     async with async_session_factory() as session:
#         async with async_engine.begin() as conn:
#             # uuid-ossp 확장 설치
#             await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            
#             # 테이블 생성
#             await conn.run_sync(Base.metadata.create_all)

#         try:
#             yield session
#         finally:
#             await session.close()
#             await async_engine.dispose()


# @pytest_asyncio.fixture
# async def async_db_inspector(async_db_session):
#     """비동기 데이터베이스 검사를 위한 inspector fixture"""
#     engine = async_db_session.get_bind()
#     def get_inspector(sync_conn):
#         return inspect(sync_conn)
#     inspector = await engine.run_sync(get_inspector)
#     return inspector


###### 가능한 설정의 비동기 설정 ######
@pytest_asyncio.fixture
async def async_db_session(test_db_container):
    """비동기 데이터베이스 세션 fixture"""
    settings = get_test_settings()
    async_engine = create_async_engine(
        settings.ASYNC_DATABASE_URL,
        pool_size=20,
        max_overflow=30,
        pool_timeout=10,
        pool_recycle=3600,
        pool_pre_ping=True,
        echo=False
    )

    # 테이블 생성은 engine.begin()을 사용
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 세션 생성
    async_session = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await async_engine.dispose()


@pytest.fixture(autouse=True)
def cleanup_all_tables_sync(db_session: Session):
    """동기 세션에서 모든 테이블의 데이터를 정리하는 fixture"""
    try:
        # 모든 테이블 목록 조회
        result = db_session.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        tables = [row[0] for row in result]
        
        # 각 테이블의 데이터만 삭제
        for table in tables:
            db_session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        raise e

@pytest_asyncio.fixture(autouse=True)
async def cleanup_all_tables_async(async_db_session: AsyncSession):
    """비동기 세션에서 모든 테이블의 데이터를 정리하는 fixture"""
    try:
        # 모든 테이블 목록 조회
        result = await async_db_session.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        tables = [row[0] for row in result]
        
        # 각 테이블의 데이터만 삭제
        for table in tables:
            await async_db_session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        
        await async_db_session.commit()
    except Exception as e:
        await async_db_session.rollback()
        raise e