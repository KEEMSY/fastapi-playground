# tests/src/domains/async_example/repository/test_async_isolation_within_file.py
import pytest
import pytest_asyncio
from sqlalchemy import select
from datetime import datetime
from src.domains.async_example.database.models import AsyncExample

@pytest.mark.repository
@pytest.mark.asyncio
@pytest.mark.async_test
async def test_first_async_example_create(async_db_session):
    """첫 번째 AsyncExample 생성 테스트"""
    # 테스트 데이터 생성
    async_example = AsyncExample(
        name="First Test Example",
        description="First test description"
    )
    async_db_session.add(async_example)
    await async_db_session.commit()
    await async_db_session.refresh(async_example)

    # 데이터 확인
    result = await async_db_session.execute(select(AsyncExample))
    examples = result.scalars().all()
    
    assert len(examples) == 1, "테이블에 정확히 1개의 레코드가 있어야 함"
    assert examples[0].name == "First Test Example"
    assert examples[0].create_date is not None
    assert examples[0].modify_date is None

@pytest.mark.repository
@pytest.mark.asyncio
@pytest.mark.async_test
async def test_second_async_example_create(async_db_session):
    """두 번째 AsyncExample 생성 테스트 - 이전 테스트의 데이터가 없어야 함"""
    # 테이블이 비어있는지 확인
    result = await async_db_session.execute(select(AsyncExample))
    examples = result.scalars().all()
    assert len(examples) == 0, "새로운 테스트 시작 시 테이블이 비어있어야 함"

    # 새로운 데이터 생성
    async_example = AsyncExample(
        name="Second Test Example",
        description="Second test description"
    )
    async_db_session.add(async_example)
    await async_db_session.commit()
    await async_db_session.refresh(async_example)

    # 데이터 확인
    result = await async_db_session.execute(
        select(AsyncExample).where(AsyncExample.name == "Second Test Example")
    )
    example = result.scalar_one()
    assert example.description == "Second test description"
    assert example.create_date is not None

@pytest.mark.repository
@pytest.mark.asyncio
@pytest.mark.async_test
async def test_async_example_update(async_db_session):
    """AsyncExample 수정 테스트"""
    # 테스트 데이터 생성
    async_example = AsyncExample(
        name="Update Test Example",
        description="Original description"
    )
    async_db_session.add(async_example)
    await async_db_session.commit()
    await async_db_session.refresh(async_example)
    
    original_create_date = async_example.create_date

    # 데이터 수정
    async_example.description = "Updated description"
    await async_db_session.commit()
    await async_db_session.refresh(async_example)

    # 수정된 데이터 확인
    assert async_example.description == "Updated description"
    assert async_example.create_date == original_create_date
    assert async_example.modify_date is not None