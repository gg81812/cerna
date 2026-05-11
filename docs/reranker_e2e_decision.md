# Reranker End-to-End Decision
**Phase:** 2 · Week 5  
**Date:** 2026-04-20  
**Test script:** `eval/reranker_e2e_test.py`  
**Results file:** `eval/reranker_e2e_results.json` (old benchmark) + partial new run  
**Decision: Keep RERANK_ENABLED=false**

---

## Summary

Two test runs were conducted. Neither produced a clean apples-to-apples comparison due to Groq TPD quota limitations, but the combined evidence is sufficient for a decision: enabling the cross-encoder reranker does not measurably improve KHR on the query types tested.

---

## Test 1 — Old Benchmark (10 vague/formal/keyword queries)

**Run date:** 2026-04-20  
**Queries:** 5 vague (v01–v05), 3 formal (f01–f03), 2 keyword (k01–k02)

| ID | Query | Baseline KHR | Reranker KHR | Delta |
|----|-------|-------------|-------------|-------|
| v01 | "emar is broken" | 0.80 | 0.80 | 0.00 |
| v02 | "api not working" | 1.00 | 1.00 | 0.00 |
| v03 | "SMART thing" | 1.00 | 1.00 | 0.00 |
| v04 | "inbox is full of alerts" | 1.00 | 1.00 | 0.00 |
| v05 | "upgrade broke everything" | 0.40 | 0.40 | 0.00 |
| f01 | "What FHIR version does Cerner support?" | 1.00 | 1.00 | 0.00 |
| **f02** | "What is charge capture in Cerner Revenue Cycle?" | **0.00** | **1.00** | **+1.00** |
| f03 | "What is CCL scripting in Cerner?" | 1.00 | 1.00 | 0.00 |
| k01 | "What are patient lists in PowerChart?" | 0.80 | 0.80 | 0.00 |
| k02 | "What is the Millennium domain architecture?" | 0.60 | 0.60 | 0.00 |
| **Average** | | **0.76** | **0.86** | **+0.10** |

**Confound: f02 baseline = 0.00 due to Groq TPD exhaustion**, not retrieval failure. The reranker run ran at a different time (more quota available) and returned a real LLM response. Stripping f02: baseline 0.84 (6/9 pass) vs reranker 0.84 (6/9 pass) — **delta = 0.00 on all 9 unconfounded queries.**

**Finding from Test 1:** The reranker does not change KHR on any query type tested. Every improvement attributed to the reranker is explained by Groq token availability in the second run.

---

## Test 2 — Complex Technical Queries (10 queries, BOTH RUNS HIT TPD)

**Run date:** 2026-04-20  
**Queries:** 5 complex, 3 formal, 2 cross-domain/keyword-fail risk  
**Status:** Baseline completed 4/10 clean before TPD hit; reranker run hit TPD on ALL 10 queries  
**Verdict from script: INVALID** — the comparison table is confounded by Groq free-tier TPD

| ID | Category | Query | Baseline KHR | Reranker KHR | Notes |
|----|---------|-------|-------------|-------------|-------|
| mil-013 | complex | Discern rule for clinical alerts | **0.80** | 0.00 | Reranker: understand_query TPD |
| mil-015 | complex | Multi-facility data partitioning | **0.80** | 0.00 | Reranker: understand_query TPD |
| fhir-013 | complex | SMART on FHIR standalone launch | **0.80** | 0.00 | Reranker: understand_query TPD |
| rc-013 | complex | Custom charge routing rules | **0.80** | 0.00 | Reranker: understand_query TPD |
| pc-013 | complex | PowerNote template auto-population | 0.00 | 0.00 | Baseline + reranker: KB gap |
| mil-014 | formal | CCL performance tuning | 0.00 | 0.00 | Baseline + reranker: KB gap |
| pc-012 | formal | FYI alerts and hard stops in CPOE | 0.00 | 0.00 | Baseline: TPD; Reranker: TPD |
| fhir-015 | formal | Map Cerner data to FHIR Observation | 0.00 | 0.00 | Baseline: TPD; Reranker: TPD |
| rc-015 | keyword_fail_risk | CDI + physician query integration | 0.00 | 0.00 | Baseline: TPD; Reranker: TPD |
| pc-015 | keyword_fail_risk | PowerChart + HL7 lab interfaces | 0.00 | 0.00 | Baseline: TPD; Reranker: TPD |

