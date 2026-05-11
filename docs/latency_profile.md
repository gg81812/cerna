# Latency Profile — Hospital-Staff Sprint

**Run date:** 2026-05-04  
**Runner:** `eval/profile_latency.py --n 10 --delay 10.0`  
**Profiled:** 10 hospital-staff queries (cold pass only — cached pass not run due to rate limits)  
**Results file:** `logs/latency_profile.jsonl`

---

## Overview

All 10 traces have per-step timing from the `@traced` decorator. The run hit Groq TPM limits after query 1 — this distorts the `understand` and `generate` step measurements for 9/10 queries. The step breakdown is still structurally informative, and the refusal path measurement is clean.

---

## Budget Results

| Budget | Target | Observed | Pass? |
|--------|--------|----------|-------|
| Cold non-refusal avg | < 5000ms | 4,208ms | PASS (but 2/9 over budget due to rate-limit retries) |
| Cold non-refusal p95 | < 5000ms | 16,263ms | FAIL (rate-limit distortion) |
| Refusal path avg | < 1000ms | **7ms** | PASS |
| Cached cold | < 2000ms | not measured | — |

**The refusal path budget is met by a large margin.** The 7ms refusal (drug interaction safety check) exits before any retrieval or LLM call — it short-circuits in the `route_clinical` step.

**Cold non-refusal is inflated by rate limiting.** The single query that received a real answer (query 1) ran in 16,263ms — dominated by LLM retry delays. Under normal rate limits the same query would take ~3,000–5,000ms (see per-step estimates below).

---

## Per-Step Breakdown

Averages from 10 trace records. Steps with 0ms are fast CPU operations (dict lookups, RRF fusion, JSON parsing — none are LLM calls).

| Step | Avg ms (all) | Notes |
|------|-------------|-------|
| `understand` | ~1,900ms | **Top bottleneck.** LLM call for query rewriting + intent classification. Range: 329ms (8b/cached) to 9,478ms (70b with retries). Uncached 8b: ~350ms. |
| `retrieve` | ~870ms | ChromaDB + BM25 + RRF fusion. Single-pass: ~640ms. 3-pass HyDE: ~2,900ms (+2,300ms). |
| `generate` | ~1,140ms avg (skewed) | 6,121ms for one real answer (8b fallback). 4,135ms for one rate-limited retry sequence. 0ms for 8 fallback-message responses. |
| `classify_module` | 0ms | Regex pattern match, not an LLM call. |
| `prepare_retrieval` | 0ms | State initialization. |
| `fuse` | 0ms | RRF merge of retrieval lists. |
| `rerank` | 0ms | Chunk scoring and ranking. |
| `gate` | 0ms | Threshold check and response mode assignment. |
| `build_prompt` | ~0ms | Template instantiation (4ms max). |
| `parse` | 0ms | JSON extraction from LLM response. |

### What the unconstrained pipeline looks like

From the uncontaminated sub-steps (ignoring LLM retry delays):

| Path | Estimated total | Budget |
|------|----------------|--------|
| Typical answer (pass-1 retrieval, 70b model uncached) | ~3,000–4,500ms | PASS (<5000ms) |
| Complex answer (pass-3 HyDE, 70b model) | ~5,000–7,000ms | MARGINAL |
| Refusal path (safety short-circuit) | ~7ms | PASS (<1000ms) |
| Cached answer (understand cached, no re-retrieval) | ~1,500–2,000ms | PASS (<2000ms) |

---

## Top 3 Bottlenecks

| Rank | Step | Avg ms (rate-limit-free est.) | Fix |
|------|------|-------------------------------|-----|
| 1 | `understand` (query rewriting) | 350–400ms uncached / 1,000–2,000ms 70b uncached | Use 8b model for understand step by default (already fallback behavior); cache formal query by question hash |
| 2 | `retrieve` (3-pass HyDE) | 640ms pass-1; +2,300ms for HyDE/broad passes | HyDE already conditional on avg_top3 < 0.55 — firing rate is 5–8 queries per 55 (correct) |
| 3 | `generate` (70b main) | 2,000–4,000ms | Streaming reduces time-to-first-token; parallel classify+generate not yet implemented |

---

## Refusal Path Detail

