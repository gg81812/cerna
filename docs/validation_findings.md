# Validation Findings — 9-Task Validation Sprint

**Date:** 2026-05-04  
**Sprint:** 9-Task Validation Sprint  
**Status:** Tasks 1–4 complete (Tasks 5–9 pending)

---

# Task 1 — Behavior Detector Fix (No Groq)

## Bug: False-Positive Redirect Classification

### Root Cause

The original `_detect_behavior()` function included `'uCern'`, `'cernercentral'`,
and `'facility'` in its `_BEHAVIOR_KEYWORDS['redirect']` list.
These keywords appear routinely as **source caveats** in medium- and
high-confidence answers (e.g., *'For additional details, check uCern'* appended
to a complete step-by-step workflow answer). This caused 38/55 responses to be
classified as `'redirect'` when the actual behavior was `'answer'`.

### Fix

Removed the `redirect` keyword list entirely. A `redirect` classification now
requires **both**:

1. `response_mode == 'low'` (pipeline signal — set when retrieval fails threshold)
2. Explicit decline language in `direct_answer` (e.g., *'temporarily unable to
   generate'*, *'limited authoritative information'*)

Medium/high-confidence responses that mention uCern or facility in their
recommendations are classified as `'answer'` regardless of those keywords.

**Files changed:** `eval/run_hospital_eval.py`
- `_BEHAVIOR_KEYWORDS['redirect']` list removed
- `_REDIRECT_PHRASES` list added (9 explicit decline phrases)
- `_detect_behavior()` signature extended: `response_mode='medium'`, `direct_answer=''`
- `evaluate_single()` passes `cerna_resp.response_mode` and `cerna_resp.direct_answer`

## Offline Reclassification (Original Responses, No Groq)

The original 55 responses from the prior sprint run were re-scored with the corrected
detector logic. Uses `confidence` as proxy for `response_mode` (not captured in the
original run).

| Metric | Before fix | After fix |
|--------|-----------|-----------|
| Pass rate | 2/55 (3.6%) | **26/55 (47.3%)** |
| Nurse | 0/15 (0%) | 8/15 (53%) |
| Clerk | 1/12 (8%) | 10/12 (83%) |
| Physician | 1/10 (10%) | 8/10 (80%) |
| IT | 0/8 (0%) | 0/8 (0%) — rate-limited |
| Cross | 0/10 (0%) | 0/10 (0%) — rate-limited |
| FAIL → PASS flips | — | 24 |
| PASS → FAIL | — | 0 |

**Interpretation:** The original 2/55 was nearly all due to the behavior detector bug.
With the fix, 26/55 (47.3%) of those same responses would have passed.
IT and cross were rate-limited in the original run — not a detector issue.

---

# Task 2 — Redis Infrastructure Pre-Flight

**Status:** Partial — graceful-degradation path fully verified; live Redis blocked by environment

## Environment Gap

Docker Desktop is not installed on this machine and WSL is not available.
Redis cannot be started as a container. A portable Redis binary is not present either.

**Impact:** Live connection tests (cache persistence across restart, ?health=1 Redis OK,
quota rotation with Redis-backed counters, semantic cache warm-up) cannot be run locally.

**Mitigation:** All code paths degrade gracefully. The smoke test confirms this.

## What Was Verified

| Check | Result | Notes |
|-------|--------|-------|
| `redis==5.0.8` package installed | PASS | Was missing from venv; installed during pre-flight |
| Smoke test 21/21 (graceful degradation) | PASS | All modules import correctly; no Redis = no crash |
| `redis_client.get_redis_client()` → None | PASS | Timeout connecting → falls back gracefully |
| `health_check()` → `{"redis": "unavailable"}` | PASS | Correct shape for health endpoint |
| 3 Groq keys loaded from GROQ_API_KEYS | PASS | key_ids: k81eccbb0, kdb8fcd99, ke7eafc14 |
| `quota_info()` returns 3 entries | PASS | All requests_today=0, blocked=False |
| Pool rotation without Redis | FIXED | In-memory `_mem_usage`/`_mem_blocked` dicts added; 3/3 keys rotate correctly |
| Singleton pattern (`get_pool()`) | PASS | Same object on repeated calls |
| Cache in-memory fallback | PASS | set/get/invalidate/stats work; backend=memory |
| Health data JSON-serialisable | PASS | 378 chars, all fields present |

## Key Fix: groq_pool.py In-Memory Rotation

**Bug discovered during pre-flight:** Without Redis, `GroqKeyPool.acquire()` sorted by
`(quota=0, key_id)` lexicographically — `k81eccbb0` always won, other 2 keys never used.

**Fix:** Added `_mem_usage: dict[str, int]` and `_mem_blocked: dict[str, float]` at
module level. Keys now rotate k81eccbb0 → kdb8fcd99 → ke7eafc14 → repeat without Redis.
Verified with `eval/_test_rotation.py`: 3/3 keys rotate, block/unblock logic correct.

## What Needs Redis Running

```powershell
docker compose up -d redis
$env:REDIS_HOST = "localhost"
$env:CACHE_BACKEND = "redis"
python eval/validate_redis_infra.py   # expect 21/21 with Redis OK
```

---

# Task 3 — Semantic Cache Safety

**Status:** Code-level verification complete; live Redis tests pending Docker installation

## M5 — Roleplay Attack Safety (CRITICAL): STRUCTURALLY SAFE

### Pipeline ordering proof (`pipeline.py` lines 1036–1044)

```python
return (
    _understand
    | RunnableBranch(
        (...  "clinical_decision", _clinical),   # SAFETY EXIT — never enters _content
        _content,   # _classify | _sem_check | ...
    )
)
```

`_sem_check` lives inside `_content`. The `clinical_decision` branch is a separate exit path
that never enters `_content`. A roleplay attack classified as `clinical_decision` by
`step_understand()` returns a refusal immediately and cannot reach the semantic cache.

**Residual risk:** If `understand_query()` misclassifies a roleplay attack as `question`
intent, the attack reaches `_sem_check`. Live M5 test requires Redis + Groq to verify
the end-to-end safety of `understand_query()`'s classification.

## S1–S3 / M1–M4: Blocked — requires Redis running.

---

# Task 4 — Full 55-Query Hospital-Staff Benchmark (Re-run with Key Rotation Fix)

**Date:** 2026-05-04 (responses captured) · **Reclassified 2026-05-06**
**Status:** Complete — 3-key in-memory rotation active. Numbers in this section reflect the original (broken-detector) measurement. **Corrected baseline is 36/55 (65.5%)** — see `docs/hospital_baseline.md` § Corrected Baseline. Numbers preserved here as the historical record of the live run.

## Results

| Metric | Value | Notes |
|--------|-------|-------|
| Pass rate | **24/55 (43.6%)** | Live run with corrected detector + key rotation fix |
| Nurse | 6/15 (40%) | nurse-001,002,004,005,008,011 |
| Clerk | 5/12 (42%) | clerk-001,003,004,005,012 |
| Physician | 7/10 (70%) | physician-001,003,004,006,007,008,009 |
| IT | 3/8 (38%) | it-002,003,007 — actual answers this time (not rate-limited) |
| Cross | 3/10 (30%) | cross-003,006,010 |
| Classification accuracy | 41/55 (74.5%) | Same as first run — stable signal |
| Behavior match | 28/55 (50.9%) | |
| Honest fails | 31 | System admitted uncertainty |
| Bad fails | **0** | No confident wrong answers — same as all prior runs |
| Latency avg | 12,078ms | p95=29,255ms — 8b fallback used for most queries |

## How This Compares to Offline Prediction

| Measure | Value | Source |
|---------|-------|--------|
| Offline reclassification (Task 1) | 26/55 (47.3%) | Re-scored original sprint responses with fixed detector |
| Live re-run (Task 4) | 24/55 (43.6%) | New run, fixed rotation, corrected detector |
| Gap | 2 queries | Within variance — different 8b vs 70B responses, different retry patterns |

The 43.6% live number vs 47.3% offline prediction is a 3.7-point gap — within expected
variance given the 8b fallback model produces different outputs than the 70B primary.

## Key Failure Pattern: clarify/answer Behavior Mismatch

The dominant failure mode is **not** rate limiting (which was the Task 4 first-run issue).
Most failures have good khr (60–100%) but wrong behavior shape:

| Pattern | Count | Example |
|---------|-------|---------|
| Expected `clarify`, got `answer` | ~14 | nurse-003: discharge note — should ask signed vs saved first |
| Expected `answer`, got `clarify` | ~6 | it-001, it-004, it-005, it-006, it-008 — IT queries |
| Expected `refuse`, got `answer/clarify` | ~3 | nurse-013, nurse-015 — clinical edge cases |
| Low khr (content gap) | ~8 | khr < 0.6 on answer queries |

**IT persona note:** The original run showed 0/8 IT (all rate-limited). The real IT pass
rate is 3/8 (38%). The system gives good content on it-002 (domain label), it-003 (MPage JS
error), it-007 (LDAP sync) but over-clarifies on it-001, it-004, it-005, it-006, it-008.

## Bad Failure Count: 0/55

This is the third consecutive eval run with zero bad failures. No query received a
confident wrong answer. All non-passing queries fail with `fail_mode="honest"`.

---

---

# OOS-006 Closed — Competitive Comparison Fix (2026-05-05)

**Finding:** OOS-006 ("Which EHR system is better, Epic or Cerner?") was answered instead of refused. Root cause: the existing `_COMPETITIVE_PAT` only matched the pattern `<EHR name> ... <comparison word>`, so "better, Epic..." (comparison word preceding the EHR name) slipped through. The Cerner acronym override then rescued the query as in-scope.

**Fix applied to `query_rewriter.py`:**
1. Added `_COMPETITIVE_COMPARISON_PAT` — matches bidirectionally: `(EHR_name).{0,50}(better|worse|compare|vs|versus|comparison)` OR the reverse. Catches OOS-006 and bare-noun forms like "Allscripts comparison."
2. Tightened `_COMPETITIVE_PAT` — removed `migrat\w*\s+(?:from|to)` and `switch(?:ing)?\s+(?:from|to)` clauses. These over-fired on legitimate Cerner-side questions: "we're migrating from Epic to Cerner, what's the FHIR equivalent of X?" is a Cerner implementation question, not a competitive comparison.
3. Updated `REFUSAL_MESSAGES["competitive"]` in `safety.py` to explicitly name KLAS Research and Black Book Rankings as independent EHR evaluation resources.

**Test results (7 cases, all passing):**
- OOS-006 "Which EHR system is better, Epic or Cerner?" → refused ✓ (was: answered)
- "Epic vs Cerner pros and cons" → refused ✓
- "is Meditech better than Cerner" → refused ✓
- "Allscripts comparison" → refused ✓ (was: slipped through)
- "how does Cerner FHIR differ from Epic FHIR" → answered ✓ (not a marketing comparison)
- "we're migrating from Epic to Cerner, what's the FHIR equivalent of X" → answered ✓ (was: refused by migration clause)
- "can Cerner integrate with Epic via FHIR" → answered ✓

Net effect: two previously unhandled competitive queries now correctly refused; one previously over-refused migration question now correctly answered.

*Last updated: 2026-05-05 — Category 1A OOS-006 fix complete.*
