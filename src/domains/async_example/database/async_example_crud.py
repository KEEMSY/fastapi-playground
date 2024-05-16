import logging
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domains.async_example.business.schemas import AsyncExampleSchema, ASyncExampleSchemaList
from src.domains.async_example.constants import ErrorCode
from src.domains.async_example.database.models import AsyncExample
from src.exceptions import DLException, handle_exceptions, ExceptionResponse

logger = logging.getLogger(__name__)

"""
[ 해야 할 일 ]
1. commit 위치 변경 
- async_example_repository(port) 생성 및 구현체(adapter) 생성 -> 구현체에서 commit 관리

2. DL에서 발생한 예측하지 못한 에러 처리
- 이것이 DLException으로 처리해야 된다 생각 24.05.15
"""


@handle_exceptions
async def create_async_example(db: AsyncSession, async_example: AsyncExampleSchema) -> AsyncExampleSchema:
    async_example = AsyncExample(
        name=async_example.name,
        description=async_example.description
    )
    db.add(async_example)
    await db.commit()
    await db.refresh(async_example)

    return AsyncExampleSchema.model_validate(async_example)


async def read_async_example(db: AsyncSession, async_example_id: int) -> AsyncExampleSchema:
    """
    단순한 조회로, 특정 ID에 대한 직접 조회만 수행한다. 만약 연관관계가 있는 경우 다른 방법(read_fetch_async_example_with_user)을 사용한다.
    """
    result = await db.get(AsyncExample, async_example_id)
    if result is None:
        logger.error(f"No AsyncExample found with id {async_example_id}")
        raise DLException(detail=f"No AsyncExample found with id {async_example_id}")

    try:
        result_into_schema = AsyncExampleSchema.model_validate(result)
        logger.info(f"Retrieved AsyncExample {async_example_id}")
        return result_into_schema
    except Exception as e:
        logger.error(f"Error while retrieving AsyncExample {async_example_id}")
        raise DLException(code="D0000", detail=f"Error while retrieving AsyncExample {async_example_id}")


@handle_exceptions
async def read_async_example_list(db, limit, offset, keyword):
    # 조건을 설정한다. 기본적으로 모든 데이터를 대상으로 한다.
    search_condition = True  # 모든 데이터를 반환하는 기본 조건

    if keyword:
        # 키워드가 주어진 경우 검색 조건을 추가한다.
        search_condition = or_(
            AsyncExample.name.ilike(f'%{keyword}%'),
            AsyncExample.description.ilike(f'%{keyword}%')
        )

    # 검색 조건을 기반으로 쿼리를 구성한다.
    query = select(AsyncExample).where(search_condition).order_by(AsyncExample.create_date.desc())

    # 쿼리 실행
    results = await db.execute(query.offset(offset).limit(limit))
    async_example_list = results.scalars().all()
    async_example_schema_list = [AsyncExampleSchema.model_validate(async_example) for async_example in
                                 async_example_list]

    # 전체 개수를 계산하는 쿼리를 생성한다.
    total_count_query = select(func.count()).select_from(
        select(AsyncExample).where(search_condition).subquery()
    )

    # 전체 개수 조회
    total_count = await db.execute(total_count_query)
    total = total_count.scalar_one()

    return ASyncExampleSchemaList(total=total, example_list=async_example_schema_list)


@handle_exceptions
async def read_fetch_async_example_with_user(db: AsyncSession, async_example_id: int) -> AsyncExampleSchema:
    """
    연관 관계가 있는 경우, 한번에 모두 가져오는 쿼리를 발생시킨다.
    """
    try:
        stmt = (
            select(AsyncExample)
            .options(selectinload(AsyncExample.user))
            .where(AsyncExample.id == async_example_id)
        )
        result = await db.execute(stmt)
        async_example = result.scalars().first()

        if async_example is None:
            logger.error(f"No AsyncExample found with id {async_example_id}")
            raise ExceptionResponse(error_code=ErrorCode.NOT_FOUND,
                                    message=f"No AsyncExample found with id {async_example_id}")

        return AsyncExampleSchema.model_validate(async_example)

    except ExceptionResponse as er:
        raise

    except Exception as e:
        logger.error(f"Error while retrieving AsyncExample {async_example_id}: {str(e)}")
        raise DLException(detail=f"Error while retrieving AsyncExample {async_example_id}")


@handle_exceptions
async def update_async_example_v1(db: AsyncSession, async_example_id: int,
                                  async_example_schema: AsyncExampleSchema) -> AsyncExampleSchema:
    async_example = await db.get(AsyncExample, async_example_id)
    if async_example is None:
        logger.error(f"No AsyncExample found with id {async_example_id}")
        raise ExceptionResponse(error_code=ErrorCode.NOT_FOUND,
                                message=f"No AsyncExample found with id {async_example_id}")

    async_example.name = async_example_schema.name
    async_example.description = async_example_schema.description

    await db.commit()
    await db.refresh(async_example)

    return AsyncExampleSchema.model_validate(async_example)


@handle_exceptions
async def update_async_example_v2(db: AsyncSession, async_example_schema: AsyncExampleSchema) -> AsyncExampleSchema:
    async_example = await db.get(AsyncExample, async_example_schema.id)
    if async_example is None:
        logger.error(f"No AsyncExample found with id {async_example_schema.id}")
        raise ExceptionResponse(error_code=ErrorCode.NOT_FOUND,
                                message=f"No AsyncExample found with id {async_example_schema.id}")

    async_example.name = async_example_schema.name
    async_example.description = async_example_schema.description

    await db.commit()
    await db.refresh(async_example)

    return AsyncExampleSchema.model_validate(async_example)


@handle_exceptions
async def delete_async_example(db: AsyncSession, async_example_id: int):
    async_example = await db.get(AsyncExample, async_example_id)
    if async_example is None:
        logger.error(f"No AsyncExample found with id {async_example_id}")
        raise ExceptionResponse(error_code=ErrorCode.NOT_FOUND,
                                message=f"No AsyncExample found with id {async_example_id}")

    await db.delete(async_example)
    await db.commit()
    logger.info(f"Deleted AsyncExample with ID {async_example_id}")

    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error while deleting ASyncExample: {e}")
        raise DLException(code=DLErrorCode.DATABASE_ERROR, detail="Database error occurred while deleting SyncExample.")

    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error while deleting SyncExample: {e}")
        raise DLException(code=DLErrorCode.UNKNOWN_ERROR,
                          detail="An unexpected error occurred while deleting ASyncExample.")