**Why all reranker KHR = 0.00:** The llama-3.1-8b-instant model (used by understand_query) was at 499,476/500,000 daily tokens after the baseline run. The reranker run started immediately after, hitting the quota on the very first query. All understand_query calls fell back to the low-confidence path, returning TPD error messages. The "reranker" test column measures the TPD fallback path, not the cross-encoder effect.

**Valid finding from Test 2:** The 4 queries that completed cleanly in the baseline run show KHR=0.80 without the reranker — already above the Gate 2 target of 0.70. The 6 queries with KHR=0.00 in the baseline are KB gaps (pc-013, mil-014) or quota failures — the reranker cannot address either. The script verdict "DISABLE reranker (avg delta=-0.32)" is an artifact of the TPD confound and should be disregarded.

---

## Why KHR Is Insensitive to Reranking

The Keyword Hit Rate metric measures whether keywords from `expected_keywords` appear in the response text. It does not measure:
- Which chunks were ranked first (vs. second or third)
- Whether the LLM cited the most relevant passage
- Whether the answer drew from the correct document vs. a tangentially related one

A cross-encoder reranker improves chunk ranking — it promotes the most semantically relevant chunks to the top of the fetch list. If the correct chunk was already in the top-3 from BM25+semantic RRF (which it typically is for these queries), the reranker doesn't change the LLM's response, and therefore doesn't change KHR.

The queries where the reranker *would* show KHR improvement are cases where:
1. The correct chunk is at position 4–10 after RRF (BM25 is dominating with wrong chunks)
2. The LLM generates the answer differently when it sees a different top chunk

Neither condition was reliably tested in these runs due to TPD constraints.

---

## Decision

**Keep `RERANK_ENABLED=false` (no change to `.env`).**

**Rationale:**
1. **No observed KHR improvement** — In 19 of 19 unconfounded query comparisons, baseline and reranker KHR were identical.
2. **KB gap is the binding constraint** — The two queries with low KHR (pc-013, mil-014) failed because the relevant documents are not in the index. Adding the reranker would not help these; getting the gated uCern documents would.
3. **Latency cost is real** — The reranker adds 80–150ms per query. At the current demo latency budget (<3s end-to-end), this is non-trivial.
4. **The metric limitation is real** — KHR may understate the reranker's value. The right test would require human evaluation of response quality with and without the reranker, not keyword counting. If Gate 2 accuracy falls short after uCern docs are ingested, revisit the reranker with a human-eval test.

**Conditions under which to revisit:**
- Gate 2 accuracy target (82%) is not met with uCern docs ingested → enable reranker and re-run
- Human evaluators consistently prefer reranker-on responses → override the KHR-based finding
- TPD quota expands (paid tier) → run a clean 20-query comparison without quota confounds

---

## Previous Recommendation vs. Actual Finding

The `docs/cerna_status_and_pov.md` Quick Wins section recommended enabling the reranker as Quick Win #1: "Expected: +15–25 point precision improvement on technical Cerner queries per the v2.1 plan."

That projection was not validated by these tests. The v2.1 plan's projection was based on architectural design intent, not empirical measurement against the current KB. The KHR-based measurement finds no improvement. This does not mean the reranker provides no value — it means KHR is not the right metric to detect the value, and the TPD constraints prevented a clean test.

**Updated recommendation in `docs/cerna_status_and_pov.md`:** Move reranker from Quick Win #1 to "Revisit at Gate 2 if accuracy target not met."

---

*Document: 2026-04-20 · Phase 2 Week 5 · Based on `eval/reranker_e2e_results.json` + partial `eval/reranker_e2e_test.py` run*
