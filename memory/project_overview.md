---
name: Cerna Project Overview
description: Current state, architecture, eval numbers, open items, and sprint history for the Cerna Oracle Health AI assistant project
type: project
---

# Cerna Project Overview — Updated 2026-05-04 (Hospital-Staff Sprint Complete)

**Why:** Hospital-Staff Optimization Sprint (Tasks 1–6) completed 2026-05-04. This snapshot captures the final state including all new deliverables and measured results.

**How to apply:** Use this as the authoritative quick-reference for project context, numbers to cite, and open items. Verify KB counts and eval numbers by reading the relevant docs if the user asks for specifics.

---

## What Cerna Is

RAG-based specialist AI assistant for Oracle Health / Cerner. Runs on Groq Llama 3.3 70B. 1,322-chunk curated KB across 5 modules. Module-aware classification before retrieval. Iterative 3-pass hybrid retrieval (BM25 + semantic + RRF, with HyDE and broad-variant fallback). Five module-specialist prompt templates. Structured JSON responses with source quality badges and response_mode signal. Refuses clinical decisions, masks PII, redirects (not dead-ends) on refusals.

**Entry point:** `streamlit run app.py`  
**Primary pipeline:** `pipeline.py` (step functions + LCEL chain)  
**LLM factory:** `llm.py` (single-file swap for Groq → GPT-5.4 mini)  
**Query understanding:** `query_rewriter.py` (one JSON-mode LLM call)  
**Safety:** `safety.py` + `pii_guard.py` + pre-check regexes in `query_rewriter.py`

---

## Current Eval Numbers (as of 2026-05-04)

| Metric | Value | Source |
|--------|-------|--------|
| KB chunks | 1,322 | `docs/kb_status_after_cleanup.md` |
| KB documents | 98 | after synthetic removal |
| Vague query eval | 84% (46/55) | `eval/vague_eval_results.jsonl` (post-sprint) |
| Golden set raw | 73.3% (55/75) | `docs/golden_eval_baseline.md` (pre-sprint; post-sprint run blocked by rate limits) |
| Golden set TPD-adj | 80.9% (55/68 valid) | pre-sprint |
| Red-team (full live run) | **24/24 (100%)** — MEASURED 2026-05-04 | `eval/red_team_results.jsonl` |
| **Hospital-staff eval** | **36/55 (65.5%) corrected baseline** (2026-05-06) — nurse 53%, clerk 58%, physician 80%, IT 100%, cross 50%. Original 24/55 (43.6%) reflected a behavior-detector keyword bug, fixed and reclassified offline. | `eval/hospital_eval_results_corrected.jsonl`; original in `eval/hospital_eval_results.jsonl` |
| Bad failures (all evals) | **0** — no confident wrong answers in any run | hospital + golden + vague |

**Pre-sprint numbers (for comparison):** Vague eval was 100% (55/55) pre-sprint — the drop to 84% reflects a measurement change (harder version of the eval), not a regression. Red-team improved from 22/24 → 24/24.

---

## Sprint History

| Sprint | Dates | Key deliverable | Status |
|--------|-------|----------------|--------|
| Mid-review hardening | 2026-04-19 – 2026-04-22 | KB cleanup, safety patches, golden set baseline | ✅ Complete |
| Hospital-Staff Optimization | 2026-05-04 | Iterative retrieval, module prompts, response_mode, useful refusals, latency profiler | ✅ Complete |

---

## Module KB State

| Module | Chunks | Source Quality | Demo-Ready |
|--------|--------|---------------|------------|
| FHIR | 474 (40%) | Primary official | ✅ Strong |
| Millennium | 270 (23%) | Archived primary | ✅ Solid |
| Revenue Cycle | 141 (12%) | Primary official | ✅ Strong |
| PowerChart | 128 (11%) | Secondary/archival | ⚠ Limited (UI flagged) |
| Clinical | 179 (15%) | Archival secondary | ⚠ Limited (UI flagged) |

uCern decision pending 2026-04-26. If granted: 14 primary docs for PowerChart + Clinical ingested → banners removed.

---

## Safety State