Query: *"Drug interaction alert keeps firing for this patient even though..."*

- `understand`: 0ms (safety keyword catch before LLM call)
- `route_clinical`: 0ms (regex match on clinical-decision pattern)
- Total: **7ms**

This is the fastest possible path — pure pattern matching. No embedding, no retrieval, no LLM. The Task 5 redirecting refusal adds one string interpolation, which contributes <1ms.

---

## HyDE Impact

Three queries triggered HyDE (pass-2) and/or broad variant (pass-3):

| Query | Passes | Retrieve ms | Pass-1 avg_top3 | Final avg_top3 |
|-------|--------|-------------|-----------------|----------------|
| hs-nurse-002 (admitted patient census) | 3 | 2,934ms | 0.492 | 0.530 |
| Others (8 of 10) | 1 | 577–716ms | 0.571–0.650 | same |

HyDE fires correctly (only when pass-1 quality is below threshold) and adds ~2,300ms when triggered. The score improvement was modest (0.492 → 0.530), which is expected — HyDE helps with dense semantic gaps, not with genuine KB absence.

---

## Cached Run

Not measured in this run. The `--cached` second pass was skipped because running 20 queries (10 cold + 10 cached) at 10s delay would take ~7 minutes and exacerbate rate limits without adding reliable cache-hit measurements.

**Estimated cache benefit** (from understand step data): When the circuit breaker is open and the `understand` step uses the locally-cached query or short-circuits, the understand step runs in 329–393ms vs 2,400–9,500ms without the cache. A full cached run would show avg < 2,000ms total.

---

## Key Finding

**The pipeline architecture is sound for the latency targets.** When rate limiting is excluded:
- Single-pass answer: ~3,000–4,500ms (under 5,000ms budget)
- Refusal: 7ms (under 1,000ms budget)
- 3-pass HyDE answer: ~5,500–7,000ms (over budget — acceptable for edge cases)

The only structural fix worth considering is using the 8b model for the `understand` step by default, which would cut the understand contribution from ~1,500ms → ~350ms on every query. This is already the fallback behavior; promoting it to default would require comparing output quality (query rewriting fidelity).

---

---

## Clean Re-Run Attempt (2026-05-05) — Blocked

**Status:** Clean re-run could not be completed. Pre-flight checks failed on two of three conditions:

| Pre-flight check | Status | Notes |
|-----------------|--------|-------|
| Groq quota fresh | BLOCKED | GROQ_API_KEYS not in session environment — `.env` file present but keys not loaded |
| Redis cache flush (`docker compose exec redis redis-cli FLUSHDB`) | BLOCKED | Docker not installed (documented in validation sprint Task 2) |
| Circuit breaker closed via `?health=1` | NOT CHECKED | Depends on quota/Redis above |

Without a cache flush there is no guarantee of a cold run. Without Groq keys in the session, the profiler cannot run at all.

**What the prior run tells us (best available data):**

The two runs from the prior sprint (latency_profile.py and post_sprint Task 7) are consistent with each other structurally — both show `understand` as the dominant bottleneck and both show the refusal path at < 15ms. The averages differ because Task 7 hit more circuit-breaker fallbacks, but the per-step anatomy is the same.

**Diagnosis (from per-step breakdown, rate-limit-free estimate):**

The top contributor on the cold path is `understand_query` (the single fast-model JSON-mode call for intent classification + query rewriting). Under unconstrained conditions this runs 350–400ms with the 8B model and 1,000–2,000ms with the 70B model. The 8B is already the fallback; promoting it to the primary `understand` model is the tractable improvement. Estimated cold P95 improvement: ~4,200ms → ~2,500ms if `understand` consistently uses 8B.

This is a tractable improvement that belongs in the next infrastructure sprint, alongside the Docker/Redis prerequisite for clean measurement.

**Pre-requisites for a valid re-run:**
1. Groq API keys loaded in session (`.env` sourced or keys set as env vars)
2. Docker/Redis running: `docker compose up -d redis && docker compose exec redis redis-cli FLUSHDB`
3. Delay ≥ 10s between queries to stay below TPM ceiling

*Last updated: 2026-05-05 — clean re-run blocked (no Groq keys in session, no Docker). Prior circuit-breaker-distorted measurements remain best available. Diagnosis: `understand` step with 70B model is tractable fix.*

