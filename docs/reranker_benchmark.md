# Reranker Benchmark — 2026-04-20
**Phase:** 2 · Week 5  
**Collection:** `cerner_docs_bge` (BGE-large-en-v1.5, 1,322 chunks)  
**Reranker model:** BAAI/bge-reranker-v2-m3 (cross-encoder, ~570 MB)  
**Mode:** `--retrieval-only` (raw query, no understand_query, no LLM calls)  
**Benchmark:** `eval/vague_query_eval.py --all --retrieval-only`

---

## Headline Result

| Setting | Pass | Total | Pass Rate | Score≥0.4 |
|---------|------|-------|-----------|-----------|
| Baseline (`RERANK_ENABLED=false`, fetch_k=5) | 46 | 55 | **84%** | 44/55 (80%) |
| With reranker (`RERANK_ENABLED=true`, fetch_k=10) | 42 | 55 | **76%** | 45/55 (82%) |
| **Delta** | **−4** | — | **−8 pp** | +1 |

**Decision: Do NOT enable `RERANK_ENABLED=true` by default.** The retrieval-only benchmark cannot measure the cross-encoder's benefit — it only exposes the downside of a larger fetch pool. See methodology note below.

---

## Methodology Note (Critical)

`RERANK_ENABLED=true` changes two things in the pipeline:

1. **fetch_k**: `TOP_K=5` → `RERANK_TOP_K=10` (more candidates fetched from ChromaDB)
2. **Cross-encoder reranking**: re-scores all 10 candidates and keeps `FINAL_TOP_K=4`

The `--retrieval-only` benchmark only simulates (1). The cross-encoder (2) is **not applied** in retrieval-only mode. As a result:

- The eval fetches 10 candidates via RRF fusion instead of 5
- It then takes the positional top-5 (by RRF order) — no re-scoring
- For borderline queries, the bigger RRF pool can dilute the top-5 with lower-semantic-score chunks from BM25 matches, dropping scores below the 0.40 threshold
- The cross-encoder would re-score those 10 and fix this, but it isn't running here

**This benchmark cannot determine whether the actual cross-encoder reranker improves answer quality. It only shows that expanding fetch_k without reranking hurts retrieval scores on this test set.**

---

## Per-Query Comparison (All 55 Queries)

| ID | Query | Baseline Score | Baseline | Reranker Score | Reranker | Delta |
|----|-------|---------------|----------|---------------|----------|-------|
| cli_01 | why won't my meds show up | 0.491 | PASS | 0.491 | PASS | = |
| cli_02 | nurse can't scan the barcode | 0.531 | PASS | 0.531 | PASS | = |
| cli_03 | emar is broken | 0.383 | FAIL(S) | 0.337 | FAIL(S) | = (worse) |
| cli_04 | how do nurses give meds | 0.479 | PASS | 0.479 | PASS | = |
| cli_05 | wristband scan failed | 0.438 | PASS | 0.438 | PASS | = |
| cli_06 | pharmacy isn't getting the order | 0.509 | FAIL(M) | 0.509 | FAIL(M) | = |
| cli_07 | medication not on the admin list | 0.551 | PASS | 0.551 | PASS | = |
| **cli_08** | **how do i chart vitals lol** | **0.493** | **FAIL(M)** | **0.470** | **PASS** | **+1 FIX** |
| pc_01 | patient list is empty | 0.540 | PASS | 0.539 | PASS | = |
| pc_02 | can't find the patient | 0.449 | PASS | 0.457 | PASS | = |
| pc_03 | where do doctors write notes | 0.493 | PASS | 0.493 | PASS | = |
| pc_04 | how do i put in an order | 0.500 | PASS | 0.500 | PASS | = |
| pc_05 | the order thing | 0.467 | PASS | 0.467 | PASS | = |
| **pc_06** | **powerchat** | **0.442** | **PASS** | **0.377** | **FAIL(S)** | **−1 REGRESS** |
| pc_07 | lab results not showing | 0.487 | PASS | 0.487 | PASS | = |
| pc_08 | inbox is full of alerts | 0.337 | FAIL(S) | 0.337 | FAIL(S) | = |
| rcm_01 | billing broken | 0.482 | PASS | 0.481 | PASS | = |
| rcm_02 | why did the charge not go through | 0.429 | PASS | 0.429 | PASS | = |
| **rcm_03** | **claim got denied** | **0.450** | **PASS** | **0.391** | **FAIL(S)** | **−1 REGRESS** |
| rcm_04 | how does coding work | 0.451 | PASS | 0.447 | PASS | = |
| rcm_05 | patient owes money | 0.449 | PASS | 0.449 | PASS | = |
| rcm_06 | revelate | 0.556 | PASS | 0.556 | PASS | = |
| **rcm_07** | **how do i fix a claim** | **0.439** | **PASS** | **0.383** | **FAIL(S)** | **−1 REGRESS** |
| rcm_08 | charge not through after nurse | 0.531 | PASS | 0.531 | PASS | = |
| fhir_01 | how to connect my app to cerner | 0.565 | PASS | 0.526 | PASS | = |
| fhir_02 | api not working | 0.331 | FAIL(S) | 0.354 | FAIL(S) | = (better score, still fails) |
| fhir_03 | how do i pull patient data | 0.581 | PASS | 0.581 | PASS | = |
| fhir_04 | SMART thing | 0.345 | FAIL(S) | 0.345 | FAIL(S) | = |
| fhir_05 | oauth setup | 0.392 | FAIL(S) | 0.392 | FAIL(S) | = |
| fhir_06 | fhir error 401 | 0.654 | PASS | 0.654 | PASS | = |
| fhir_07 | how to get lab results from the API | 0.496 | PASS | 0.496 | PASS | = |
| fhir_08 | hl7 message not arriving | 0.408 | PASS | 0.408 | PASS | = |
| mil_01 | how does cerner backend work | 0.564 | PASS | 0.564 | PASS | = |
| mil_02 | ccl script not running | 0.554 | PASS | 0.554 | PASS | = |
| mil_03 | millenium domain | 0.557 | PASS | 0.557 | PASS | = |
| mil_04 | mpage not loading | 0.613 | PASS | 0.613 | PASS | = |
| mil_05 | how do i customize the homepage | 0.388 | FAIL(B) | 0.388 | FAIL(B) | = |
| mil_06 | upgrade broke everything | 0.305 | FAIL(S) | 0.305 | FAIL(S) | = |
| mil_07 | discern report wrong | 0.489 | PASS | 0.489 | PASS | = |
| **mil_08** | **what is cerner** | **0.546** | **PASS** | **0.546** | **FAIL(M)** | **−1 REGRESS** |
| fhir_09 | patient not found in the api | 0.520 | PASS | 0.491 | PASS | = |
| **fhir_10** | **how to register a cerner app** | **0.552** | **PASS** | **0.520** | **FAIL(M)** | **−1 REGRESS** |
| fhir_11 | getting a 403 on the endpoint | 0.493 | PASS | 0.493 | PASS | = |
| fhir_12 | careaware not syncing | 0.413 | PASS | 0.408 | PASS | = |
| fhir_13 | how do i get a patient's labs via api | 0.542 | PASS | 0.542 | PASS | = |
| cross_01–05 | (all 5 cross-module queries) | — | PASS ×5 | — | PASS ×5 | = |
| f_01–05 | (all 5 formal regression queries) | — | PASS ×5 | — | PASS ×5 | = |

