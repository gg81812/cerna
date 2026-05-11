"""
groq_pool.py — Multi-key Groq API pool with Redis-backed quota tracking.

Key selection strategy:
  1. Skip keys with a groq_blocked:<key_id> Redis flag (set on 429, 60s TTL).
  2. Skip keys at or above GROQ_QUOTA_THRESHOLD requests today.
  3. Among eligible keys, pick the one with the lowest request count today.
  4. If no key is eligible, return (None, None) — caller degrades gracefully.

Redis key scheme:
  groq_quota:<key_id>:<YYYY-MM-DD>   →  integer request count (25h TTL)
  groq_blocked:<key_id>              →  "1" (60s TTL, written on 429)

When Redis is unavailable, falls back to in-memory counters so that multiple
keys still rotate under load rather than always selecting the first key.

Environment variables:
  GROQ_API_KEYS              comma-separated list of Groq API keys
  GROQ_API_KEY               single key (fallback if GROQ_API_KEYS not set)
  GROQ_DAILY_REQUEST_LIMIT   per-key daily request limit (default: 100)
"""

from __future__ import annotations

import hashlib
import os
import time
from datetime import date
from typing import Optional

# In-memory fallback quota state (used when Redis is unavailable).
# Resets each process lifetime — accurate enough for key rotation without Redis.
_mem_usage:   dict[str, int]   = {}   # key_id -> request count this session
_mem_blocked: dict[str, float] = {}   # key_id -> unblock epoch (time.time())

# Parse key list from env: multi-key takes priority over single-key.
_raw = os.getenv("GROQ_API_KEYS", os.getenv("GROQ_API_KEY", ""))
_API_KEYS: list[str] = [k.strip() for k in _raw.split(",") if k.strip()]

_DAILY_LIMIT: int = int(os.getenv("GROQ_DAILY_REQUEST_LIMIT", "100"))
_QUOTA_THRESHOLD: int = int(_DAILY_LIMIT * 0.95)   # skip key when ≥ 95% full
_BLOCK_TTL_SECONDS: int = 60                         # 429 cooldown per key
_QUOTA_TTL_SECONDS: int = 25 * 3600                 # 25h — spans midnight safely


def _key_id(api_key: str) -> str:
    """Short opaque identifier derived from the key — never log the key itself."""
    return "k" + hashlib.sha256(api_key.encode()).hexdigest()[:8]


def _quota_redis_key(kid: str) -> str:
    return f"groq_quota:{kid}:{date.today().isoformat()}"


def _blocked_redis_key(kid: str) -> str:
    return f"groq_blocked:{kid}"


class GroqKeyPool:
    """Thread-safe multi-key Groq pool backed by a shared Redis connection pool."""

    def __init__(self, api_keys: list[str]) -> None:
        if not api_keys:
            raise ValueError("GroqKeyPool requires at least one API key.")
        self._entries: list[tuple[str, str]] = [(_key_id(k), k) for k in api_keys]

    # ── Public interface ─────────────────────────────────────────────────────

    def acquire(self) -> tuple[Optional[str], Optional[str]]:
        """
        Return (key_id, api_key) for the lowest-quota eligible key.
        Returns (None, None) if every key is blocked or over quota.
        """
        from redis_client import get_redis_client
        r = get_redis_client()
        now = time.time()

        candidates: list[tuple[int, str, str]] = []
        for kid, api_key in self._entries:
            if r:
                try:
                    if r.exists(_blocked_redis_key(kid)):
                        continue
                    quota = int(r.get(_quota_redis_key(kid)) or 0)
                except Exception:
                    quota = _mem_usage.get(kid, 0)
            else:
                # In-memory fallback: honour per-key 429 blocks and usage counts
                if _mem_blocked.get(kid, 0) > now:
                    continue
                quota = _mem_usage.get(kid, 0)

            if quota >= _QUOTA_THRESHOLD:
                continue
            candidates.append((quota, kid, api_key))

        if not candidates:
            return None, None

        candidates.sort()
        _, kid, api_key = candidates[0]
        return kid, api_key

    def mark_blocked(self, key_id: str) -> None:
        """Mark key as 429-blocked for _BLOCK_TTL_SECONDS seconds."""
        from redis_client import get_redis_client
        r = get_redis_client()
        if r:
            try:
                r.setex(_blocked_redis_key(key_id), _BLOCK_TTL_SECONDS, "1")
            except Exception:
                pass
        _mem_blocked[key_id] = time.time() + _BLOCK_TTL_SECONDS

    def record_usage(self, key_id: str) -> None:
        """Increment today's request counter for key_id (pipeline for atomicity)."""
        from redis_client import get_redis_client
        r = get_redis_client()
        if r:
            try:
                qkey = _quota_redis_key(key_id)
                pipe = r.pipeline()
                pipe.incr(qkey)
                pipe.expire(qkey, _QUOTA_TTL_SECONDS)
                pipe.execute()
            except Exception:
                pass
        _mem_usage[key_id] = _mem_usage.get(key_id, 0) + 1

    def quota_info(self) -> list[dict]:
        """Return per-key quota snapshot for the admin/health endpoints."""
        from redis_client import get_redis_client
        r = get_redis_client()
        result = []
        for kid, _ in self._entries:
            requests_today = 0
            blocked = False
            blocked_ttl = 0
            if r:
                try:
                    requests_today = int(r.get(_quota_redis_key(kid)) or 0)
                    blocked = bool(r.exists(_blocked_redis_key(kid)))
                    blocked_ttl = max(0, r.ttl(_blocked_redis_key(kid))) if blocked else 0
                except Exception:
                    pass
            result.append({
                "key_id":         kid,
                "requests_today": requests_today,
                "daily_limit":    _DAILY_LIMIT,
                "pct_used":       round(requests_today / _DAILY_LIMIT * 100, 1),
                "blocked":        blocked,
                "blocked_ttl_s":  blocked_ttl,
            })
        return result


# ── Module-level singleton ────────────────────────────────────────────────────

_pool: Optional[GroqKeyPool] = None


def get_pool() -> GroqKeyPool:
    """Return the module-level GroqKeyPool singleton (created on first call)."""
    global _pool
    if _pool is None:
        _pool = GroqKeyPool(_API_KEYS)
    return _pool
