from collections.abc import AsyncIterator

from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Settings(BaseSettings):
    # k8s 에서는 이 값이 Secret → 환경변수 DATABASE_URL 로 들어온다
    database_url: str = "postgresql+asyncpg://consign:consign@localhost:55432/consign"
    # 없으면 Outbox 를 쌓기만 하고 내보내지 않는다(테스트는 Redis 없이 돈다)
    redis_url: str | None = None
    # 판매 이벤트를 어디로 보낼지: redis(Streams) | rabbitmq. trace 는 어느 쪽이든 Redis 에 남는다
    broker: str = "redis"
    rabbitmq_url: str = "amqp://guest:guest@localhost:55672/"
    # 콘솔이 정산 화면을 그릴 때 부르는 정산 서비스 주소. k8s 에선 Service 이름
    settlement_url: str = "http://localhost:8002"


settings = Settings()

# 엔진은 프로세스당 하나. 커넥션 풀을 가진다(pool_size 기본 5 + max_overflow 10).
# Pod 수 × 프로세스 수 × 15 가 Postgres max_connections 를 넘지 않아야 한다.
engine = create_async_engine(settings.database_url)

# expire_on_commit=False: 커밋 뒤 속성에 접근해도 다시 SELECT 하지 않는다.
# async 에서는 그 암묵적 SELECT(지연 로딩)가 await 없이 일어날 수 없어 MissingGreenlet 오류가 난다.
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncIterator[AsyncSession]:
    # 요청당 세션 하나. 요청이 끝나면 커넥션을 풀에 돌려준다
    async with SessionLocal() as session:
        yield session