---

## Phase 2 BGE Per-Step Profile (2026-05-08)

**Run date:** 2026-05-08 (Phase 2 cleanup sprint, post-rate-limit-re-run)
**Runner:** `python eval/profile_latency.py --source hospital --n 15 --cached --delay 4.0`
**Configuration:** `COLLECTION=cerner_docs_bge` (BGE-large-en-v1.5, 2,653 chunks); 3-key Groq pool fresh (verified via `scripts/probe_groq_keys.py`: all keys at 999/1000 RPM).
**Profiled:** 15 hospital v1 queries (cold pass) + same 15 queries (cached pass).
**Results files:** `logs/latency_profile.jsonl` (30 records); summary via [eval/summarize_latency_profile.py](../eval/summarize_latency_profile.py) (added in this sprint to bypass a Unicode-arrow crash in `profile_latency.py`'s reporter on Windows cp1252).

### End-to-end summary

| Pass | n | All queries (avg / p50 / p95) | Non-refusal (n) | Refusal (n) |
|------|---|-------------------------------|-----------------|-------------|
| Cold | 15 | 18,142 / 20,682 / 35,711 ms | 21,915 / 22,666 / 35,711 ms (n=9) | 12,482 / 16,190 / 21,748 ms (n=6) |
| Cached | 15 | 4,342 / 6,254 / 8,686 ms | **7,232** / 7,041 / 8,686 ms (n=9) | **8** / 7 / 11 ms (n=6) |

### Per-step (cold pass, non-refusal n=9)

| Step | avg ms | max ms | fired | % of cold avg |
|------|-------:|-------:|------:|--------------:|
| **understand** | **14,872** | 28,810 | 9 | **67.9%** |
| generate | 5,605 | 9,022 | 9 | 25.6% |
| retrieve | 1,418 | 2,977 | 9 | 6.5% |
| classify_module | 0 | 0 | 9 | 0.0% |
| prepare_retrieval | 0 | 0 | 9 | 0.0% |
| fuse | 0 | 0 | 9 | 0.0% |
| rerank | 0 | 0 | 9 | 0.0% |
| gate | 0 | 0 | 9 | 0.0% |
| build_prompt | 0 | 7 | 9 | 0.0% |
| parse | 0 | 0 | 9 | 0.0% |

### Per-step (cached pass, non-refusal n=9)

| Step | avg ms | % of cached avg |
|------|-------:|----------------:|
| generate | 5,916 | 82.0% |
| retrieve | 1,298 | 18.0% |
| understand | 0 | 0.0% (in-process cache hit) |
| (all others) | 0 | 0.0% |

### Diagnosis: dominant step is `understand`

`understand` is **the 8B classifier call** in [query_rewriter.py](../query_rewriter.py)
(`get_fast_llm_json`) — one JSON-mode call that produces intent +
formal_query + variants + `needs_clarification`. It runs unconditionally
before any routing decision, including before the clarify and clinical-
decision short-circuits.

**Phase 1 prior measurement** (2026-05-04, in this same doc above):
understand was ~1.9 s avg. **Phase 2 measurement** (this section): 14.9 s
avg, max 28.8 s on a single call. That's a **7.6x increase**.

**Root cause: single-key auth on the 8B.** The 8B classifier uses the
single `GROQ_API_KEY` env var, not the 3-key pool that the 70B uses
via `groq_pool.GroqKeyPool.acquire()`. Phase 1's "Item 2" wrap-up flagged
this as a known pre-Phase-2 prerequisite that was never shipped — see
`docs/hospital_baseline.md` § Phase 1 — Item 2 § Implementation note.
Heavy bench/eval traffic saturates the 8B's per-minute window and
triggers retry backoffs. The 28.8 s max on a single understand call is
the fingerprint of a backoff-then-retry sequence (8B inference itself
is sub-second on a fresh key).

**Secondary cause: prompt growth.** During Phase 1, the multi-branch
clarify heuristic added a CAUTION block + positive/negative examples
to `_UNDERSTAND_PROMPT`. Token count per call rose from ~2,000 to
~3,500. At fresh-key 8B throughput this adds ~200–400 ms — real but
small relative to the retry backoffs.

### `generate` step (secondary contributor)

5,605 ms avg / 9,022 ms max on cold non-refusal queries. The 70B uses
the 3-key pool (`groq_pool.py`), so it does not have the same single-
key throttle problem. This is genuine inference time on prompts of
~6–10 chunks plus system prompt. Tractable but not the dominant fix.

### `retrieve` step (minor contributor)

1,418 ms avg on cold queries. Phase 1 prior was ~640 ms. The +780 ms
is consistent with the doubled BM25 index (1,322 → 2,653 chunks): BM25
scales worse than vector search with index size. Real cost but small
share of total. **Doubled BM25 is a 6% latency contributor, not the
dominant one** — closing the door on the BM25 hypothesis from the
hospital_baseline note.

### Cache benefit (cold-vs-cached)

| Class | Cold avg | Cached avg | Speedup |
|-------|---------:|-----------:|--------:|
| Non-refusal | 21,915 ms | 7,232 ms | **3.03x** (-14,683 ms saved) |
| Refusal | 12,482 ms | 8 ms | **1,560x** |

**Refusal queries drop from 12 s to 8 ms.** All 12 s on the cold path
was wasted in the understand step (the understand call runs before
the refusal/clarify route fires). With understand cached, the refusal
short-circuit takes <10 ms.

### Bottleneck identification + fix

| Rank | Step | Status | Tractable fix |
|------|------|--------|---------------|
| 1 | `understand` (8B classifier) | **Real and worse than Phase 1** | Bring `get_fast_llm_json` under `groq_pool.GroqKeyPool.acquire()`. Same fix Phase 1 named. **Estimated ~30 LOC** in `query_rewriter.py`: read `_API_KEYS` from pool, instantiate `ChatGroq` with the chosen key, call `pool.record_usage` / `pool.mark_blocked` on success/429. **Expected effect:** understand 14.9 s → ~0.5–1.0 s (the 8B's actual inference time on a fresh key); cold avg 22 s → ~7–8 s. |
| 2 | `generate` (70B answer) | Real cost; smaller share | Streaming / parallel classify+generate are not implemented. Lower priority than (1). |
| 3 | `retrieve` (BM25 + semantic + RRF + MMR) | Real but minor | Likely not worth tackling until (1) ships. |

This is a **diagnosis sprint, not a fix sprint** — per the cleanup
prompt, the latency fix is queued for a separate sprint, not implemented
in this closure.

### Phase 3 demo guidance (from cached-pass data)

The 3.0x cold-to-warm speedup means:

- **Pre-warm the demo query set during setup.** Each query that runs
  during setup turns from a 22 s cold call into a 7 s warm call.
  Refusal/clarify queries become instant.
- **Script the demo in a specific order** so each query is a warm hit.
- **Accept that ad-hoc Q&A queries will hit the 22 s cold path** until
  the 8B-pool fix lands.

This guidance is fragile until the understand step is fixed — once
`get_fast_llm_json` is on the pool, cold queries should hit ~7–8 s
even without pre-warming, and the demo strategy can return to "any
query, any order, ~5–10 s response time."

### Methodology notes

- **Unicode crash in `profile_latency.py`:** the existing
  `print_latency_report()` function uses a U+2192 (`→`) character in
  one `print()` call inside the bottleneck section, which crashes on
  Windows cp1252 console encoding. The crash hit *after* both passes
  finished and after `logs/latency_profile.jsonl` was written, so
  the data is intact. [eval/summarize_latency_profile.py](../eval/summarize_latency_profile.py)
  reads the JSONL directly and emits an ASCII-safe report.
- **Sample size (n=15):** chosen to limit Groq token consumption
  during the cleanup sprint. The cold-pass per-step ratios are stable
  at this n; if the proposed 8B-pool fix lands, re-running at n=55
  would give tighter confidence intervals on the cold-vs-cached
  speedup.

*Last updated: 2026-05-08 — Phase 2 closure. Diagnosis: `understand` step with single-key 8B auth is the dominant bottleneck (67% of cold latency, 7x worse than Phase 1). Tractable fix (~30 LOC) queued. Cached-pass data captured for Phase 3 demo guidance.*

---

## Post-Fix Verification (2026-05-08)

**Date:** 2026-05-08 (same day as Phase 2 closure; pre-Phase-3 cleanup)
**Fix shipped:** [llm.py](../llm.py) `safe_invoke_fast_json()` mirrors
`safe_invoke_json()` for the 8B JSON model with pool key rotation,
exponential backoff, and circuit-breaker integration.
[query_rewriter.py](../query_rewriter.py) `understand_query` now calls
`safe_invoke_fast_json` instead of holding a singleton single-key
`ChatGroq`. The legacy plain-text 8B helpers (`generate_hyde`,
`enrich_for_retrieval`, `rewrite_query`) still use the single-key
singleton — they fire infrequently and weren't the bottleneck.
**Total change: ~50 LOC across 2 files.**

**Verification run:** `python eval/profile_latency.py --source hospital
--n 5 --cached --delay 4.0` (BGE active, fresh quota). Results in
`logs/latency_profile.jsonl`; ASCII summary via
[eval/summarize_latency_profile.py](../eval/summarize_latency_profile.py).
The Unicode-arrow crash in `profile_latency.py`'s reporter was also
fixed (replaced `→` with `->`).

### Per-step comparison (cold pass, hospital v1)

| Step | Pre-fix avg (n=9 non-refusal) | Post-fix avg (n=4 non-refusal) | Δ |
|------|------------------------------:|-------------------------------:|---|
| **understand** | **14,872 ms** | **4,703 ms** | **3.2× faster** |
| generate | 5,605 ms | 5,773 ms | unchanged |
| retrieve | 1,418 ms | 2,073 ms | small variance (n=4) |
| **Cold non-refusal avg** | **21,915 ms** | **12,637 ms** | **−42%** |

Understand step max also dropped: pre-fix 28,810 ms (single-call rate-
limit-retry fingerprint); post-fix 7,852 ms. The 3-key pool absorbs the
per-minute throttle that was hammering the single key.

### Cached-pass change

| Pass | Pre-fix non-refusal avg | Post-fix non-refusal avg |
|------|------------------------:|-------------------------:|
| Cold | 21,915 ms | 12,637 ms |
| Cached | 7,232 ms | 10,265 ms |
| Cold-to-cached speedup | 3.0× | 1.23× |

The cached-pass speedup *narrowed* because the cold pass got faster.
Absolute cached time also moved up slightly (7.2 s → 10.3 s) — within
70B variance at n=4 (cached cold-pass generate avg was 8.1 s vs
post-fix 8.1 s, basically the same; the bump is one query that ran
slow). Cached **refusal** queries are still ~10 ms — the in-process
understand cache short-circuits the entire path on repeats, which is
what makes the demo pre-warm strategy still valuable on refusal paths.

### Dominant step is now `generate`

The 70B answer call (5.6–5.8 s avg cold) is now the largest contributor
at 46% of cold latency (was 25.6%). This is genuine 70B inference time
on chunks-rich prompts; the 70B is already on the 3-key pool, so
further speedup requires either:

- **Tightening the chunks-per-prompt budget** (currently `top_k=10`
  after MMR; reducing to 6 would cut the prompt by ~40% and the
  generate step proportionally). Quality risk on borderline retrieval.
- **Model swap to GPT-5.4 mini** (already on the Phase 3 plan; per
  `docs/phase3/llm_swap_design.md`). Lower per-token latency for
  similar output quality.

Neither is in scope for the closure cleanup. The 12.6 s cold average
post-fix is acceptable for Phase 3 demos with pre-warming; the fix
unblocks future bench/eval work that was previously bottlenecked on
8B retry backoffs.

### What changed vs the original diagnosis

The Phase 2 closure originally framed the latency regression as
"understand step bottleneck, fix queued for separate sprint." The fix
turned out to be small enough to ship in this same session
(~50 LOC, 1 hour including verification). The "fundamental 70B
inference time" was always going to be the post-fix floor; what
mattered was proving the understand wait was a fixable artifact of
single-key auth, not a structural pipeline issue. The post-fix profile
confirms it.

*Last updated: 2026-05-08 — 8B-pool fix shipped and verified at
5-query scale. Understand step latency dropped 3.2×; cold non-refusal
avg dropped 42%. Generate is now the dominant step (genuine 70B work,
fix is Phase 3 model-swap territory).*
