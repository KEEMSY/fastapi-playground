"""Redis 학습 커리큘럼 공통 스키마"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────
# 공통 응답 래퍼
# ──────────────────────────────────────────

class RedisLabResponse(BaseModel):
    """Redis 학습용 공통 응답 형식"""
    stage: str = Field(description="커리큘럼 단계")
    topic: str = Field(description="학습 주제")
    description: str = Field(description="개념 설명")
    commands_used: List[str] = Field(default=[], description="사용된 Redis 명령어")
    result: Any = Field(default=None, description="실행 결과")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="추가 정보")


# ──────────────────────────────────────────
# Stage 1 - 기초
# ──────────────────────────────────────────

class SetKeyRequest(BaseModel):
    key: str = Field(description="저장할 키")
    value: str = Field(description="저장할 값")
    ttl: Optional[int] = Field(default=None, description="만료 시간(초). 없으면 영구 저장")


class GetKeyRequest(BaseModel):
    key: str = Field(description="조회할 키")


# ──────────────────────────────────────────
# Stage 2 - 자료구조
# ──────────────────────────────────────────

class ListPushRequest(BaseModel):
    value: str = Field(description="큐에 추가할 값")


class SetAddRequest(BaseModel):
    member: str = Field(description="Set에 추가할 멤버")


class ZSetAddRequest(BaseModel):
    member: str = Field(description="Sorted Set에 추가할 멤버")
    score: float = Field(description="멤버의 점수")


class HashSetRequest(BaseModel):
    field: str = Field(description="Hash 필드명")
    value: str = Field(description="Hash 필드 값")


class HyperLogLogAddRequest(BaseModel):
    user_id: str = Field(description="방문자 ID (유니크 방문자 추적용)")


# ──────────────────────────────────────────
# Stage 3 - 실무 패턴
# ──────────────────────────────────────────

class CacheQueryRequest(BaseModel):
    resource_id: int = Field(description="조회할 리소스 ID (캐시 히트/미스 시뮬레이션)")


class SessionCreateRequest(BaseModel):
    user_id: str = Field(description="세션을 생성할 사용자 ID")
    data: Dict[str, str] = Field(
        default={"role": "user", "theme": "dark"},
        description="세션에 저장할 데이터",
    )


class TokenBlacklistRequest(BaseModel):
    token: str = Field(description="블랙리스트에 등록할 JWT 토큰 (또는 jti)")
    ttl: int = Field(default=3600, description="토큰 만료까지 남은 시간(초)")


class RateLimitRequest(BaseModel):
    client_id: str = Field(description="요청 클라이언트 ID")
    limit: int = Field(default=5, description="허용 요청 수")
    window: int = Field(default=60, description="슬라이딩 윈도우 크기(초)")


class DistributedLockRequest(BaseModel):
    resource: str = Field(description="잠글 리소스 이름")
    ttl: int = Field(default=5, description="락 만료 시간(초)")


# ──────────────────────────────────────────
# Stage 5 - 성능 최적화
# ──────────────────────────────────────────

class PipelineRequest(BaseModel):
    count: int = Field(default=100, ge=1, le=1000, description="파이프라인으로 처리할 명령어 수")


# ──────────────────────────────────────────
# Stage 7 - 고급
# ──────────────────────────────────────────

class StreamPublishRequest(BaseModel):
    event_type: str = Field(description="이벤트 타입 (예: user.signup, order.created)")
    payload: Dict[str, str] = Field(description="이벤트 데이터")


class TransactionRequest(BaseModel):
    key: str = Field(description="트랜잭션으로 증가시킬 카운터 키")
