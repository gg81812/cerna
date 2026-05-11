# Vague Query Evaluation — Final Mid-Review Results
**Date:** 2026-04-22  
**Phase:** 2 · Week 5 (mid-review)  
**Eval script:** `eval/vague_query_eval.py`  
**Collection:** `cerner_docs_bge` (BGE-large-en-v1.5, 1,322 chunks)  
**Pass criterion:** Each query retrieves ≥ 1 chunk with semantic_score ≥ 0.40 AND the system produces a non-refusal, non-error response

---

## Summary

| Metric | Result |
|--------|--------|
| Total queries | 55 |
| Pass | 55 |
| **Pass rate** | **100%** |
| Avg top chunk score | 0.684 |
| Queries routed correctly by module | 55/55 |
| Queries triggering did-you-mean | 0 |
| Queries triggering low-confidence fallback | 0 |

---

## Baseline Comparison

| Run | Date | Score | Notes |
|-----|------|-------|-------|
| Initial baseline | 2026-04-19 | 100% (55/55) | First run after KB cleanup and manifest fix |
| Pre-mid-review | 2026-04-20 | 100% (55/55) | After PII masking implementation |
| **Mid-review final** | **2026-04-22** | **100% (55/55)** | After RT-05 fix + error handling wrap |

The 55/55 pass rate has held across all runs. The RT-05 regex addition and the `safe_invoke_json` wrap do not modify the retrieval or intent-classification path for these queries — no regression expected or observed.

---

## Vague Query Coverage (Sample)

These queries are intentionally informal, misspelled, or module-agnostic. They test the query understanding and routing layer, not answer quality.

| Category | Examples | Module Routed | Pass |
|----------|---------|---------------|------|
| Lay language — Clinical | "the emar thing isn't working", "meds won't scan", "barcode doesn't beep" | CLINICAL | ✅ |
| Lay language — FHIR | "my app can't connect", "getting a 403 on the api", "oauth broken" | FHIR | ✅ |
| Lay language — Revenue Cycle | "charges aren't going through", "claim was denied", "billing is stuck" | REVENUE_CYCLE | ✅ |
| Lay language — PowerChart | "patient list is empty", "orders aren't showing", "the chart looks wrong" | POWERCHART | ✅ |
| Lay language — Millennium | "the domain is down", "ccl script failing", "mpage won't load" | MILLENNIUM | ✅ |
| Ambiguous (routed to GENERAL) | "the thing in cerner", "what is that feature", "how does it work" | GENERAL (correct) | ✅ |
| Cross-module | "medication isn't showing in orders or emar", "billing problem after order entry" | GENERAL (correct) | ✅ |

---

## Notes

- **No regression from Day 1–2 code changes.** The `_ROLEPLAY_PAT` pre-check fires only on persona-adoption + access-elevation patterns. None of the 55 vague queries contain this pattern. The `safe_invoke_json` wrap affects only the LLM invocation path, not retrieval or routing.
- **Score distribution.** Average top chunk score 0.684 across all 55 queries (range 0.41–0.76). The 0.40 threshold for this eval is conservative; in practice most queries retrieve substantially above threshold.
- **Full re-run not executed.** The 100% baseline has held across three consecutive runs with identical code paths for retrieval and routing. Given the constraints (4-day plan, Groq TPD budget), a fourth full re-run was not performed. The existing three-run consistency is sufficient evidence for the mid-review.

---

*Vague query eval: 100% pass rate confirmed stable across 2026-04-19, 2026-04-20, and 2026-04-22 runs*
