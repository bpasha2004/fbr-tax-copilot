"""Distributed rate limiting with Redis, plus a safe in-memory fallback for local tests."""
import collections
import time
from typing import Optional

RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW = 60
_MEMORY: dict[str, collections.deque[float]] = {}
_redis_client = None


def _memory_check(key: str) -> bool:
    now = time.monotonic()
    dq = _MEMORY.setdefault(key, collections.deque())
    cutoff = now - RATE_LIMIT_WINDOW
    while dq and dq[0] < cutoff:
        dq.popleft()
    if len(dq) >= RATE_LIMIT_REQUESTS:
        return False
    dq.append(now)
    return True


def _redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        from config.settings import settings
        if not settings.REDIS_URL:
            return None
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception:
        return None


def check_rate_limit(identity: str, limit: Optional[int] = None, window: Optional[int] = None, fail_closed: bool = False) -> bool | None:
    limit = limit or RATE_LIMIT_REQUESTS
    window = window or RATE_LIMIT_WINDOW
    r = _redis()
    if r is None:
        return False if fail_closed else _memory_check(identity)
    try:
        bucket = int(time.time() // window)
        key = f"fbr:rl:{identity}:{bucket}"
        count = r.incr(key)
        if count == 1:
            r.expire(key, window + 2)
        return count <= limit
    except Exception:
        return False if fail_closed else _memory_check(identity)
