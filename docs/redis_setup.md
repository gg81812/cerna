# Redis Setup — Cerna Infrastructure Sprint

**Task:** 1 of 6  
**Date:** 2026-05-04  
**Status:** Complete

---

## Why Redis

Cerna's in-process LRU cache (512 entries, session-lifetime) works fine for a single-user demo. Redis adds:

1. **Persistence** — cached responses survive app restarts; warm cache on day-2 demo without re-querying Groq.
2. **Quota counters** — per-key Groq TPM tracking (Task 2) requires a shared counter that survives process restarts.
3. **Semantic cache** — embedding vectors stored in Redis sorted sets (Task 4) don't belong in-process.

The design principle throughout: **Redis is optional**. If it's unreachable, `get_redis_client()` returns `None` and every caller falls back to its in-memory path. Zero crashes, zero user-visible errors.

---

## Container Configuration

`docker-compose.yml` defines two services on an internal bridge network (`cerna_net`):

| Service | Image | Port | Network |
|---------|-------|------|---------|
| `redis` | `redis:7-alpine` | 6379 (host) | `cerna_net` |
| `app` | local Dockerfile build | 8501 (host) | `cerna_net` |

### Why redis:7-alpine

- Smallest stable image (~30 MB). No shell tools that increase attack surface.
- Redis 7.x supports stream commands and key-expiry notifications (used by quota counters in Task 2).
- LTS-equivalent: Redis 7.0 is the current stable major version.

### Persistence strategy

```yaml
command: redis-server --save 60 1 --loglevel warning
```

`--save 60 1`: RDB snapshot every 60 s if at least 1 key changed. Stored in the `redis_data` named volume.

| Scenario | Data preserved? |
|----------|----------------|
| `docker compose restart` | Yes (volume survives) |
| `docker compose down` | Yes (volume preserved) |
| `docker compose down -v` | No (volume deleted — intentional wipe) |
| Redis crashes mid-write | Partial (last RDB snapshot) — acceptable for a cache |

AOF (append-only-file) is intentionally NOT enabled. Cerna's cache is warm-able on demand; losing the last 60 s of cache entries on crash is acceptable. AOF would add disk I/O overhead with no meaningful durability benefit for a cache.

---

## redis_client.py — Connection Pool Design

**File:** [redis_client.py](../redis_client.py)

### Connection lifecycle

```
First call to get_redis_client()
    │
    ├─ _pool_tried == False → attempt _init_pool()
    │       ├─ ConnectionPool created (max_connections=20)
    │       ├─ ping() to verify reachability
    │       ├─ OK → _pool set, return StrictRedis client
    │       └─ Exception → _pool = None, warning logged, return None
    │
    └─ _pool_tried == True
            ├─ _pool is not None → return StrictRedis(connection_pool=_pool)
            └─ _pool is None → return None (no retry for process lifetime)
```

**One connection attempt per process.** If Redis is down at startup, the app degrades to in-memory for the session. This avoids thundering-herd retries from Streamlit's multi-threaded request handling. To reconnect after Redis recovers: restart the app (or `docker compose restart app`).

### Thread safety

`redis.ConnectionPool` is thread-safe. Multiple Streamlit threads can call `get_redis_client()` concurrently after `_init_pool()` completes. The `_pool_tried` flag is set once in the first call; a race on the very first call may cause two `_init_pool()` calls but both will succeed or fail identically — no corruption possible since `_pool` assignment is GIL-protected in CPython.

### Environment variables

| Variable | Default | Notes |
|----------|---------|-------|
| `REDIS_HOST` | `localhost` | Set to `redis` in docker-compose (resolves via Docker DNS) |
| `REDIS_PORT` | `6379` | Standard Redis port |
| `REDIS_DB` | `0` | DB 0 is the default; use different DBs to isolate test vs dev |

### Timeouts

`socket_connect_timeout=2` and `socket_timeout=2` (seconds). If Redis is unreachable, the connection attempt fails in ≤2 s rather than blocking indefinitely. This keeps app startup fast even when Redis is not running.

---

## Startup Health Check

`redis_client.health_check()` returns a status dict used by the health endpoint (Task 5 wires this into `?health=1`):

```python
# Redis reachable
{"redis": "ok", "host": "localhost", "port": 6379, "version": "7.2.4"}

# Redis unreachable (first call failed)
{"redis": "unavailable", "host": "localhost", "port": 6379}

# Redis was reachable but ping failed mid-session
{"redis": "error", "error": "Connection refused"}
```

---

## Graceful Degradation

Every Redis caller in Cerna checks `get_redis_client() is not None` before any operation:

| Layer | Redis available | Redis unavailable |
|-------|----------------|-------------------|
| `cache.py` (Task 3) | Redis exact-match cache | In-process LRU (512 entries) |
| `groq_pool.py` (Task 2) | Per-key quota counters | All keys treated as available |
| `semantic_cache.py` (Task 4) | Embedding lookup | Skip semantic cache entirely |
| Health endpoint (Task 5) | Per-key quota metrics | Shows "redis: unavailable" |

The app never imports from `redis_client` at module load time — all imports are deferred to `_init_pool()` inside `get_redis_client()`. If `redis` is not installed, the `ImportError` is caught and returns `None`.

---

## Relationship to cache.py

`cache.py` currently has its own Redis connection code using `REDIS_URL`. This is **not changed in Task 1**. Task 3 will update `cache.py` to:
- Use `get_redis_client()` from `redis_client.py` instead of its own pool
- Support `CACHE_BACKEND=redis|memory` feature flag
- Use `RESPONSE_CACHE_TTL` env var instead of hardcoded 3600 s
- Update key scheme to `response_cache:<prompt_version>:<query_hash>`

Until Task 3 lands, `cache.py` continues to work as before. Tasks 2 and 4 use `redis_client.py` directly.

---

## Dev Workflow

### Bring up the stack

```bash
docker compose up
# Redis starts first → healthcheck passes → app starts
# http://localhost:8501
```

### Run app locally (faster iteration)

```bash
docker compose up redis          # start only Redis
# In another terminal:
streamlit run app.py             # REDIS_HOST=localhost by default
```

### Verify Redis is reachable from Python

```python
from redis_client import get_redis_client, health_check
r = get_redis_client()
print(r.ping())          # True
print(health_check())    # {'redis': 'ok', ...}
```

### Verify persistence (named volume)

```bash
docker compose up -d redis
docker exec cerna_redis redis-cli set test_key "hello"
docker compose restart redis
docker exec cerna_redis redis-cli get test_key   # "hello" — survived restart
docker compose down -v
docker compose up -d redis
docker exec cerna_redis redis-cli get test_key   # (nil) — volume was wiped
```

### Stop Redis, keep app running (degradation test)

```bash
docker compose stop redis
# App continues — get_redis_client() returned None at startup if Redis was already down,
# or existing connections will fail and callers catch exceptions gracefully.
# Logs will show: [Redis] Unavailable (...). Falling back to in-memory cache.
```

---

## What's Next (Task 2)

Task 2 (groq_pool.py) imports `get_redis_client()` to back quota counters with keys:
- `groq_quota:<key_id>:<YYYY-MM-DD>` → integer token count, 25h TTL
- `groq_blocked:<key_id>` → string "1", 60s TTL (per-key 429 backoff)

No changes to `redis_client.py` are needed for Task 2. The connection pool is shared.

---

*Last updated: 2026-05-04 — Task 1 complete*
