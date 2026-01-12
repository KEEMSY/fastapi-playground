from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.domains.standard.database.standard_async_repository import StandardAsyncRepository
from src.domains.standard.presentation.schemas.standard import DatabaseSessionInfo, PoolInfo
from src.database import get_db
from typing import Tuple

router = APIRouter()

@router.get("/database/info", response_model=Tuple[DatabaseSessionInfo, PoolInfo])
async def get_database_info(db: AsyncSession = Depends(get_db)):
    """데이터베이스 세션과 연결 풀 정보를 반환합니다."""
    try:
        repository = StandardAsyncRepository(db)
        return await repository.get_database_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 