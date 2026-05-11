"""
redis_client.py — Shared Redis connection pool for Cerna.

All Redis access across tasks (cache, quota tracking, semantic cache) goes
through get_redis_client(). Returns a connected StrictRedis instance or None
if Redis is unreachable. Callers must handle None — never raise on absence.

Connection is attempted once at first call. If it fails, the module stays
None for the process lifetime; restart the app if Redis recovers.

Environment variables:
    REDIS_HOST  (default: localhost)
    REDIS_PORT  (default: 6379)
    REDIS_DB    (default: 0)
"""

from __future__ import annotations

import logging
import os
from typing import Optional

_logger = logging.getLogger(__name__)

_REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
_REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
_REDIS_DB:   int = int(os.getenv("REDIS_DB", "0"))

_pool = None
_pool_tried: bool = False


def _init_pool() -> bool:
    global _pool, _pool_tried
    if _pool_tried:
        return _pool is not None
    _pool_tried = True
    try:
        import redis as _redis
        _pool = _redis.ConnectionPool(
            host=_REDIS_HOST,
            port=_REDIS_PORT,
            db=_REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            max_connections=20,
        )
        # Verify the pool can actually reach the server before returning True.
        _redis.StrictRedis(connection_pool=_pool).ping()
        _logger.info(
            "[Redis] Connected — %s:%s db=%s", _REDIS_HOST, _REDIS_PORT, _REDIS_DB
        )
        return True
    except Exception as exc:
        _logger.warning(
            "[Redis] Unavailable (%s). Falling back to in-memory cache.", exc
        )
        _pool = None
        return False


def get_redis_client():
    """Return a StrictRedis client (shared pool) or None if Redis is unavailable."""
    if not _init_pool():
        return None
    import redis
    return redis.StrictRedis(connection_pool=_pool)


def health_check() -> dict:
    """Return a Redis connectivity status dict for the health and admin endpoints."""
    r = get_redis_client()
    if r is None:
        return {
            "redis":  "unavailable",
            "host":   _REDIS_HOST,
            "port":   _REDIS_PORT,
        }
    try:
        r.ping()
        info = r.info("server")
        return {
            "redis":   "ok",
            "host":    _REDIS_HOST,
            "port":    _REDIS_PORT,
            "version": info.get("redis_version", "unknown"),
        }
    except Exception as exc:
        return {"redis": "error", "error": str(exc)}