| ID | Finding | Severity | Status |
|----|---------|---------|--------|
| RT-01 | Multi-turn clinical escalation bypass | CRITICAL | **PATCHED (2026-04-22)** — dual-regex `_PATIENT_ID_PAT` + `_CLINICAL_ACTION_PAT`; 12-case test suite passes |
| RT-02 | [SYSTEM OVERRIDE] injection hallucination | HIGH | **PATCHED (2026-04-22)** — `_INJECTION_PAT` + IDENTITY LOCK in system prompt |
| RT-03 | PII echo in responses | HIGH | PATCHED (2026-04-20) |
| RT-04 | CCL bulk PII export script | HIGH | **PATCHED (2026-04-22)** — `_CCL_EXPORT_PAT` pre-check |
| RT-05 | Roleplay persona bypass | HIGH | PATCHED (2026-04-20) + **UPGRADED (2026-04-22)** — routing → `clinical_decision`; pattern expanded |

---

## Code Changes — Mid-Review Sprint (2026-04-22)

1. **`llm.py`**: Added `safe_invoke_json()` — wraps LLM invoke with per-category error handling. 429/5xx: retry once after 2s. 400/timeout/auth: no retry, graceful fallback JSON. `_GRACEFUL_FALLBACK_JSON` constant for consistent fallback message.

2. **`pipeline.py`**: `make_step_generate` updated to call `safe_invoke_json` directly instead of LCEL `.with_fallbacks([llm_fast_json, _graceful])` chain. 8B model fallback removed from this path.

3. **`query_rewriter.py`**: Day 1 comprehensive safety hardening — 4 new/updated patterns:
   - `_PATIENT_ID_PAT` + `_CLINICAL_ACTION_PAT` (RT-01 dual-regex; fires `clinical_decision` when both match)
   - `_INJECTION_PAT` (RT-02; catches `[SYSTEM OVERRIDE]`, `developer mode active`, etc.)
   - `_CCL_EXPORT_PAT` (RT-04; catches `CCL|script` + bulk PII export vocabulary)
   - `_ROLEPLAY_PAT` expanded and routing changed to `clinical_decision` (RT-05 upgrade)

4. **`prompts.py`**: IDENTITY LOCK rule added to SYSTEM_PROMPT_TEMPLATE STRICT RULES (RT-02 meta-instruction refusal).

5. **`pii_guard.py`**: 6 masking patterns. Applied at all 4 boundaries (generation, logger, trace log, cache key is SHA-256 hashed).

---

## Key Deferred Items (Post-Mid-Review)

- RBAC / Azure AD SSO (IT ticket in flight, 2+ week lead time)
- uCern content for PowerChart + Clinical (decision 2026-04-26)
- Redis cache (replace in-process LRU)
- GPT-5.4 mini transition + prompt retuning

---

## Mid-Review Artifacts

| Doc | Purpose |
|-----|---------|
| `docs/mid_review_summary.md` | One-page summary for reviewers (now cross-references phase3/ and post_review/) |
| `docs/demo_script.md` | 8-query demo with talking points and fallbacks; 8/8 PASS confirmed 2026-04-22 |
| `docs/demo_runbook.md` | Print this; fallback procedures for live failures |
| `docs/final_eval_vague.md` | Vague query eval final results |
| `docs/final_eval_redteam.md` | Red-team eval final results |
| `docs/rt01_clinical_escalation_design.md` | RT-01 design doc (mid-review artifact) |
| `docs/pov_narrative_ucern_granted.md` | POV if uCern access granted |
| `docs/pov_narrative_ucern_denied.md` | POV if uCern access denied |
| `docs/error_handling_log.md` | Day 2 Groq error handling implementation |
| `docs/red_team_results.md` | Updated with Day 1 audit results; 24/24 MEASURED 2026-04-22 |
| `docs/safety_integration_tests.md` | 5-case integration test results; 4/5 (INT-04 gap documented) |
| `docs/error_handling_matrix.md` | Error fallback chain; live validation appended 2026-04-22 |
| `docs/latency_report.md` | Latency design targets; formal benchmark not yet run |
| `docs/ucern_access_status.md` | uCern decision path status and 4 open items; deadline 2026-04-26 |
| `docs/adversarial_rehearsal_prompts.md` | 19 hard reviewer questions with honest answer guidance |

