from sqlalchemy import text
from sqlalchemy.orm import Session
from src.domains.standard.presentation.schemas.standard import DatabaseSessionInfo, PoolInfo

class StandardRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_connection_pool_info(self):
        """연결 풀 정보 조회"""
        pool_status = self.db.execute(text("""
            SELECT 
                current_setting('max_connections')::int as max_connections,
                current_setting('idle_in_transaction_session_timeout')::int / 1000 as wait_timeout,
                (SELECT count(*) FROM pg_stat_activity) as current_connections
        """))
        return pool_status.mappings().first()
    
    def get_session_stats(self):
        """데이터베이스 세션 통계 조회"""
        result = self.db.execute(text("""
            SELECT 
                count(*) as total_connections,
                count(*) FILTER (WHERE state = 'active') as active_connections
            FROM pg_stat_activity
        """))
        return result.mappings().first()
    
    def get_additional_stats(self):
        """추가 세션 정보 조회"""
        result = self.db.execute(text("""
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
        return {row.name: row.value for row in result}
    
    def get_database_connection_info(self):
        """데이터베이스 연결 정보 조회"""
        result = self.db.execute(text("""
            SELECT 
                current_database() as database_name,
                current_user as user,
                inet_server_addr() as host,
                inet_server_port() as port
        """))
        return result.mappings().first()
    
    def execute_sleep_query(self, delay):
        """지연 쿼리 실행"""
        self.db.execute(text("SELECT pg_sleep(:delay)"), {"delay": delay})
    
    def get_database_info(self):
        """모든 데이터베이스 정보 통합 조회"""
        pool_info_data = self.get_connection_pool_info()
        db_stats = self.get_session_stats()
        additional_stats = self.get_additional_stats()
        db_conn_info = self.get_database_connection_info()
        
        session_info = DatabaseSessionInfo(
            database_name=db_conn_info["database_name"],
            user=db_conn_info["user"],
            host=db_conn_info["host"],
            port=db_conn_info["port"],
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