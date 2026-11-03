"""
Redis 학습 커리큘럼 — 메인 라우터

모든 단계별 라우터를 하나의 prefix 아래로 통합한다.
최종 경로: /api/v1/redis/{stage}/{endpoint}

커리큘럼 구성:
  1단계: 기초 이해       (/api/v1/redis/stage1/...)
  2단계: 핵심 자료구조   (/api/v1/redis/stage2/...)
  3단계: 실무 패턴       (/api/v1/redis/stage3/...)
  4단계: 영속성&메모리   (/api/v1/redis/stage4/...)
  5단계: 성능 최적화     (/api/v1/redis/stage5/...)
  7단계: 고급 주제       (/api/v1/redis/stage7/...)

※ 6단계(고가용성: Sentinel/Cluster)는 Docker 멀티 컨테이너 환경이
  필요하므로 별도 인프라 설정 후 실습 권장.
  docker-compose-monitoring.yml 참고.
"""

from fastapi import APIRouter

from src.domains.redis.presentation.stage1_basics_router import router as stage1_router
from src.domains.redis.presentation.stage2_data_structures_router import router as stage2_router
from src.domains.redis.presentation.stage3_patterns_router import router as stage3_router
from src.domains.redis.presentation.stage4_persistence_router import router as stage4_router
from src.domains.redis.presentation.stage5_performance_router import router as stage5_router
from src.domains.redis.presentation.stage7_advanced_router import router as stage7_router

# 공통 prefix: /api/v1/redis
router = APIRouter(prefix="/api/v1/redis")

router.include_router(stage1_router)
router.include_router(stage2_router)
router.include_router(stage3_router)
router.include_router(stage4_router)
router.include_router(stage5_router)
router.include_router(stage7_router)
