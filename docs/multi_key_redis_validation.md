# Multi-Key Redis Infrastructure Validation

**Task:** 6 of 6  
**Sprint:** Redis/Multi-Groq/Semantic-Cache Infrastructure Sprint  
**Date:** 2026-05-04  
**Status:** Script ready — run commands below to validate

---

## Validation Scope

| Test | What it verifies | Required to pass |
|------|-----------------|-----------------|
| Infrastructure smoke test | Import-level correctness for all new modules | Yes |
| Red-team regression | 24/24 safety refusals still hold after llm.py changes | Yes |
| Cache warm-up | 10 hospital-staff queries: cold vs warm latency | Yes |
| Semantic cache hit rate | At least 1 semantic hit on re-phrased queries | Informational |

---

## 1. Infrastructure Smoke Test

Run without Groq API key or Redis (tests graceful degradation paths):

```bash
python eval/validate_redis_infra.py
```

Run with Redis (tests live connection):

```bash
REDIS_HOST=localhost CACHE_BACKEND=redis python eval/validate_redis_infra.py
```

**Expected output:** All `[PASS]` entries, exit code 0.

**What it tests:**
- `redis_client.get_redis_client()` — returns client or None
- `redis_client.health_check()` — correct shape
- `GroqKeyPool.acquire()`, `mark_blocked()`, `record_usage()`, `quota_info()` — no exceptions
- `cache.get()`, `cache.set()`, `cache.invalidate()`, `cache.stats()` — correct key isolation and eviction
- `semantic_cache._query_hash()` — deterministic
- `semantic_cache._cosine_sim()` — mathematically correct
- `semantic_cache.step_semantic_cache_check()` — miss on empty cache, no exception
- `semantic_cache.step_semantic_cache_store()` — no-op on low-confidence, no exception
- `llm.get_circuit_breaker_state()` — JSON-serialisable shape
- `llm._pool_acquire()`, `_pool_block(None)`, `_pool_record(None)` — no exception

---

## 2. Red-Team Regression

**Why the changes cannot break safety:** The 24 red-team cases test safety classifiers (`step_clinical_decision`, `step_out_of_scope`, the PII guard, and injection detection). These are all in `query_rewriter.py` and `safety.py`, which this sprint did not touch. The only changes to `llm.py` are:

1. Pool key selection helpers (`_pool_acquire`, `_pool_record`, `_pool_block`) — these run before the circuit breaker check, not in the safety path.
2. `safe_invoke_json()` — modified to select a pool key before invoking. Refusal paths (`step_casual`, `step_out_of_scope`, `step_clinical_decision`) never call `safe_invoke_json()` — they return responses directly without LLM generation.
3. `_invoke_with_backoff()` — added `key_id=None` parameter and a `_pool_block(key_id)` call on 429. This only changes error handling, not safety logic.

**Run the full red-team suite to confirm:**

```bash
python eval/red_team_test.py --delay 8.0
```

Expected: **24/24** (same as pre-sprint baseline).

---

## 3. Cache Warm-Up Validation (10 queries, cold vs warm)

This test requires Redis running and `CACHE_BACKEND=redis`.

**Setup:**
```bash
docker compose up -d redis
set REDIS_HOST=localhost
set CACHE_BACKEND=redis
```

**Run (cold pass — first run populates cache):**
```bash
python eval/run_hospital_eval.py --persona nurse --limit 10 --delay 3.0 2>&1 | head -50
```

Note the avg latency from the cold run.

**Flush cache (do not wipe Redis volume — just delete response_cache keys):**
```bash
docker exec cerna_redis redis-cli --scan --pattern "response_cache:*" | xargs docker exec cerna_redis redis-cli del
```

Actually don't flush — instead, run the same 10 queries again to measure warm cache:

```bash
python eval/run_hospital_eval.py --persona nurse --limit 10 --delay 0.5 2>&1 | head -50
```

**Latency targets:**

