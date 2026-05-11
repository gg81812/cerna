# Multi-Key Groq Pool — Implementation Notes

**Task:** 2 of 6  
**Date:** 2026-05-04  
**Status:** Complete

---

## Problem

Groq free tier limits: ~100k tokens/day per key (conservative per-key budget used here), 6k TPM, 30 RPM. A 55-query eval run at 3s delay regularly exhausts one key and opens the circuit breaker, causing ~3 rate-limit windows of 120s each.

Multi-key pool distributes requests across keys, selecting whichever key has the most remaining quota. Keys that return 429 are parked for 60 seconds before being tried again.

---

## Files Changed

| File | Change |
|------|--------|
| [groq_pool.py](../groq_pool.py) | New — GroqKeyPool class, Redis quota counters |
| [llm.py](../llm.py) | Modified — pool key selection in `safe_invoke_json`, per-key 429 blocking in `_invoke_with_backoff` |

### No changes to
- `pipeline.py` — no Groq key knowledge
- `orchestrator.py` — no Groq key knowledge
- `config.py` — GROQ_API_KEY validation unchanged; pool reads its own env vars
- `safety.py`, `query_rewriter.py` — use `get_llm_fast()` which uses GROQ_API_KEY directly (single-key path; acceptable — these calls are cheap and infrequent)

---

## Architecture

```
safe_invoke_json(llm, messages)
    │
    ├─ _pool_acquire()                    ← groq_pool.get_pool().acquire()
    │       ├─ Redis: check groq_blocked:<key_id>  (skip if exists)
    │       ├─ Redis: check groq_quota:<key_id>:<date> (skip if ≥ 95%)
    │       └─ return (key_id, api_key)  for lowest-usage eligible key
    │
    ├─ _llm_with_key(llm, pool_key)       ← clone ChatGroq with selected key
    │
    ├─ _invoke_with_backoff(llm, ..., key_id)
    │       ├─ llm.invoke() attempt 1
    │       │       on 429 → _pool_block(key_id)  [sets groq_blocked, 60s TTL]
    │       │               + _cb_record_failure() [existing circuit breaker]
    │       ├─ sleep 1s → attempt 2
    │       ├─ sleep 3s → attempt 3
    │       └─ return None on final failure
    │
    ├─ on success → _pool_record(key_id)  ← INCR groq_quota, EXPIRE 25h
    │
    └─ 8B fallback → _pool_acquire() again (may pick different key)
             on 429 → _pool_block(fb_key_id)
```

### Circuit breaker vs per-key blocking

These are independent and composing:

| Mechanism | Scope | Trigger | Duration | Effect |
|-----------|-------|---------|----------|--------|
| Circuit breaker | All keys | 5 failures in 60s | 120s | Skip all Groq calls; go to graceful fallback |
| Per-key blocking | Single key | Any 429 on that key | 60s | Pool picks a different key on next call |

If Key A gets 429: Key A is blocked for 60s, Key B is used next. Circuit breaker is also incremented — if both keys get 429 repeatedly, the circuit opens and all calls stop for 120s. This is correct behavior.

---

## Redis Key Scheme

| Key | Type | Value | TTL | Set by |
|-----|------|-------|-----|--------|
| `groq_quota:<kid>:<YYYY-MM-DD>` | string (int) | request count | 25h | `record_usage()` on success |
| `groq_blocked:<kid>` | string | "1" | 60s | `mark_blocked()` on 429 |

`<kid>` is the first 8 hex chars of SHA-256 of the raw API key — never the key itself.

25h TTL (not 24h) ensures the counter survives midnight UTC rollovers on a busy day without resetting mid-session.

---

## Key Selection Logic (`acquire()`)

```python
for key_id, api_key in self._entries:
    if blocked(key_id):   continue        # 429 cooldown
    if quota >= 95% limit: continue       # daily budget exhausted
    candidates.append((quota, key_id, api_key))

candidates.sort()                          # lowest quota first
return candidates[0]
```

When Redis is unavailable: `blocked()` always False, `quota` always 0 → all keys return as "available", first key is returned. Effectively single-key mode — correct degradation.

---

## Environment Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `GROQ_API_KEYS` | *(not set)* | Comma-separated keys: `key1,key2,key3` |
| `GROQ_API_KEY` | *(required)* | Used as fallback if `GROQ_API_KEYS` not set |
| `GROQ_DAILY_REQUEST_LIMIT` | `100` | Per-key daily request cap (~100k tokens at ~1k avg/request) |

If neither `GROQ_API_KEYS` nor `GROQ_API_KEY` is set, `GroqKeyPool.__init__` raises `ValueError` at startup. The existing `config.py` `EnvironmentError` check for `GROQ_API_KEY` still fires before `groq_pool.py` is ever imported, so the startup failure message is unchanged.

---

## What Is Not Changed

- `get_llm()`, `get_llm_fast()`, `get_llm_fast_json()` — still use `GROQ_API_KEY` directly. These are used by `query_rewriter.py` and `safety.py` (fast model, cheap calls). Bringing these under pool control is a future enhancement; it's not needed for the demo.
- `_invoke_with_backoff()` signature adds `key_id=None` but all existing call sites work without it (default None = no pool tracking, no per-key blocking).
- Circuit breaker state, thresholds, and logic: **unchanged**.

---

## Backward Compatibility

Single-key deployments (only `GROQ_API_KEY` set):
1. `_pool_acquire()` calls `get_pool().acquire()` → pool has one entry → returns `(kid, GROQ_API_KEY)` if not blocked/exhausted
2. `_llm_with_key(llm, GROQ_API_KEY)` creates a ChatGroq identical to the input
3. All paths behave identically to pre-Task-2 code

Zero behavior change for single-key users.

---

## Known Gaps (acceptable for sprint scope)

1. `get_llm_fast()` (used by classify, rewrite, safety) still uses `GROQ_API_KEY` directly — fast model calls are cheap and infrequent enough that this doesn't meaningfully affect quota distribution.
2. Quota tracking is by request count, not token count. At ~1k avg tokens/request, 100 requests ≈ 100k tokens. This is a conservative estimate that may leave unused quota on complex multi-turn queries.
3. The pool singleton is process-level. Under Streamlit's multi-worker mode (if launched with `--server.workers N`), each worker has its own pool instance — Redis counters are still correct (INCR is atomic), but the in-process `_pool_tried` state is independent per worker. Acceptable for demo scale.

---

*Last updated: 2026-05-04 — Task 2 complete*
