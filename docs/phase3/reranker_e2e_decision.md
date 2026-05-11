# Phase 3 Design: Reranker End-to-End Validation
**Status:** Decision pending — enable vs. permanently disable  
**Context:** Reranker coded, integrated, currently disabled (`RERANK_ENABLED=false`)  
**Related doc:** `docs/reranker_e2e_decision.md` (prior test results)  
**Timing:** Run after uCern decision lands and any new content is ingested

---

## Problem

The BAAI/bge-reranker-v2-m3 cross-encoder reranker is fully implemented in `reranker.py`, integrated into `pipeline.py`, and disabled by a configuration flag. The prior decision to keep it disabled (`docs/reranker_e2e_decision.md`, 2026-04-20) was based on two test runs both confounded by Groq TPD quota exhaustion. The finding was that KHR showed no improvement — but this is likely a metric limitation, not a true null result.

**The unresolved question:** Does the reranker improve response quality on queries where the correct chunk is not in the top-3 after BM25+semantic RRF? The prior tests couldn't answer this because KHR measures keyword presence in responses, not chunk rank position, and the TPD confounds prevented a clean end-to-end comparison.

The decision to disable was defensible for Phase 2 (latency cost not justified by uncertain benefit; KB coverage gap is the binding constraint). For Phase 3, after uCern docs are ingested and the KB coverage gap is substantially closed, the reranker may provide measurable improvement specifically on queries that have multiple plausible candidate chunks at similar relevance scores.

---

## Why the Prior Test Was Insufficient

The Phase 2 reranker test used Keyword Hit Rate (KHR) — whether words from `expected_keywords` appear in the response. KHR is insensitive to chunk rank order because:

1. A response generated from the 3rd-ranked chunk is likely to contain the same keywords as one generated from the 1st-ranked chunk, if they're about the same topic.
2. The cross-encoder only matters when there are semantically similar chunks at competing rank positions and the LLM would give a different (better) answer if it saw the top-ranked chunk.

The reranker's actual value is on queries where: (a) the correct chunk is at position 4–8 after RRF (not in the top-3 fetched), or (b) two chunks appear equally relevant but one is semantically closer to the query. Neither condition is captured by KHR.

The right test measures **response quality** on borderline queries — queries where Cerna currently gives a partial or uncertain answer. This requires human evaluation, not a keyword counter.

---

## Proposed Test Design: 15-Query Human Eval

### Query Selection

Select 15 queries from three categories:

**Category A (8 queries): Borderline vague queries from Phase 2 failures.** These are the queries in `docs/final_eval_vague.md` that passed at the 0.40 threshold but produced low-confidence or marginal responses. These are the cases most likely to benefit from better chunk ranking.

**Category B (5 queries): Formal benchmark queries from `docs/post_cleanup_benchmarks.md`.** These currently produce strong results. The reranker should not regress them. If any formal benchmark query gets worse with the reranker, do not enable.

**Category C (2 queries): Keyword-mismatch golden-eval failures.** Queries where the expected answer chunks are not being retrieved by BM25+semantic. Reranking after broader retrieval (top-20 instead of top-10) might surface the correct chunk.

### Test Procedure

1. Run each query twice: once with `RERANK_ENABLED=false` (baseline) and once with `RERANK_ENABLED=true`.
2. For each pair, record: (a) which chunks appear in the context, (b) the full response text.
3. A human evaluator (someone who knows Cerner workflows) rates each response pair on: accuracy, completeness, and whether the correct primary source was cited.
4. Decision criterion: if the reranker improves ≥3 of 15 queries without regressing any Category B query, enable it. Otherwise keep disabled with documentation.

### Important: No TPD Confound

Run the baseline and reranker test on the same day, with a 4-hour gap between runs, on a Groq paid tier or after midnight UTC when the free-tier budget resets. The Phase 2 test was invalidated by TPD exhaustion mid-comparison. This cannot happen again.

---

## Trade-offs

**Latency: 80–150ms additional per query on CPU**

At current median latency of 2–4s, adding 100ms is a 3–5% increase. Imperceptible to users. Non-trivial if the reranker is running synchronously in a low-latency path, but Cerna's latency is dominated by the 70B generation call, not retrieval. Acceptable.

**Memory: ~570MB for bge-reranker-v2-m3**

The model is already downloaded and cached (loaded in `reranker.py` on import). No additional download required. The memory footprint is additive to the BGE embedding model (~1.3GB). Total memory with both models loaded: ~1.9GB. Acceptable for a server deployment; tight for a laptop demo.

**Fetch-then-rerank: top-20 fetch vs. top-10**

The reranker is most valuable when it has more candidates to reorder. Currently the retriever fetches top-10 (5 semantic + 5 BM25). For the reranker test, consider fetching top-20 to give the cross-encoder more candidates. This increases retrieval latency slightly (~20ms) but improves the reranker's working set.

**Metric vs. human eval**

KHR-based automation is fast but insensitive to reranker value. Human eval is accurate but slow (2–3 hours for 15 query pairs). The Phase 3 test should use human eval. Do not repeat the KHR-only test; it cannot detect the signal.

---

## Decision Criteria (Operationalized)

| Outcome | Decision |
|---------|---------|
| Reranker improves ≥3 of 15 queries, no Category B regression | Enable `RERANK_ENABLED=true` in production `.env`. Document improvement cases. |
| Reranker improves 1–2 queries, no regression | Keep disabled. Benefit too small to justify memory/latency cost. |
| Any Category B query regresses | Keep disabled regardless of other improvements. Formal benchmarks are the floor. |
| Ambiguous results (disagreement among evaluators) | Keep disabled. Burden of proof is on enabling, not disabling. |

---

## Timing Constraint

**Do not run this test before uCern documents are ingested.** The Phase 2 decision confirmed that the binding constraint is KB coverage, not chunk ranking. Running the reranker test now and finding it unhelpful is not informative — the KB will change materially when uCern docs arrive, and the reranker's value may be different on a larger, higher-quality KB.

Correct sequence:
1. uCern decision lands (2026-04-26)
2. If Scenario A: ingest the 14 uCern documents, re-run vague query eval to confirm no regression
3. Run the 15-query reranker human eval on the updated KB
4. Decision: enable or permanently disable

If Scenario B or C (uCern access not obtained): run the reranker test on the current KB as-is, since the KB won't change materially. This is a lower-priority decision in that scenario since the accuracy target may be harder to reach with archival-only content regardless.

---

## Effort Estimate

| Task | Duration |
|------|----------|
| Query selection (15 from existing eval sets) | 1 hour |
| Two test runs (baseline + reranker, with TPD guard) | 3 hours |
| Human evaluation of 15 query pairs | 2–3 hours |
| Decision write-up and config update | 1 hour |
| **Total** | **~0.75 to 1 day** |

---

*Design doc: Phase 3 Reranker E2E Decision · Cerna · 2026-04-22*
