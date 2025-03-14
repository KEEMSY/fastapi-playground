from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.standard.presentation.schemas.standard import DatabaseSessionInfo, PoolInfo
from src.database.database import async_engine

class StandardAsyncRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_connection_pool_info(self):
        """연결 풀 정보 조회"""
        async with async_engine.connect() as conn:
            pool_status = await conn.execute(text("""
                SELECT 
                    @@max_connections as max_connections,
                    @@wait_timeout as wait_timeout,
                    (SELECT COUNT(*) FROM information_schema.PROCESSLIST) as current_connections
            """))
            return pool_status.mappings().first()
    
    async def get_session_stats(self):
        """데이터베이스 세션 통계 조회"""
        async with async_engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT 
                    COUNT(*) as total_connections,
                    SUM(CASE WHEN COMMAND != 'Sleep' THEN 1 ELSE 0 END) as active_connections
                FROM information_schema.PROCESSLIST
            """))
            return result.mappings().first()
    
    async def get_additional_stats(self):
        """추가 세션 정보 조회"""
        async with async_engine.connect() as conn:
            result = await conn.execute(text("""
                SHOW GLOBAL STATUS 
                WHERE Variable_name IN 
                ('Threads_connected', 'Threads_running', 'Max_used_connections')
            """))
            return {row[0]: row[1] for row in result}
    
    async def execute_sleep_query(self, delay):
        """지연 쿼리 실행"""
        await self.db.execute(text("SELECT SLEEP(:delay)"), {"delay": delay})
    
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