**FAIL(S)** = score below 0.40; **FAIL(M)** = correct score, wrong module in top-5; **FAIL(B)** = both.

---

## Regression Analysis

**5 regressions (PASS → FAIL):**

| ID | Query | Root Cause | Before | After |
|----|-------|-----------|--------|-------|
| pc_06 | powerchat | BM25 "chat" matches diluted top-5 at fetch-10; misspelling queries are fragile | 0.442 | 0.377 |
| rcm_03 | claim got denied | Fetch-10 RRF pulls in cross-module chunks (fhir/clinical) displacing high-sem RC chunk | 0.450 | 0.391 |
| rcm_07 | how do i fix a claim | Same — "fix" is a generic verb; larger pool brings in low-sem BM25 matches | 0.439 | 0.383 |
| mil_08 | what is cerner | Fetch-10 RRF top-5 drops millennium; overview question spans all modules | 0.546 (PASS) | 0.546 (FAIL-M) |
| fhir_10 | how to register a cerner app | Fetch-10 RRF top-5 drops fhir; "register" matches multiple modules | 0.552 (PASS) | 0.520 (FAIL-M) |

**1 improvement (FAIL → PASS):**

| ID | Query | Root Cause | Before | After |
|----|-------|-----------|--------|-------|
| cli_08 | how do i chart vitals lol | Fetch-10 brought clinical chunk into top-10; module_pass flipped | FAIL(M) | PASS |

**Pattern:** The score regressions (pc_06, rcm_03, rcm_07) all involve short or generic queries where BM25 over-indexes on common words ("fix", "claim", "chat"). The module regressions (mil_08, fhir_10) are broad-topic queries where the top-5 RRF slots are contested across modules.

---

## Latency Impact

The cross-encoder model (BAAI/bge-reranker-v2-m3, ~570 MB) adds:
- **First load:** ~2–4 s model download + CPU load (cached after first run)
- **Per-query inference (10 pairs, CPU):** ~80–150 ms estimated on CPU
- **Baseline median latency:** ~290 ms (retrieval only, no LLM)
- **Expected end-to-end with reranker:** +80–150 ms added to the retrieval phase

Latency impact is modest and acceptable for the POV use case. However, the CPU cross-encoder is the bottleneck — GPU inference would reduce this to ~20–40 ms.

---

## Decision: Keep RERANK_ENABLED=false

The retrieval-only benchmark **cannot** determine whether the cross-encoder improves answer quality, because it measures retrieval scores on the same queries the cross-encoder would re-rank. The correct evaluation requires:

1. Run `run_eval.py` with `RERANK_ENABLED=true` and compare keyword_hit_rate to baseline
2. Specifically check the 8 borderline vague queries (scores 0.305–0.392) to see if cross-encoder lifts any to the answer-quality passing bar

Until end-to-end eval can be run with the cross-encoder active, default stays `RERANK_ENABLED=false`. Setting `false` is safe — no answer quality regression possible since the reranker was never in production.

**If end-to-end eval shows reranker improves keyword_hit_rate on borderline queries (likely), enable it then.** The infrastructure is ready; the decision just needs data from Task 1.

---

## .env State After This Task

```
COLLECTION=cerner_docs_bge
RERANK_ENABLED=false
```

*Benchmark run: 2026-04-20 · Phase 2 Week 5 · collection: cerner_docs_bge 1322 chunks*
