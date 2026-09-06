"""Simple in-memory LRU cache with optional Redis backend."""
from __future__ import annotations
import time
import json
import hashlib
from collections import OrderedDict
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

# ── In-memory LRU ─────────────────────────────────────────────────────────────

class LRUCache:
    def __init__(self, maxsize: int = 128, default_ttl: int = 300):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._maxsize = maxsize
        self._default_ttl = default_ttl

    def _is_valid(self, expires_at: float) -> bool:
        return expires_at > time.monotonic()

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        value, expires_at = self._cache[key]
        if not self._is_valid(expires_at):
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl or self._default_ttl
        expires_at = time.monotonic() + ttl
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (value, expires_at)
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)

    def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()

    def stats(self) -> dict:
        return {"size": len(self._cache), "maxsize": self._maxsize}


# Global in-memory cache
_mem_cache = LRUCache(maxsize=256, default_ttl=300)

# Optional Redis client
_redis_client = None


def init_redis(url: str) -> None:
    global _redis_client
    try:
        import redis
        _redis_client = redis.from_url(url, decode_responses=True)
        _redis_client.ping()
        logger.info("Redis cache connected: %s", url)
    except Exception as exc:
        logger.warning("Redis unavailable (%s). Using in-memory cache.", exc)
        _redis_client = None


def make_key(*parts: Any) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()


def cache_get(key: str) -> Optional[Any]:
    if _redis_client:
        try:
            raw = _redis_client.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
    return _mem_cache.get(key)


def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    _mem_cache.set(key, value, ttl)
    if _redis_client:
        try:
            _redis_client.setex(key, ttl, json.dumps(value, default=str))
        except Exception:
            pass


def cache_stats() -> dict:
    stats = {"memory": _mem_cache.stats(), "redis": _redis_client is not None}
    return stats