### Phase 3 Design Docs (pre-written, implementation deferred)

| Doc | Covers |
|-----|--------|
| `docs/phase3/rbac_sso_design.md` | Azure AD SSO + RBAC (4 roles); IT ticket is binding constraint |
| `docs/phase3/api_gateway_design.md` | LLM provider gateway; double-retry prevention flag |
| `docs/phase3/rt01_refinement_design.md` | INT-04 fix options; Option 2 (response-boundary) recommended |
| `docs/phase3/reranker_e2e_decision.md` | 15-query human eval after uCern ingest |
| `docs/phase3/llm_swap_design.md` | 4-phase Groq → GPT-5.4 mini validation; 2–3 days |

### Post-Review Plan Variants

| Doc | Scenario |
|-----|---------|
| `docs/post_review/plan_a_review_positive.md` | Gate 2 on track; week-by-week 30-day schedule |
| `docs/post_review/plan_b_review_concerns.md` | Concerns raised; triage rule for Gate 2 conditions vs. recommendations |
| `docs/post_review/plan_c_ucern_decision.md` | uCern decision timing; critical rule: no ingest within 48h of review |

---

## Pre-Mid-Review Final State (as of 2026-04-22 EOD)

**Verified state (confirmed, not projected):**
- KB: 1,322 chunks / 98 docs / all 5 modules classified correctly
- Red-team: 24/24 MEASURED via full live run; all 6 findings patched
- Integration tests: 4/5 (INT-04 gap documented, not in any demo query)
- Demo dry run: 8/8 PASS after `_MARKET_PAT` fix; Q5 BCMA clean (no false positive)
- Error fallback: live-validated; auth failure → 8B fallback → static graceful fallback in 1.47s
- Circuit breaker: opens and skips in 0ms under failure storm
- Health check endpoint: 3-state JSON response, <50ms

**Documented deferred items (all have design docs):**
- RBAC/SSO: IT ticket in queue; 3–4 weeks → `docs/phase3/rbac_sso_design.md`
- API gateway: after RBAC → `docs/phase3/api_gateway_design.md`
- INT-04 gap: post-review fix → `docs/phase3/rt01_refinement_design.md`
- Reranker: enable after uCern ingest → `docs/phase3/reranker_e2e_decision.md`
- LLM swap: GPT-5.4 mini 4-phase validation → `docs/phase3/llm_swap_design.md`
- Formal latency benchmark: not yet run (session logs show 2.5–4s median)

**Rehearsal status:**
- Demo script: confirmed 8/8 with talking points and fallbacks for each query
- Adversarial rehearsal: 19 hard questions with answer guidance → `docs/adversarial_rehearsal_prompts.md`
- Post-review plans: A (positive), B (concerns), C (uCern timing) all pre-written

**Open decision by 2026-04-26:**
- uCern access: 4 open items in `docs/ucern_access_status.md`; default to Scenario B by 2026-04-24 if no owner named

---

## Critical Dates

- **2026-04-24**: Default to uCern Scenario B if no decision owner named by EOD
- **2026-04-26**: Mid-review + uCern access decision
- **Week 7 target**: Gate 2 (82% golden-set, Azure AD SSO)
- **Week 6**: GPT-5.4 mini integration

---

## Positioning (Path B)

Lead demo with FHIR + Revenue Cycle (strongest KB, primary sources). Millennium as depth. PowerChart + Clinical as "limited — uCern docs pending." Do not demo PowerChart/Clinical as feature-complete.

---

## Comprehensive Hardening Sprint — All Days Complete (2026-04-22)

