from fastapi import Query
from typing import Optional

from src.common.constants import APIVersion
from src.common.presentation.response import BaseErrorResponse, BaseResponse
from src.common.presentation.router import create_versioned_router
from src.domains.standard.presentation.schemas.standard import StandardResponse
from src.utils import Logging


logger = Logging.__call__().get_logger(name=__name__, path="standard.py", isThread=True)

# V2 라우터 생성
router_v2 = create_versioned_router(
    prefix="standard",
    version=APIVersion.V2,
    tags=["standard-v2"],
    responses={
        400: {"model": BaseErrorResponse.BadRequestResponse},
        404: {"model": BaseErrorResponse.NotFoundResponse},
        422: {"model": BaseErrorResponse.InvalidRequestResponse},
        500: {"model": BaseErrorResponse.ServerErrorResponse},
    }
)

@router_v2.get(
    "/test",
    response_model=BaseResponse[StandardResponse],
    summary="V2 향상된 테스트 API",
    description="""
    V2에서 개선된 사항:
    - 메시지 커스터마이징 지원
    - 다중 메시지 지원
    - 메시지 필터링 기능
    """
)
async def test_v2(
    custom_message: Optional[str] = Query(
        None,
        description="커스텀 메시지 (옵션)"
    ),
    count: Optional[int] = Query(
        1,
        ge=1,
        le=5,
        description="반환할 메시지 수 (1-5)"
    ),
    prefix: Optional[str] = Query(
        None,
        description="메시지 접두어 필터"
    )
):
    logger.info(f"Test API V2 called with message: {custom_message}, count: {count}")
    
    # 기본 메시지 리스트
    messages = [
        "Welcome to V2",
        "Enhanced Features",
        "Better Performance",
        "New Capabilities",
        "Improved API"
    ]
    
    # 커스텀 메시지가 있는 경우 첫 번째 메시지로 사용
    if custom_message:
        messages[0] = custom_message
    
    # 접두어 필터링
    if prefix:
        messages = [msg for msg in messages if msg.startswith(prefix)]
    
    # 요청된 수만큼 메시지 선택
    selected_messages = messages[:count]
    
    return BaseResponse(
        data=StandardResponse(
            message=" | ".join(selected_messages)
        ),
        metadata={
            "total_messages": len(selected_messages),
            "filtered": bool(prefix),
            "customized": bool(custom_message)
        }
    )


