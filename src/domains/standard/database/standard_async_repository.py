from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.standard.presentation.schemas.standard import DatabaseSessionInfo, PoolInfo
from typing import Tuple
from sqlalchemy.exc import SQLAlchemyError

class StandardAsyncRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_connection_pool_info(self):
        """연결 풀 정보 조회"""
        result = await self.db.execute(text("""
            SELECT 
                current_setting('max_connections')::int as max_connections,
                current_setting('idle_in_transaction_session_timeout')::int / 1000 as wait_timeout,
                (SELECT count(*) FROM pg_stat_activity) as current_connections
        """))
        return result.mappings().first()
    
    async def get_session_stats(self):
        """데이터베이스 세션 통계 조회"""
        result = await self.db.execute(text("""
            SELECT 
                count(*) as total_connections,
                count(*) FILTER (WHERE state = 'active') as active_connections
            FROM pg_stat_activity
        """))
        return result.mappings().first()
    
    async def get_additional_stats(self):
        """추가 세션 정보 조회"""
        result = await self.db.execute(text("""
            SELECT 
                'Threads_connected' as name, 
                (SELECT count(*) FROM pg_stat_activity)::text as value 
            UNION ALL
            SELECT 
                'Threads_running' as name, 
                (SELECT count(*) FROM pg_stat_activity WHERE state = 'active')::text as value
            UNION ALL
            SELECT 
                'Max_used_connections' as name,
                (SELECT current_setting('max_connections')::text) as value
        """))
        return {row.name: str(row.value) for row in result}
    
    async def execute_sleep_query(self, delay):
        """지연 쿼리 실행"""
        await self.db.execute(text("SELECT pg_sleep(:delay)"), {"delay": delay})
    
    async def get_database_info(self) -> Tuple[DatabaseSessionInfo, PoolInfo]:
        """데이터베이스 세션과 연결 풀 정보를 반환합니다."""
        try:
            # 현재 데이터베이스 연결 정보 조회
            result = await self.db.execute(text("SELECT current_database(), current_user, inet_server_addr(), inet_server_port()"))
            db_info = result.fetchone()
            
            # 세션 통계 조회
            stats_result = await self.db.execute(text("""
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections
                FROM pg_stat_activity
            """))
            stats = stats_result.mappings().first()
            
            # 추가 통계 조회
            additional_stats_result = await self.db.execute(text("""
                SELECT 
                    'Threads_connected' as name, 
                    (SELECT count(*) FROM pg_stat_activity)::text as value 
                UNION ALL
                SELECT 
                    'Threads_running' as name, 
                    (SELECT count(*) FROM pg_stat_activity WHERE state = 'active')::text as value
                UNION ALL
                SELECT 
                    'Max_used_connections' as name,
                    (SELECT current_setting('max_connections')::text) as value
            """))
            additional_stats = {row.name: str(row.value) for row in additional_stats_result}
            
            # 연결 풀 정보 조회
            pool_info_result = await self.db.execute(text("""
                SELECT 
                    current_setting('max_connections')::int as max_connections,
                    current_setting('idle_in_transaction_session_timeout')::int / 1000 as wait_timeout,
                    (SELECT count(*) FROM pg_stat_activity) as current_connections
                FROM pg_stat_activity
            """))
            pool_info_data = pool_info_result.mappings().first()
            
            # 연결 풀 정보 생성
            pool_info = PoolInfo(
                max_connections=int(pool_info_data['max_connections']),
                current_connections=int(pool_info_data['current_connections']),
                available_connections=int(pool_info_data['max_connections']) - int(pool_info_data['current_connections']),
                wait_timeout=int(pool_info_data['wait_timeout'])
            )
            
            # 세션 정보 생성
            session_info = DatabaseSessionInfo(
                database_name=db_info[0],
                user=db_info[1],
                host=str(db_info[2]),  # IPv4Address를 문자열로 변환
                port=db_info[3],
                total_connections=stats['total_connections'],
                active_connections=stats['active_connections'],
                threads_connected=additional_stats.get('Threads_connected', '0'),
                threads_running=additional_stats.get('Threads_running', '0'),
                max_used_connections=additional_stats.get('Max_used_connections', '0'),
                max_connections=int(pool_info_data['max_connections']),
                current_connections=int(pool_info_data['current_connections']),
                available_connections=int(pool_info_data['max_connections']) - int(pool_info_data['current_connections']),
                wait_timeout=int(pool_info_data['wait_timeout'])
            )
            
            return session_info, pool_info
        except SQLAlchemyError as e:
            # 데이터베이스 연결 오류 처리
            raise Exception(f"데이터베이스 연결 오류: {str(e)}")