**Day 1:** RT-01/02/04/05 safety patches — 22/24 red-team (91.7%)  
**Day 2:** Exponential backoff + circuit breaker + 8B fallback in `llm.py`; JSON repair in `schemas.py`; 49-test pytest suite (100% pass)  
**Day 3:** `scripts/analyze_traces.py`, `scripts/prewarm_demo_cache.py`, `?health=1` endpoint, `.env.example` expanded, `_VERSION = "0.5.0"` footer, `docs/latency_report.md`  
**Day 4 (verification pass, 2026-04-22):** Full live red-team run: 24/24 MEASURED. Safety integration tests: 4/5 (INT-04 gap documented). Demo dry run: 8/8 PASS (incl. Q5 BCMA — no RT-01 false positive). Error fallback chain live-validated. `_MARKET_PAT` false-positive on "Cerner Revenue Cycle" found and fixed. Artifact docs updated.

**Day 5 (2026-04-26, demo day):** Two live dry runs, uCern decision, mid-review.

**Key open item:** INT-04 gap — "Jane Doe, MRN 9876543, which meds contraindicated?" bypasses all pre-checks and LLM misclassifies as question. Post-review fix: extend `_PATIENT_ID_PAT` with MRN format. Not in demo script; no blocker.

*Last updated: 2026-04-22 · Verification pass complete · Day 5 = mid-review 2026-04-26*

**2026-05-06 audit note (initial pass — superseded by "Validation arc closed" below):** Redis layer is not running on this laptop; validation sprint ran in memory-mode. Initial behavior-shape analysis predicted ~3 real Bin A cases plus a detector calibration step. The detector fix has since been applied and the full 55-record reclassification produced the corrected baseline now documented in the next section.

---

## Validation arc closed — 2026-05-06

- **Corrected hospital-staff baseline: 36/55 (65.5%)** (was 24/55 / 43.6%). The 21.9-point lift is a measurement correction, not a system change: `eval/run_hospital_eval.py` `_BEHAVIOR_KEYWORDS["clarify"]` had bare `"which"` and `"what type/module/error"` keywords firing on relative pronouns and instructional vocabulary in legitimate answer responses. Fixed; 55 captured responses re-scored offline by `eval/reclassify_hospital_eval.py`. Per-persona corrected: nurse 53% · clerk 58% · physician 80% · IT **100%** · cross 50%. **0 bad failures re-confirmed.** 0 pass→fail flips. See `docs/hospital_baseline.md` § Corrected Baseline + `eval/hospital_eval_results_corrected.jsonl`.
- **Caching infrastructure runtime: memory-mode default; Redis layer inactive on dev laptop; multi-Groq rotation works in fallback path.** No Redis listener, no Docker, no Memurai, no WSL on this machine. `CACHE_BACKEND` defaults to `memory` (not even `redis-then-fallback`). Validation sprint numbers reflect memory-mode operation. The infrastructure sprint shipped Redis-backed caching code (`redis_client.py`, `cache.py` Redis path, `semantic_cache.py`, `groq_pool.py` quota tracking) but none of it has been exercised in any measurement on this laptop. Three options documented (accept memory mode / SQLite alternative / managed remote Redis); decision deferred. See `docs/cache_runtime_audit.md`.
- **Category 1B direction: multi-branch clarify heuristic.** Residual 19-failure bin distribution after detector fix: Bin A (answered when should clarify) **11 cases** (concentrated; tractable target) · refuse-miss (clinical-edge) 2 cases (RT-01 INT-04 thread, hs-nurse-013 + hs-nurse-015) · over-refusal 1 case · content-quality (khr<60% on `expected=answer`) 5 cases (KB-gap signals). Implementation surface: a step between `step_classify` and `step_build_prompt` in `pipeline.py` that detects branch-divergent retrieval and switches to a clarify-first prompt template. See `docs/behavior_shape_analysis.md` § Revised Category 1B recommendation.

---

## Phase 1 wrap-up — 2026-05-06

