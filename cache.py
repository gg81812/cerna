"""
cache.py — Query-level caching for Cerna.

Backend selection (CACHE_BACKEND env var):
  redis   — Use Redis via shared redis_client pool; falls back to in-memory LRU
             if Redis is unreachable at startup.
  memory  — In-process LRU only (default; safe for single-process Streamlit).

Cache key scheme:
  response_cache:<PROMPT_VERSION>:<sha256(masked_query | module | model | collection)>

Including PROMPT_VERSION in the key prefix means changing PROMPT_VERSION in
config.py automatically invalidates all previous cache entries without any
manual flush — old keys become unreachable orphans that expire via TTL.

PII safety: the query is masked via pii_guard.mask_pii() before hashing.
The SHA-256 digest never contains PII; only the hash is stored in Redis.

TTL: configurable via RESPONSE_CACHE_TTL (default 3600s = 1 hour).
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Optional

from config import ACTIVE_COLLECTION, GROQ_MODEL, PROMPT_VERSION

_CACHE_BACKEND: str = os.getenv("CACHE_BACKEND", "memory").lower()
_TTL_SECONDS: int = int(os.getenv("RESPONSE_CACHE_TTL", "3600"))

_lru_store: dict[str, str] = {}
_LRU_MAX = 512
_hits: int = 0
_misses: int = 0


def _get_redis():
    """Return Redis client if backend is redis and connection is available."""
    if _CACHE_BACKEND != "redis":
        return None
    try:
        from redis_client import get_redis_client
        return get_redis_client()
    except Exception:
        return None


def _make_key(query: str, module: Optional[str]) -> str:
    try:
        from pii_guard import mask_pii
        safe_query = mask_pii(query.strip().lower())
    except Exception:
        safe_query = query.strip().lower()

    raw = json.dumps({
        "q":      safe_query,
        "module": module or "all",
        "model":  GROQ_MODEL,
        "coll":   ACTIVE_COLLECTION,
    }, sort_keys=True)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"response_cache:{PROMPT_VERSION}:{digest}"


def get(query: str, module: Optional[str] = None) -> Optional[str]:
    """Return cached JSON response string or None on cache miss."""
    global _hits, _misses
    key = _make_key(query, module)
    r = _get_redis()
    if r:
        try:
            val = r.get(key)
            if val is not None:
                _hits += 1
                return val
        except Exception:
            pass

    val = _lru_store.get(key)
    if val is not None:
        _hits += 1
    else:
        _misses += 1
    return val


def set(query: str, module: Optional[str], response_json: str) -> bool:
    """Cache a JSON response string. Returns True on success."""
    key = _make_key(query, module)
    r = _get_redis()
    if r:
        try:
            r.setex(key, _TTL_SECONDS, response_json)
            return True
        except Exception:
            pass

    if len(_lru_store) >= _LRU_MAX:
        oldest = next(iter(_lru_store))
        del _lru_store[oldest]
    _lru_store[key] = response_json
    return True


def invalidate(query: str, module: Optional[str] = None) -> None:
    """Remove a specific cache entry."""
    key = _make_key(query, module)
    r = _get_redis()
    if r:
        try:
            r.delete(key)
        except Exception:
            pass
    _lru_store.pop(key, None)


def stats() -> dict:
    """Return cache stats for admin and health endpoints."""
    r = _get_redis()
    backend = "redis" if r else ("memory(fallback)" if _CACHE_BACKEND == "redis" else "memory")
    total = _hits + _misses
    return {
        "backend":          backend,
        "cache_backend_cfg": _CACHE_BACKEND,
        "ttl_seconds":      _TTL_SECONDS,
        "hits":             _hits,
        "misses":           _misses,
        "hit_rate_pct":     round(_hits / total * 100, 1) if total else 0.0,
        "in_memory_entries": len(_lru_store),
        "lru_max":          _LRU_MAX,
    }
