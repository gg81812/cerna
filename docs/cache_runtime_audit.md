# Cache Runtime Audit

**Date:** 2026-05-06
**Author:** investigation pass on the company laptop
**Scope:** Determine the actual runtime state of the Redis-backed infrastructure
delivered by the infrastructure sprint (Tasks 1–6, 2026-05-04), given that
Docker is not available on this machine.

---

## TL;DR

- **Redis is not running.** No listener on `localhost:6379`, no Redis/Memurai
  Windows service, no WSL distro, no Docker. The `redis_client.get_redis_client()`
  call returns `None` after a 2 s connect timeout.
- **The system is operating in pure memory mode.** `CACHE_BACKEND` is unset →
  defaults to `"memory"` (not even `redis-with-fallback`). Backend reports as
  `"memory"`, not `"memory(fallback)"`.
- **The validation sprint numbers reflect memory-mode operation.** Zero
  `cache_hit`, zero Redis-key references, and only one sub-100 ms latency record
  across all 55 hospital-eval queries — and that one is a clinical_decision
  refusal short-circuit, not a cache hit.
- **Multi-Groq key rotation is working** in the in-memory fallback path
  (k81eccbb0 → kdb8fcd99 → ke7eafc14, even split). Groq quota numbers in the
  health JSON, however, are misleading — `quota_info()` only reads from Redis,
  so it always shows `requests_today: 0` even after thousands of in-memory
  rotations.
- **Net:** the infrastructure sprint's Redis layer has been dead code on this
  laptop the entire time. The system works correctly because every Redis path
  has a memory fallback, but the response cache, semantic cache, and
  cross-process quota tracking that the sprint advertises have never been
  exercised in any measurement on this machine.

---

## 1.1 — Is Redis reachable right now?

**Probe** (`get_redis_client()` and `health_check()` from `redis_client.py`):

```
[Redis] Unavailable (Timeout connecting to server). Falling back to in-memory cache.
health_check() → {'redis': 'unavailable', 'host': 'localhost', 'port': 6379}
get_redis_client() → None
```

**Listener / service / runtime checks:**

| Check | Result |
|-------|--------|
| `Test-NetConnection localhost 6379` | False — no listener |
| `Get-NetTCPConnection -LocalPort 6379` | empty — port idle |
| `Get-Service *redis* / *memurai*` | none registered |
| `wsl --list --quiet` | no distros installed |
| `docker` command | not on PATH |
| `redis-py` package | installed (5.0.8) — pinned per `docker-compose.yml` |

**Verdict:** Redis is not running anywhere this app can reach it. The
`redis-py` library imports cleanly; the issue is purely that there is no
server. `redis_client.py` correctly catches the timeout and degrades.

