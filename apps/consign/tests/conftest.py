import pytest
from httpx import ASGITransport, AsyncClient

from app.db import Base, engine, settings
from app.main import app


@pytest.fixture
async def client():
    # 테스트마다 테이블을 새로 만든다. 실제 Postgres 에 붙인다 — 동시성 검증은 SQLite 로는 의미가 없다
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # ASGITransport: 서버를 띄우지 않고 앱을 같은 이벤트 루프에서 직접 호출한다
    # ASGITransport 는 lifespan 을 돌리지 않는다. app.state(http·redis 클라이언트)가 필요하니 직접 감싼다.
    # lifespan 종료가 engine.dispose() 를 하므로 pytest-asyncio 의 테스트별 이벤트 루프 문제도 같이 풀린다
    # 기본 정산 주소(localhost:8002)는 kind 클러스터가 떠 있으면 실제로 응답한다. 테스트가 클러스터에 기대지 않게 빈 포트로
    settings.settlement_url = "http://127.0.0.1:9"
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
