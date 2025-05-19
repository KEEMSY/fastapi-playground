import pytest
import pytest_asyncio
from sqlalchemy import select
from src.domains.async_example.database.models import AsyncExample

@pytest.mark.repository
@pytest.mark.asyncio
@pytest.mark.async_test
async def test_independent_async_example_create(async_db_session):
    """다른 테스트 파일의 영향을 받지 않는 독립적인 테스트"""
    # 테이블이 비어있는지 확인
    result = await async_db_session.execute(select(AsyncExample))
    examples = result.scalars().all()
    assert len(examples) == 0, "테이블이 비어있어야 함"

    # 새로운 데이터 생성
    async_example = AsyncExample(
        name="Independent Test Example",
        description="Test from another file"
    )
    async_db_session.add(async_example)
    await async_db_session.commit()

    # 데이터 확인
    result = await async_db_session.execute(
        select(AsyncExample).where(AsyncExample.name == "Independent Test Example")
    )
    example = result.scalar_one()
    assert example.description == "Test from another file"

@pytest.mark.repository
@pytest.mark.asyncio
@pytest.mark.async_test
async def test_bulk_async_example_create(async_db_session):
    """대량 데이터 생성 테스트"""
    # 여러 데이터 생성
    examples = [
        AsyncExample(
            name=f"Bulk Test Example {i}",
            description=f"Bulk test description {i}"
        )
        for i in range(3)
    ]
    async_db_session.add_all(examples)
    await async_db_session.commit()

    # 데이터 수 확인
    result = await async_db_session.execute(select(AsyncExample))
    examples = result.scalars().all()
    assert len(examples) == 3, "정확히 3개의 레코드가 있어야 함"