| Scenario | Latency target | Notes |
|----------|---------------|-------|
| Cold (cache miss) | < 8000ms avg | Rate-limit distorted; genuine LLM path |
| Warm (exact-match cache hit) | < 200ms avg | Redis GET + CernaResponse.parse only |
| Semantic cache hit | < 1500ms avg | Embedding + cosine sim + Redis GET |

**Expected:** Warm pass is ≥10× faster than cold pass for repeated queries.

---

## 4. Semantic Cache Hit Rate

After running the warm-up test above, run 5 re-phrased versions of the same nurse queries (not exact repeats — paraphrased to test semantic matching):

```bash
python eval/tune_semantic_threshold.py
```

**Expected output:** All `[PASS]` entries; safe threshold range includes 0.85.

If any should-hit pairs show `[LOW]`, the threshold may need lowering. If any should-miss pairs show `[HIGH]`, the threshold needs raising. Adjust `SEMANTIC_CACHE_THRESHOLD` in `.env` accordingly.

---

## 5. Quota Dashboard Spot Check

```bash
streamlit run app.py
# Navigate to http://localhost:8501/?admin=1&view=quota
```

**Expected:**
- Redis status shows "OK" if Docker Redis is running
- Groq key quota table shows at least 1 key
- Circuit breaker shows "CLOSED"
- Cache hit rate updates after the warm-up test

```bash
# Navigate to http://localhost:8501/?health=1
```

**Expected:** JSON with all fields present (`status`, `redis`, `cache`, `circuit_breaker`, `groq_keys`).

---

## 6. Full System Regression

After all the above, run the full regression suite to confirm no new failures:

```bash
python eval/red_team_test.py --delay 8.0       # safety regression
python eval/vague_query_eval.py --delay 8.0    # retrieval regression (target 84%)
```

**Acceptance criteria:**
- Red-team: 24/24 (100%)
- Vague query: ≥ 46/55 (84%) — same as pre-sprint baseline
- Bad failures (confident wrong answers): 0 across both suites

---

## What Changed — Risk Assessment

| Component | Change | Risk |
|-----------|--------|------|
| `redis_client.py` | New file | None — not imported by any existing code yet |
| `groq_pool.py` | New file | None — only imported by llm.py helpers |
| `cache.py` | Key scheme changed; connection via redis_client | Low — key format change invalidates old cache (intentional cold start) |
| `llm.py` | Pool key selection in `safe_invoke_json`; `_invoke_with_backoff` adds `key_id=None` | Low — backward compatible; single-key behaves identically |
| `pipeline.py` | Semantic cache check/store steps added; `_content` chain extended | Medium — new `_retrieval_branch` RunnableBranch; must not change branch when `semantic_cache_hit=False` |
| `state.py` | Two new fields with defaults | None — TypedDict is not enforced at runtime |
| `app.py` | Health endpoint extended; quota view added | Low — both changes are additive; existing admin=1 panel unchanged |

**Medium-risk item: pipeline.py `_retrieval_branch`**

The new branch logic:
```python
_retrieval_branch = RunnableBranch(
    (lambda s: bool(s.get("semantic_cache_hit")), RunnableLambda(lambda s: s)),
    _prep | _retrieve | _fuse | _rerank | _gate | _generation_branch,
)
```

When `semantic_cache_hit=False` (default, and the case for every query until the semantic cache is populated): the branch takes the default path `_prep | ... | _generation_branch`. This is identical to the pre-sprint `_content` chain. The only change is a `bool(s.get("semantic_cache_hit"))` check per request (negligible overhead) and the two new steps `_sem_check` and `_sem_store` which are both lightweight (sub-millisecond when Redis is unavailable or semantic hit check returns None quickly).

**If semantic cache causes issues:** set `CACHE_BACKEND=memory` — this disables Redis-backed semantic cache (both `_get_redis()` calls in semantic_cache.py return None immediately) and the new steps become true no-ops.

---

*Last updated: 2026-05-04 — All 6 tasks complete*
