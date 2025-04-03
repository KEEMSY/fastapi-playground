from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.standard.presentation.schemas.standard import DatabaseSessionInfo, PoolInfo

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
    
    async def get_database_info(self):
        """모든 데이터베이스 정보 통합 조회"""
        pool_info_data = await self.get_connection_pool_info()
        db_stats = await self.get_session_stats()
        additional_stats = await self.get_additional_stats()
        
        session_info = DatabaseSessionInfo(
            total_connections=db_stats["total_connections"],
            active_connections=db_stats["active_connections"],
            threads_connected=additional_stats.get("Threads_connected", "0"),
            threads_running=additional_stats.get("Threads_running", "0"),
            max_used_connections=additional_stats.get("Max_used_connections", "0"),
            max_connections=int(pool_info_data['max_connections']),
            current_connections=int(pool_info_data['current_connections']),
            available_connections=int(pool_info_data['max_connections']) - int(pool_info_data['current_connections']),
            wait_timeout=int(pool_info_data['wait_timeout'])
        )
        
        pool_info = PoolInfo(
            max_connections=int(pool_info_data['max_connections']),
            current_connections=int(pool_info_data['current_connections']),
            available_connections=int(pool_info_data['max_connections']) - int(pool_info_data['current_connections']),
            wait_timeout=int(pool_info_data['wait_timeout'])
        )
        
        return session_info, pool_info