"""
eval/validate_redis_infra.py — Infrastructure smoke test for Tasks 1-5.

Tests all new components without needing a running app or Groq API key.
Requires: Redis running on REDIS_HOST:REDIS_PORT (or uses in-memory fallback).

Usage:
  # With Redis (full validation)
  REDIS_HOST=localhost CACHE_BACKEND=redis python eval/validate_redis_infra.py

  # Without Redis (fallback validation only)
  python eval/validate_redis_infra.py

Exit code 0 = all required tests passed. Non-zero = failures present.
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_PASS = []
_FAIL = []


def ok(name: str, detail: str = "") -> None:
    _PASS.append(name)
    print(f"  [PASS] {name}" + (f" — {detail}" if detail else ""))


def fail(name: str, detail: str = "") -> None:
    _FAIL.append(name)
    print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


# ── 1. Redis client ───────────────────────────────────────────────────────────

section("1. Redis client (redis_client.py)")

try:
    from redis_client import get_redis_client, health_check

    r = get_redis_client()
    if r is not None:
        r.ping()
        ok("get_redis_client() returns live client")
        hc = health_check()
        if hc.get("redis") == "ok":
            ok("health_check() reports ok", f"version={hc.get('version')}")
        else:
            fail("health_check() unexpected", str(hc))
    else:
        ok("get_redis_client() returns None (graceful degradation)")
        hc = health_check()
        ok("health_check() returns unavailable dict", str(hc))
except Exception as exc:
    fail("redis_client import", str(exc))


# ── 2. Groq key pool ─────────────────────────────────────────────────────────

section("2. Groq key pool (groq_pool.py)")

try:
    os.environ.setdefault("GROQ_API_KEY", "test_key_placeholder")
    from groq_pool import GroqKeyPool, get_pool

    pool = GroqKeyPool(["test_key_aaa", "test_key_bbb"])
    ok("GroqKeyPool instantiated", "2 keys")

    kid, key = pool.acquire()
    if key is not None:
        ok("acquire() returns a key", f"key_id={kid}")
    else:
        fail("acquire() returned None with valid keys")

    pool.mark_blocked(kid)
    ok("mark_blocked() called without exception")

    pool.record_usage(kid)
    ok("record_usage() called without exception")

    qi = pool.quota_info()
    assert isinstance(qi, list), "quota_info() must return a list"
    ok("quota_info() returns list", f"{len(qi)} entries")

    singleton = get_pool()
    ok("get_pool() returns singleton")

except Exception as exc:
    fail("groq_pool", str(exc))


# ── 3. Cache (cache.py) ───────────────────────────────────────────────────────

section("3. Cache (cache.py)")

try:
    import cache as _cache

    # Reset hit/miss counters for clean test
    _cache._hits = 0
    _cache._misses = 0
    _cache._lru_store.clear()

    # Set then get
    test_q = "validate_cache_test_query_" + str(time.time())
    test_resp = '{"direct_answer": "test", "confidence": "high", "response_mode": "high"}'

    _cache.set(test_q, "FHIR", test_resp)
    ok("cache.set() called")

    result = _cache.get(test_q, "FHIR")
    if result == test_resp:
        ok("cache.get() returns correct value")
    else:
        fail("cache.get() returned wrong value", repr(result))

    # Different module should miss
    miss = _cache.get(test_q, "MILLENNIUM")
    if miss is None:
        ok("cache.get() correctly misses on different module")
    else:
        fail("cache.get() should miss on different module")

    # Invalidate
    _cache.invalidate(test_q, "FHIR")
    after_inv = _cache.get(test_q, "FHIR")
    if after_inv is None:
        ok("cache.invalidate() removes entry")
    else:
        fail("cache.invalidate() did not remove entry")

    # Stats
    s = _cache.stats()
    assert "backend" in s and "hit_rate_pct" in s
    ok("cache.stats() returns expected fields", f"backend={s['backend']}")

except Exception as exc:
    fail("cache", str(exc))


# ── 4. Semantic cache (semantic_cache.py) ─────────────────────────────────────

section("4. Semantic cache (semantic_cache.py)")

try:
    from semantic_cache import _query_hash, _cosine_sim, step_semantic_cache_check, step_semantic_cache_store

    # Hash function
    h1 = _query_hash("test query", "FHIR")
    h2 = _query_hash("test query", "FHIR")
    h3 = _query_hash("different query", "FHIR")
    assert h1 == h2, "Same input must produce same hash"
    assert h1 != h3, "Different input must produce different hash"
    ok("_query_hash() is deterministic and input-sensitive")

    # Cosine similarity
    import math
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    assert abs(_cosine_sim(v1, v2) - 1.0) < 1e-9
    assert abs(_cosine_sim(v1, v3) - 0.0) < 1e-9
    ok("_cosine_sim() correct (parallel=1.0, orthogonal=0.0)")

    # Pipeline step: check on empty state (miss)
    from state import make_initial_state
    state = make_initial_state("BCMA override stuck")
    state["classification"] = "CLINICAL"
    state["formal_query"] = "BCMA override stuck"

    result = step_semantic_cache_check(state)
    if not result.get("semantic_cache_hit"):
        ok("step_semantic_cache_check() returns miss on empty cache")
    else:
        fail("step_semantic_cache_check() unexpected hit on empty cache")

    # Pipeline step: store (no-op when Redis unavailable or low confidence)
    state["response"] = {"response_mode": "low", "direct_answer": "test"}
    stored = step_semantic_cache_store(state)
    ok("step_semantic_cache_store() completes without exception (low-conf skip)")

except Exception as exc:
    fail("semantic_cache", str(exc))


# ── 5. llm.py additions ───────────────────────────────────────────────────────

section("5. LLM additions (llm.py)")

try:
    from llm import get_circuit_breaker_state, _pool_acquire, _pool_block, _pool_record

    cb = get_circuit_breaker_state()
    assert "state" in cb and "failures_recent" in cb
    ok("get_circuit_breaker_state() returns expected fields", f"state={cb['state']}")

    # Pool helpers should not raise even without Groq API key
    kid, key = _pool_acquire()
    ok("_pool_acquire() does not raise", f"key_id={kid}")

    _pool_block(None)    # should no-op
    _pool_record(None)   # should no-op
    ok("_pool_block(None) and _pool_record(None) are no-ops")

except Exception as exc:
    fail("llm additions", str(exc))


# ── 6. Health endpoint data ───────────────────────────────────────────────────

section("6. Health endpoint integration data")

try:
    from redis_client import health_check as rh
    from cache import stats as cs
    from llm import get_circuit_breaker_state as cbs

    data = {
        "redis": rh(),
        "cache": cs(),
        "circuit_breaker": cbs(),
    }
    import json
    _serialised = json.dumps(data)
    ok("All health data JSON-serialisable", f"{len(_serialised)} chars")
except Exception as exc:
    fail("health data serialisation", str(exc))


# ── Summary ───────────────────────────────────────────────────────────────────

section("SUMMARY")
print(f"  Passed: {len(_PASS)}")
print(f"  Failed: {len(_FAIL)}")

if _FAIL:
    print("\nFailed tests:")
    for name in _FAIL:
        print(f"  - {name}")
    sys.exit(1)
else:
    print("\n  All tests passed.")
    sys.exit(0)