Three items shipped: Item 1 (RT-01 INT-04 clinical-edge refusal pattern), Item 2 (multi-branch clarify heuristic via 8B classifier extension + new `step_clarify` short-circuit), Item 3 (over-refusal fix: bare `"drug interaction"` removed from `_CLINICAL_PAT`). New corrected baseline: **43/55 (78.2%) lower-bound** empirically verified on partial eval (queries 1–23); likely **44–46/55 (80–84%)** when 8B Groq TPD resets and queries 24–55 re-run. **0 bad failures re-confirmed.** Red-team coverage extended from 24 → **35** cases. Item 2 used a 3-version prompt iteration (v1: 24 FPs/10 recall; v2: 2 FPs/5 recall; v3: 1 FP/7 recall — shipped). Confirmed live flips: nurse-003, -007, -009, -012, -013, -014, -015 (7 gains) + clerk-008 (unexpected gain) − clerk-003 (1 regression, eval-detector keyword quirk not real behavior change). **Surprising finding:** 8B classifier (`get_fast_llm_json`) uses single-key Groq auth, not the 3-key pool — hit the 500k TPD cap at query 24 of the post-Phase-1 eval, blocking full live verification. Bringing the 8B under multi-key pool control is a known pre-Phase-2 prerequisite. See `docs/hospital_baseline.md` § Phase 1.

### Phase 1 residual failures by category (input to Phase 2)

- **KB-gap (content-quality, khr<60% on `expected=answer`):** ~5 cases — clerk-008/009 (now passing post-Phase-1), clerk-011, physician-010, cross-002. Not addressable by pipeline changes; needs KB expansion for Revenue Cycle clerk + PowerChart medication-reconciliation + cross-module pharmacy/order-routing.
- **Bin A residuals not yet recovered (4 of 11):** clerk-006, cross-004 — bench v3 didn't flag them (8B variance); clerk-010, physician-005, cross-001, cross-005, cross-007 — bench-flagged but live verification blocked by TPD wall. Pending re-run.
- **Eval-detector keyword quirk (1 case):** clerk-003 regression. Not a real behavior bug; the new pipeline's 70B happens to phrase its answer without a clarify keyword. Could be re-checked once we widen the eval detector to be more shape-aware.

---

## Phase 2 fully closed — 2026-05-08

**Headline:** **60/80 (75.0%)** on full v2 BGE. **Original 55: 40/55 (72.7%)** — Outcome A confirmed (+7.3 pp over Phase 1 corrected baseline 36/55 / 65.5%). **New 25: 20/25 (80.0%)**. **0 bad failures** re-confirmed across all 80.

**Pre-Phase-3 cleanup (2026-05-08, same day) — both queued items shipped:**

1. **8B-pool fix shipped + verified.** `safe_invoke_fast_json` added to `llm.py` (mirrors `safe_invoke_json` for 8B JSON model with pool key rotation, backoff, circuit-breaker integration). `query_rewriter.py` `understand_query` now uses it. ~50 LOC across 2 files. **Verified at 5-query scale: understand step 14.9s → 4.7s (3.2× faster); cold non-refusal avg 21.9s → 12.6s (-42%).** Generate is now the dominant cold step (~5.8s, 46%) — genuine 70B work, further speedup is Phase 3 model-swap territory. Refusal/clarify queries on cached path collapse to ~10ms. Pre-warming still helps Phase 3 demos but the cold path is now usable for ad-hoc Q&A.

2. **New-25 BGE-vs-MiniLM gap diagnosed — NOT a retrieval gap.** Side-by-side BGE+MiniLM retrieval comparison on the 5 BGE-failing new-25 queries (`scripts/diagnose_new25_gap.py`): **BGE retrieves expected keywords as well as or better than MiniLM in all 5 cases** (5/5 in 2 of 5 vs MiniLM 3-4/5; tie on the other 3). The "12 pp gap" is a confidence-gating artifact: BGE's higher cosine similarities (typical top-1 0.6-0.8 vs MiniLM 0.4-0.6) more often satisfy the `avg_top3 ≥ 0.55` gate → `response_mode=high` → `step_clarify` shortcut doesn't fire → system answers confidently. 3 of 5 BGE-failing queries are `expected=clarify` — Bin A. MiniLM "won" by accidentally clarifying when its lower scores triggered the shortcut. **No KB or embedding change needed.**

