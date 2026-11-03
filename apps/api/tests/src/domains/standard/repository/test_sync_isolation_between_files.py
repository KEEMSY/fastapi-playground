import pytest
from sqlalchemy import text
from uuid import uuid4

@pytest.mark.repository
@pytest.mark.sync_test
def test_independent_table(db_session):
    """다른 테스트 파일의 영향을 받지 않는 독립적인 테이블 테스트"""
    # 새로운 독립적인 테이블 생성
    db_session.execute(
        text("CREATE TABLE IF NOT EXISTS another_sync_test_table (id TEXT PRIMARY KEY, value TEXT)")
    )
    
    # 데이터 삽입
    test_id = str(uuid4())
    db_session.execute(
        text("INSERT INTO another_sync_test_table (id, value) VALUES (:id, :value)"),
        {"id": test_id, "value": "independent_test"}
    )
    db_session.commit()

    # 이전 테스트 파일의 테이블 상태 확인
    result = db_session.execute(
        text("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_name = 'test_sync_isolation'
            )
        """)
    )
    table_exists = result.scalar()
    
    if table_exists:
        result = db_session.execute(
            text("SELECT COUNT(*) FROM test_sync_isolation")
        )
        count = result.scalar()
        assert count == 0, "다른 테스트 파일의 테이블이 비어있어야 함"