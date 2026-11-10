"""요청·내부 이동 기록. 두 서비스의 모든 Pod 가 Redis 스트림 하나에 쓰고 콘솔이 읽는다.

Pod 마다 메모리에 두면 콘솔이 붙은 Pod 의 것만 보인다 — 그래서 공용 저장소(Redis)에 모은다.
"""

import socket

TRACE = "trace"
HOST = socket.gethostname()
PROBES = ("/healthz", "/readyz")


async def trace(redis, svc: str, kind: str, what: str, **extra) -> None:
    if redis is None:
        return
    try:
        # ponytail: 최근 2000건만 둔다(MAXLEN ~). 오래 보관·검색이 필요하면 로그 수집기(Loki 등)로
        await redis.xadd(TRACE, {"svc": svc, "pod": HOST, "kind": kind, "what": what,
                                 **{k: str(v) for k, v in extra.items()}}, maxlen=2000, approximate=True)
    except Exception:
        pass  # 기록 실패가 요청·relay 를 깨면 안 된다


def http_kind(path: str) -> str:
    return "probe" if path in PROBES else "http"