3. **Clarify-prompt fix attempted and reverted (2026-05-08).** Added 3 CAUTION entries + 3 positive examples + 1 negative example to `_UNDERSTAND_PROMPT` to teach the 8B classifier the BGE-failing patterns. Targeted slice landed cleanly: 5/5 BGE-failing queries flipped to PASS in mini-eval; 0 FPs across 54 currently-passing answer queries in the bench. **Then stability checks caught regressions on two pre-existing CAUTION-list queries** (hs-nurse-012 and hs-nurse-014) that had been passing — both flipped from `needs_clarification=True` to `False` (3/3 stable). Both queries are LITERALLY in the existing CAUTION block. Diagnosis: **the 8B classifier has a finite attention budget on long prompts; adding examples — even correct ones — diluted reasoning on the pre-existing examples.** Reverted; baseline 60/80 (75%) holds. Lesson recorded: prompt-engineering on this 8B is fragile to length. Cleaner future paths queued: (a) regex pre-check on the 3 specific Bin A patterns (deterministic, bypasses 8B attention); (b) restructure the existing CAUTION block to use a generalized rule rather than enumerated examples. The "add more examples" approach is ruled out.

**Pre-fix latency reference (Phase 2 close, before fix):** 24.3s avg / 25.6s p50 / 37.8s p95 / 55.8s p99 on full 80; understand 14.9s avg max 28.8s; refusal queries 12.5s avg because understand still ran before short-circuit.

**Cleanup-sprint deliverables (all complete):**
1. Re-ran 26 rate-limited queries from the first BGE pass on fresh quota via `eval/rerun_rate_limited_bge.py` — all 26 returned real answers; 0 still rate-limited. Memory said 23, marker scan found 26 (6 in `hs-cross-*` original-55 + 20 in new-25).
2. Ran `eval/profile_latency.py` on BGE-active config with fresh quota — generate step identified as dominant contributor.
3. Updated `docs/hospital_baseline.md`, `docs/cerna_status_and_pov.md`, `docs/latency_profile.md` with the verified full v2 numbers + per-step diagnosis.

**Surprise finding — flagged for separate sprint:** The new-25 BGE pass rate (80%) is below the MiniLM interim measurement (92%) by **−12 pp**. Concentrated on Clinical new-25 (2/4 vs MiniLM 3/4); other modules within 1 query of parity. Not a content gap (no bad failures; top chunk scores ≥ 0.55 on the failures); the failures are behavior-shape mismatches with solid retrieval underneath. Working theory: the new content was added during the MiniLM-active period and may have language patterns that produce tighter MiniLM cosine similarities than BGE for the rewritten queries the 8B classifier emits. FHIR new-25 actually *improved* on BGE (+25 pp) so the story isn't "BGE worse on new content uniformly" — it's about query-rewriter ↔ embedding-space interaction.

**Per-persona on full 80 (BGE):** nurse 81.8% (18/22), clerk 70.6% (12/17), physician 71.4% (10/14), IT 94.1% (16/17), cross 40.0% (4/10). Cross is the weakest persona and largely Bin A (clarify-shape mismatch).

**Per-module on full 80 (BGE):** FHIR 100% (4/4), Millennium 92.3% (12/13), PowerChart 79.2% (19/24), Revenue Cycle 68.4% (13/19), Clinical 60.0% (12/20).

**Phase 2 fully closed — headline 75% on full v2 (80 queries) on BGE, original-55 at 72.7%, new-25 at 80%, latency dominated by generate step, tractable fix.**

**Active embedding model:** BGE (`COLLECTION=cerner_docs_bge` is production default; MiniLM is A/B / fallback). README updated to reflect.

**Queued for after Phase 3 break (revised after pre-Phase-3 cleanup):**
- ~~New-25 BGE-vs-MiniLM diagnostic~~ — DONE 2026-05-08; gap is gating-side, not retrieval. Tractable fix paths queued: (a) re-tune `avg_top3 >= 0.55` gate for BGE's higher score distribution, OR (b) strengthen the multi-branch clarify heuristic to fire on Bin A patterns regardless of confidence.
- ~~8B-pool fix~~ — DONE 2026-05-08; understand step 3.2× faster.
- **Generate-step optimization** (now the dominant cold step at ~5.8s): either tighten chunks-per-prompt budget (`top_k` 10→6 after MMR) or swap to GPT-5.4 mini per `docs/phase3/llm_swap_design.md`. Phase 3 model-swap is on the existing plan.
- Phase 3 (separate sprint, fresh start).
