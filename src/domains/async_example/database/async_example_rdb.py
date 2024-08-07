import logging

from sqlalchemy import or_, select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domains.async_example.business.schemas import AsyncExampleSchema, ASyncExampleSchemaList, \
    RelatedAsyncExampleSchema, RelatedAsyncExampleSchemaList
from src.domains.async_example.constants import ErrorCode
from src.domains.async_example.database.models import AsyncExample, RelatedAsyncExample
from src.exceptions import handle_exceptions, ExceptionResponse, DLException

logger = logging.getLogger(__name__)

"""
[ 해야할 일 ]
트랜잭션 처리를 위한 작업 진행
- 모든 Command 쿼리 내에 commit 삭제, flush 작업 진행

모든 Query 쿼리 내에 commit 및 flush 선택 옵션 추가
- is_commit: True, False
- is_flush: True, False

조회 메서드 내, 필요 기능 정리
- 필터링을 위한 동적 메서드(조회(단일), 검색(다수))추가
  - 속성 값을 통한 조회
  - 키워드를 통한 검색
  - 정렬
- 페이징
"""


class AsyncExampleCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db

    @handle_exceptions
    async def create_async_example(self, async_example: AsyncExampleSchema) -> AsyncExampleSchema:
        async_example = AsyncExample(
            name=async_example.name,
            description=async_example.description
        )
        self.db.add(async_example)
        await self.db.flush()
        await self.db.refresh(async_example)

        return AsyncExampleSchema.model_validate(async_example)

    @handle_exceptions
    async def read_async_example_list(self, limit, offset, keyword, sort_by=None, sort_order=None):
        if sort_by is None:
            sort_by = ['create_date']  # 기본 정렬 컬럼
        if sort_order is None:
            sort_order = ['desc']  # 기본 정렬 순서

        # 조건을 설정한다. 기본적으로 모든 데이터를 대상으로 한다.
        search_condition = True  # 모든 데이터를 반환하는 기본 조건

        if keyword:
            # 키워드가 주어진 경우 검색 조건을 추가한다.
            search_condition = or_(
                AsyncExample.name.ilike(f'%{keyword}%'),
                AsyncExample.description.ilike(f'%{keyword}%')
            )

        # 정렬 조건을 동적으로 설정
        order_by_clauses = self._create_order_by_clauses(sort_by, sort_order)

        # 검색 조건을 기반으로 쿼리를 구성한다.
        query = select(AsyncExample).where(search_condition).order_by(*order_by_clauses)

        # 쿼리 실행
        results = await self.db.execute(query.offset(offset).limit(limit))
        async_example_list = results.scalars().all()
        async_example_schema_list = [AsyncExampleSchema.model_validate(async_example) for async_example in
                                     async_example_list]

        # 전체 개수를 계산하는 쿼리를 생성한다.
        total_count_query = select(func.count()).select_from(
            select(AsyncExample).where(search_condition).subquery()
        )

        # 전체 개수 조회
        total_count = await self.db.execute(total_count_query)
        total = total_count.scalar_one()

        return ASyncExampleSchemaList(total=total, example_list=async_example_schema_list)

    @handle_exceptions
    async def read_fetch_async_example(self, async_example_id: int) -> AsyncExampleSchema:
        """
        연관 관계가 있는 경우, 한번에 모두 가져오는 쿼리를 발생시킨다.
        """
        try:
            stmt = (
                select(AsyncExample)
                .options(selectinload(AsyncExample.user))
                .where(AsyncExample.id == async_example_id)
            )
            result = await self.db.execute(stmt)
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
    async def update_async_example_v2(self, async_example_schema: AsyncExampleSchema) -> AsyncExampleSchema:
        async_example = await self.db.get(AsyncExample, async_example_schema.id)
        if async_example is None:
            logger.error(f"No AsyncExample found with id {async_example_schema.id}")
            raise ExceptionResponse(error_code=ErrorCode.NOT_FOUND,
                                    message=f"No AsyncExample found with id {async_example_schema.id}")

        async_example.name = async_example_schema.name
        async_example.description = async_example_schema.description

        await self.db.commit()
        await self.db.refresh(async_example)

        return AsyncExampleSchema.model_validate(async_example)

    @handle_exceptions
    async def delete_async_example(self, async_example_id: int):
        async_example = await self.db.get(AsyncExample, async_example_id)
        if async_example is None:
            logger.error(f"No AsyncExample found with id {async_example_id}")
            raise ExceptionResponse(error_code=ErrorCode.NOT_FOUND,
                                    message=f"No AsyncExample found with id {async_example_id}")

        await self.db.delete(async_example)
        await self.db.commit()
        logger.info(f"Deleted AsyncExample with ID {async_example_id}")

    @handle_exceptions
    async def create_related_async_example(self, related_async_example: RelatedAsyncExampleSchema):
        related_async_example = RelatedAsyncExample(
            name=related_async_example.name,
            description=related_async_example.description
        )
        self.db.add(related_async_example)
        await self.db.flush()
        await self.db.refresh(related_async_example)
        return AsyncExampleSchema.model_validate(related_async_example)

    @handle_exceptions
    async def read_fetch_related_async_example(self, related_async_example_id):
        """
        연관 관계가 있는 경우, 한번에 모두 가져오는 쿼리를 발생시킨다.
        """
        try:
            stmt = (
                select(RelatedAsyncExample)
                .options(selectinload(RelatedAsyncExample.async_example))
                .where(RelatedAsyncExample.id == related_async_example_id)
            )
            result = await self.db.execute(stmt)
            async_example = result.scalars().first()

            if async_example is None:
                logger.error(f"No AsyncExample found with id {related_async_example_id}")
                raise ExceptionResponse(error_code=ErrorCode.NOT_FOUND,
                                        message=f"No RelatedAsyncExample found with id {related_async_example_id}")

            return AsyncExampleSchema.model_validate(async_example)

        except ExceptionResponse as er:
            raise

        except Exception as e:
            logger.error(f"Error while retrieving RelatedAsyncExample {related_async_example_id}: {str(e)}")
            raise DLException(detail=f"Error while retrieving RelatedAsyncExample {related_async_example_id}")

    @handle_exceptions
    async def read_related_async_example_list(self, limit, offset, keyword):
        # 조건을 설정한다. 기본적으로 모든 데이터를 대상으로 한다.
        search_condition = True  # 모든 데이터를 반환하는 기본 조건

        if keyword:
            # 키워드가 주어진 경우 검색 조건을 추가한다.
            search_condition = or_(
                RelatedAsyncExample.name.ilike(f'%{keyword}%'),
                RelatedAsyncExample.description.ilike(f'%{keyword}%')
            )

        # 검색 조건을 기반으로 쿼리를 구성한다.
        query = select(RelatedAsyncExample).where(search_condition).order_by(RelatedAsyncExample.create_date.desc())

        # 쿼리 실행
        results = await self.db.execute(query.offset(offset).limit(limit))
        async_example_list = results.scalars().all()
        async_example_schema_list = [RelatedAsyncExample.model_validate(async_example) for async_example in
                                     async_example_list]

        # 전체 개수를 계산하는 쿼리를 생성한다.
        total_count_query = select(func.count()).select_from(
            select(RelatedAsyncExample).where(search_condition).subquery()
        )

        # 전체 개수 조회
        total_count = await self.db.execute(total_count_query)
        total = total_count.scalar_one()

        return RelatedAsyncExampleSchemaList(total=total, example_list=async_example_schema_list)

    def _create_order_by_clauses(self, sort_by, sort_order):
        order_by_clauses = []
        for column_name, direction in zip(sort_by, sort_order):
            sort_column = self._get_sort_column(model=AsyncExample, column_name=column_name)
            if direction.lower() not in ['asc', 'desc']:
                raise ValueError(f"Invalid sort direction '{direction}'. Use 'asc' or 'desc'.")
            sort_direction = desc if direction.lower() == 'desc' else asc
            order_by_clauses.append(sort_direction(sort_column))
        return order_by_clauses

    def _get_sort_column(self, model, column_name):
        # 상위 메서드로 빼야 할 듯(혹은 유틸 메서드로)
        try:
            return getattr(model, column_name)
        except AttributeError:
            raise ExceptionResponse(error_code=ErrorCode.DATABASE_ERROR,
                                    message=f"Column '{column_name}' does not exist in {model.__name__}.")