This matches `docs/validation_findings.md` Task 2 ("Docker Desktop is not
installed on this machine and WSL is not available… Redis cannot be started
as a container") — that statement is still true today.

---

## 1.2 — What does the running app think the cache state is?

The `?health=1` endpoint logic in [app.py:300-345](../app.py#L300-L345) was
exercised directly by importing the same modules (Streamlit-free) to avoid
spinning up a server. Output:

```json
{
  "chroma_dir_exists": true,
  "redis":           {"redis": "unavailable", "host": "localhost", "port": 6379},
  "cache":           {"backend": "memory",
                      "cache_backend_cfg": "memory",
                      "ttl_seconds": 3600,
                      "hits": 0, "misses": 0, "hit_rate_pct": 0.0,
                      "in_memory_entries": 0, "lru_max": 512},
  "circuit_breaker": {"state": "closed",
                      "failures_recent": 0, "failure_threshold": 5,
                      "open_until_epoch": null, "seconds_until_close": 0},
  "groq_keys": [
    {"key_id": "k81eccbb0", "requests_today": 0, "daily_limit": 100, "blocked": false, ...},
    {"key_id": "kdb8fcd99", "requests_today": 0, "daily_limit": 100, "blocked": false, ...},
    {"key_id": "ke7eafc14", "requests_today": 0, "daily_limit": 100, "blocked": false, ...}
  ]
}
```

Reading [cache.py:31](../cache.py#L31) and [cache.py:122-123](../cache.py#L122-L123):

- `_CACHE_BACKEND = os.getenv("CACHE_BACKEND", "memory")` — there is no
  `CACHE_BACKEND` line in `.env` (verified), so the cache backend is plain
  `memory`. The fallback label `memory(fallback)` only fires when
  `CACHE_BACKEND=redis` *and* Redis is unreachable. We're not even attempting
  Redis-mode caching.
- `semantic_cache.py` likewise reads `CACHE_BACKEND` — in plain memory mode
  `_get_redis()` returns `None`, `check()` always misses, `store()` is a no-op.
  Semantic cache is structurally inert.

**Verdict:** the app correctly reports "we are running on memory backend, no
Redis." The dashboard surfaces it; nothing is being silently masked. (One
caveat — see §1.4 — Groq quota numbers in this same JSON are *not* honest.)

---

## 1.3 — What was actually running during the validation sprint?

Three independent signals all point the same direction: the validation sprint
ran in pure memory mode.

**Signal A — eval results jsonl.** Across 55 records in
`eval/hospital_eval_results.jsonl`:
- 0 lines contain `cache_hit`, `redis`, or `groq_quota`
- 54/55 records have `latency_ms > 1000`
- The 1 record under 100 ms (`hs-nurse-009`, 15 ms) is a clinical-decision
  refusal exit that short-circuits before retrieval/LLM, not a cache hit
- avg latency 12,078 ms, max 70,174 ms — consistent with cold full-pipeline
  execution on every query, not a system with a warm semantic cache

**Signal B — explicit doc statements.**
- `docs/validation_findings.md` Task 2: "Live connection tests… cannot be run
  locally." Listed as BLOCKED.
- `docs/post_sprint_benchmarks.md` L130: "*Requires Redis. Semantic cache
  (cosine ≥ 0.85, 6h TTL) is implemented but needs Docker.*"
- `docs/post_sprint_benchmarks.md` L193: "Cached latency — not measured;
  estimated < 2000 ms but unconfirmed (requires Redis)"
- `docs/latency_profile.md` L124: "Redis cache flush — BLOCKED — Docker not
  installed (documented in validation sprint Task 2)"

**Signal C — env state today.** No `CACHE_BACKEND` in `.env`, no Redis
listener, no service, no Docker, no WSL. Even if the validation sprint had
managed to start Redis somehow, the laptop is not in that state now and
nothing in `.env` would re-engage it on next boot.

**Verdict:** the validation sprint Tasks 1, 4, 5, 6, 7 were all run with
`cache_backend=memory`, `redis_client → None`, `semantic_cache` inert, and
Groq quota tracking via in-memory `_mem_usage` only. The infrastructure
sprint's Redis layer never participated in any measurement that reached the
`hospital_eval_results.jsonl` / `golden_set.jsonl` / `latency_profile.md`
numbers.

This is not a case of "Docker was running on a colleague's machine and the
results were imported" — the docs themselves say live Redis tests were
blocked. The infrastructure sprint delivered the *code*; it did not deliver
*any measured caching benefit* on this environment.

---

## 1.4 — Multi-Groq pool actual operational state

The pool is the one piece of infrastructure that arguably did affect
validation numbers. Verified by exercising `acquire()` + `record_usage()` 15
times in a Redis-down environment:

```
selection sequence: k81…, kdb…, ke7…, k81…, kdb…, ke7…, …  (round-robin)
counts: {'k81eccbb0': 5, 'kdb8fcd99': 5, 'ke7eafc14': 5}
_mem_usage after: {'k81eccbb0': 5, 'kdb8fcd99': 5, 'ke7eafc14': 5}
```

All three keys rotate evenly. The fix described in `validation_findings.md`
Task 2 ("`_mem_usage` / `_mem_blocked` dicts added") is in place in
[groq_pool.py:33-34](../groq_pool.py#L33-L34) and works.

**However — a real bug uncovered by this audit:** `quota_info()`
([groq_pool.py:130-154](../groq_pool.py#L130-L154)) only reads
`requests_today` and `blocked` from Redis; when Redis is unavailable it
returns `requests_today: 0, blocked: False` for every key, even though
`_mem_usage[kid]` has been incrementing. The `?health=1` and admin-dashboard
panels therefore lie when running in memory mode: they show all keys at
0/100 forever.

This is mostly cosmetic for a single-user Streamlit dev session, but it
matters for the operational dashboard story in the POV demo — anyone looking
at the dashboard during a live demo on this laptop would see a flat
"all keys idle, no usage" picture even after dozens of queries. Worth
noting; not blocking.

**Three keys are configured and rotating** — so the `groq_pool` story for
the validation sprint is honest. The 24/55 hospital-staff and 32/75 golden
numbers were run on real 3-key rotation, not on a single key. The
"single-key silent failure" scenario the audit was meant to rule out did not
happen.

---

## Summary

> The Redis infrastructure is currently **not running** on this laptop, has
> not been running at any time during the 9-task validation sprint, and is
> not configured to start on the next reboot (no service, no Docker, no
> dotenv `CACHE_BACKEND` setting). The system is operating in
> **memory-fallback** mode — though specifically the "plain memory" variant,
> not the "redis-attempt-then-fall-back" variant: `CACHE_BACKEND` defaults
> to `memory` and the Redis path is never even tried for the response cache
> or semantic cache.
>
> The validation sprint numbers (24/55 hospital-staff, 32/75 golden,
> 12,078 ms avg latency, 0 bad failures) reflect **memory-mode operation
> with no response cache, no semantic cache, and in-memory Groq quota
> rotation across 3 keys**. They are real numbers on a real system; they
> just don't reflect any of the caching benefits the infrastructure sprint
> claimed.

---

## What the infrastructure sprint actually delivered (on this laptop)

| Sprint deliverable | Code shipped | Working on this laptop? |
|--------------------|--------------|--------------------------|
| `redis_client.py` shared pool | yes | inert — Redis not reachable |
| `docker-compose.yml` + Dockerfile | yes | unusable — no Docker |
| `groq_pool.py` 3-key rotation | yes | **works (in-memory path)** |
| `cache.py` Redis backend | yes | inert — `CACHE_BACKEND=memory` |
| `cache.py` LRU fallback | yes | works — but cold every restart |
| `semantic_cache.py` | yes | inert — `_get_redis()` returns None |
| `?health=1` endpoint | yes | works — accurately reports `unavailable` |
| `?admin=1&view=quota` dashboard | yes | works structurally, but Groq quota panel always shows 0/100 (see §1.4 bug) |
| Smoke test 21/21 graceful degradation | yes | passes |

The deliverables that actually moved validation numbers are the **3-key
in-memory rotation** (without it, validation would have hit single-key rate
limits much harder) and the **graceful-degradation discipline** (without it,
the absence of Redis would crash the app). Everything else is shelf-ready
code waiting for a Redis instance.

---

## Next-step options

The audit produces three valid paths. Picking between them is a judgment
call about what the POV needs to demonstrate, not a code question.

### Option 1 — Accept memory-mode operation, document honestly

For a single-user Streamlit dev / demo environment, plain in-memory caching
is functionally adequate. Cache hits across a single demo session help; the
fact that they don't survive restart doesn't really matter for a stakeholder
demo. The 12 s avg latency is dominated by retrieval + LLM, not by cache
absence — Redis would mostly help on repeat queries within a session,
which an LRU already does.

**Cost:** zero code change. Update docs to stop implying Redis is part of
the running system. Drop the "estimated < 2000 ms cached latency" claim
from `post_sprint_benchmarks.md` (or measure it with the LRU-only path,
which is what the user actually experiences).

**Trade-off:** the POV pitch loses the "production-grade caching layer"
talking point. The dashboard's Redis card permanently reads `UNAVAILABLE`
in any live demo on this laptop.

### Option 2 — SQLite-backed alternative (no infra change required)

Replace the Redis backend in `cache.py` and `groq_pool.py`'s quota tracking
with a SQLite file at `chroma_store/cache.sqlite`. SQLite is in stdlib,
needs no service, and gives durability across restarts plus honest
quota_info() readings.

Semantic cache is harder — it needs a vector similarity store. Either keep
that path Redis-only (and dead) or extend ChromaDB to host a `sem_cache`
collection alongside `cerner_docs_bge`.

**Cost:** ~1–2 days of focused work. Touches `cache.py`, `groq_pool.py`,
optionally `semantic_cache.py`. No new dependency.

**Trade-off:** mild performance hit vs Redis (10–50× slower per op, still
sub-millisecond). The POV's "production caching" narrative changes from
"Redis" to "embedded persistence" — arguably more honest for a desktop demo.

### Option 3 — Remote Redis (managed instance)

Spin up a Redis instance in a corporate-approved cloud tenancy (Azure
Cache for Redis, AWS ElastiCache, or even a small Render/Railway free
tier for the demo). Set `REDIS_HOST` / `REDIS_PORT` / `CACHE_BACKEND=redis`
in `.env`. The existing code starts using it on next launch.

**Cost:** ~1–2 hours including provisioning, network reachability check,
and re-running validation to capture the cache-warm numbers.

**Trade-off:** introduces a network dependency and credential management
into the demo. Latency from the laptop to a managed Redis adds 5–30 ms per
op — usually fine, occasionally annoying. May require corp-IT approval
depending on the tenancy used.

### What this audit does **not** answer

Whether any of the three options is worth doing. That's a separate
conversation about what the POV actually needs from the caching layer
versus what was shipped speculatively during the infrastructure sprint.

---

## Smaller findings worth tracking

1. **`quota_info()` lies in memory mode.** It only reads from Redis. When
   Redis is down, the dashboard shows all keys idle even after thousands of
   rotations. Trivial fix (read from `_mem_usage` as fallback) but the
   current dashboard is misleading on this machine.

2. **`CACHE_BACKEND` defaults to `memory`, not `redis`.** The "Redis-first
   with memory fallback" path advertised in `cache.py`'s docstring is
   gated behind an env var that nobody set. To actually exercise it, the
   user would need to add `CACHE_BACKEND=redis` to `.env` AND have Redis
   running. Current `.env` has neither.

3. **`docker-compose.yml` and `Dockerfile` are aspirational on this
   laptop.** They are valid artifacts a colleague with Docker could use,
   but they cannot be exercised here. The sprint summary should
   distinguish "code shipped" from "code exercised in this environment."

4. **In-memory LRU is cold every restart.** Streamlit reloads on file
   edits and on every `streamlit run` invocation reset `_lru_store = {}`.
   Effective cache lifetime in practice is one session. This is a real
   limitation of the no-Redis path, separate from the audit but worth
   factoring into the Option 1 calculus.

---

*This audit is data, not a recommendation.* Whether to migrate, accept, or
provision Redis is a judgment call to make once we know what the POV demo
actually needs from the caching layer.
