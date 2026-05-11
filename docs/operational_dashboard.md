# Operational Dashboard — Implementation Notes

**Task:** 5 of 6  
**Date:** 2026-05-04  
**Status:** Complete

---

## Endpoints

### `?health=1` — Machine-readable health JSON

Extended from the original `{status, version, chroma_dir_exists, chunk_total}` to include:

```json
{
  "status": "ok",
  "version": "1.3.0",
  "chroma_dir_exists": true,
  "chunk_total": 1322,
  "redis": {
    "redis": "ok",
    "host": "localhost",
    "port": 6379,
    "version": "7.2.4"
  },
  "cache": {
    "backend": "redis",
    "cache_backend_cfg": "redis",
    "ttl_seconds": 3600,
    "hits": 42,
    "misses": 18,
    "hit_rate_pct": 70.0,
    "in_memory_entries": 0,
    "lru_max": 512
  },
  "circuit_breaker": {
    "state": "closed",
    "failures_recent": 0,
    "failure_threshold": 5,
    "open_until_epoch": null,
    "seconds_until_close": 0
  },
  "groq_keys": [
    {
      "key_id": "ka1b2c3d",
      "requests_today": 23,
      "daily_limit": 100,
      "pct_used": 23.0,
      "blocked": false,
      "blocked_ttl_s": 0
    }
  ]
}
```

**When to use:** Uptime monitors, CI health gates, load balancer probes.

### `?admin=1` — Original admin panel

Unchanged: shows cache stats + recent query log.

### `?admin=1&view=quota` — Quota dashboard (new)

Human-readable Streamlit page showing:
- Redis connectivity status
- Cache hit rate and backend
- Circuit breaker state (OPEN/CLOSED, recent failure count, seconds until close)
- Per-key Groq quota table (key ID, requests today, % used, blocked status)
- Bar chart of today's request counts per key

**Access:** `http://localhost:8501/?admin=1&view=quota`

---

## Circuit Breaker States

| State | Meaning | User impact |
|-------|---------|------------|
| `closed` | Normal — all Groq calls proceed | None |
| `open` | ≥5 failures in 60s — all Groq calls skipped | `final_fallback` responses for `seconds_until_close` seconds |

The circuit breaker auto-closes after 120s and clears its failure history. The dashboard shows `seconds_until_close` to let operators know how long the outage will last.

---

## Groq Key Quota Table

| Column | Source | Notes |
|--------|--------|-------|
| Key ID | SHA-256 prefix of raw key | Opaque — never logs the actual key |
| Requests Today | `groq_quota:<kid>:<date>` Redis counter | INCR on each successful call |
| Daily Limit | `GROQ_DAILY_REQUEST_LIMIT` env var (default 100) | Configurable |
| % Used | requests_today / daily_limit × 100 | |
| Blocked | `groq_blocked:<kid>` exists in Redis | True for 60s after a 429 |
| Blocked TTL (s) | Redis TTL on the blocked key | Countdown to recovery |

Keys at ≥95% of limit are skipped by the pool but still appear in the table. This lets operators see when a key is approaching exhaustion and add more keys.

---

## When Redis Is Unavailable

All three dashboards degrade gracefully:

| Field | Redis available | Redis unavailable |
|-------|----------------|-------------------|
| `health.redis` | `{"redis": "ok", ...}` | `{"redis": "unavailable"}` |
| `health.groq_keys` | Per-key quota data | Empty list `[]` |
| Quota dashboard | Full table + chart | "No quota data available" info box |

The health endpoint always returns `status: ok` or `status: degraded` based on ChromaDB state, not Redis state. Redis unavailability is reflected in the `redis` sub-field but does not change the overall status (the app continues working with in-memory cache).

---

## Implementation Notes

### get_circuit_breaker_state() (llm.py)

Added before the circuit breaker state variables (safe: Python function bodies resolve module globals at call time, not definition time). Takes `_CB_LOCK` to ensure a consistent read of `_cb_failures` and `_cb_open_until`.

### Quota admin view (app.py)

Uses `pandas.DataFrame` for the quota table — pandas is transitively installed via sentence-transformers. Uses `st.bar_chart` for the usage chart. Calls `st.stop()` to prevent the main chat UI from rendering.

The `?admin=1&view=quota` check is placed before the regular `?admin=1` block in the file, so the quota view takes priority when both params are present.

---

*Last updated: 2026-05-04 — Task 5 complete*
