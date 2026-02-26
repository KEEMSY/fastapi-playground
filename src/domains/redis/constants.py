"""Redis 학습 커리큘럼 상수 정의"""

# 모든 학습용 키에 사용할 공통 prefix (다른 키와 충돌 방지)
KEY_PREFIX = "redis_lab"


def make_key(*parts: str) -> str:
    """키 생성 헬퍼 함수. prefix를 자동으로 붙여준다."""
    return f"{KEY_PREFIX}:{':'.join(parts)}"


# Stage 1 - 기초 키
STAGE1_BASIC_KEY = make_key("stage1", "basic")

# Stage 2 - 자료구조 키
STAGE2_STRING_COUNTER = make_key("stage2", "string", "counter")
STAGE2_LIST_QUEUE = make_key("stage2", "list", "queue")
STAGE2_LIST_RECENT = make_key("stage2", "list", "recent")
STAGE2_SET_TAGS = make_key("stage2", "set", "tags")
STAGE2_SET_ONLINE = make_key("stage2", "set", "online_users")
STAGE2_ZSET_RANKING = make_key("stage2", "zset", "ranking")
STAGE2_HASH_USER = make_key("stage2", "hash", "user")
STAGE2_HLL_VISITORS = make_key("stage2", "hll", "visitors")

# Stage 3 - 실무 패턴 키
STAGE3_CACHE_PREFIX = make_key("stage3", "cache")
STAGE3_SESSION_PREFIX = make_key("stage3", "session")
STAGE3_BLACKLIST_PREFIX = make_key("stage3", "blacklist")
STAGE3_RATELIMIT_PREFIX = make_key("stage3", "ratelimit")
STAGE3_LOCK_PREFIX = make_key("stage3", "lock")

# Stage 5 - 성능 키
STAGE5_PIPELINE = make_key("stage5", "pipeline")
STAGE5_LUA = make_key("stage5", "lua")

# Stage 7 - 고급 키
STAGE7_STREAM = make_key("stage7", "stream")
STAGE7_TRANSACTION = make_key("stage7", "transaction")
