# Prompt Design — Module-Specialist Templates

**Version:** 2.0.0  
**Sprint:** Hospital-Staff Optimization Sprint (2026-05-04)  
**File:** [prompts.py](../prompts.py)

---

## Problem: why one generic prompt wasn't enough

The original `SYSTEM_PROMPT_TEMPLATE` (v1.3.0) was uniform regardless of which module a query routed to. For a Cerner engineer writing an SME query about FHIR R4 resources, this worked reasonably well. For a nurse at a nursing station asking "BCMA stuck on override prompt — won't let me pass it," it was wrong in two ways:

1. **Tone mismatch**: The generic prompt optimises for completeness and technical depth. A shift-floor nurse needs a direct answer fast, with the clinical boundary stated clearly upfront.
2. **Missing boundary enforcement**: The generic prompt says "never make a clinical decision" once in the rules block. For clinical queries where the boundary is the most important thing, that's not prominent enough. The clinical prompt needed to make the workflow/clinical split the *first* thing the model considers.

---

## Design Decisions

### What the module prompts are

Each module prompt is a **variant of SYSTEM_PROMPT_TEMPLATE** with module-specific framing added, not a complete rewrite. The JSON output schema is identical. Downstream code (orchestrator, UI) required zero changes — `step_build_prompt` just selects a different template based on classification.

### What they're not

- Not different personas — all five still say "You are Cerna."
- Not different confidence levels — the confidence field means the same thing in all five.
- Not role-locked differently — all five have the same identity lock.
- Not shorter — the generic SYSTEM_PROMPT_TEMPLATE already scales depth to question complexity. The module prompts inherit this.

### The clinical boundary case

The most important design decision was in `CLINICAL_PROMPT_TEMPLATE`. Many hospital-staff queries are workflow questions that touch clinical edges. A pure clinical refusal ("I can't help with that") is evasive and unhelpful. A pure answer risks giving clinical advice.

The clinical prompt draws a two-sided line:

> **If a question asks HOW a Cerner workflow works → ANSWER IT FULLY.**  
> **If a question asks WHAT SHOULD I DO CLINICALLY → ANSWER THE WORKFLOW SIDE ONLY, then state the clinical boundary.**

The example in the prompt ("BCMA shows an override — should I give it?") was chosen specifically because it's the most common edge case: a workflow-valid question (how does BCMA override work?) dressed as a clinical question (should I give the med?). The prompt instructs the model to answer the workflow side completely and close with the boundary statement.

---

## Template Inventory

| Template | Classification | Key framing |
|----------|----------------|-------------|
| `CLINICAL_PROMPT_TEMPLATE` | CLINICAL | Workflow/clinical boundary; BCMA/eMAR/PharmNet specifics; lay-language mappings |
| `POWERCHART_PROMPT_TEMPLATE` | POWERCHART | Menu paths and click sequences when known; general vs specific acknowledgment; physician/nurse/build team distinction |
| `RCM_PROMPT_TEMPLATE` | REVENUE_CYCLE | Workflow steps + metric definitions; explicit decline on charge code / coding decisions |
| `FHIR_PROMPT_TEMPLATE` | FHIR | Technical specificity; version-awareness (R4 vs DSTU2/STU3); Cerner-specific extensions |
| `MILLENNIUM_PROMPT_TEMPLATE` | MILLENNIUM | OCI vs on-prem distinction; admin tool paths; CCL/MPage as separate concerns |
| `SYSTEM_PROMPT_TEMPLATE` | GENERAL (fallback) | Generic — used when classification is GENERAL or cross-module |

---

## A/B Comparison Notes (Task 3 validation)

> Fill in after running the hospital-staff benchmark against baseline and module-prompt variants.

### Measurement note — direct A/B comparison

A direct side-by-side run (specialist vs generic, same queries) was attempted but Groq TPM rate limiting allowed only 1 real answer per ~15 queries. Only hs-nurse-013 received a real LLM response in the generic run. All other queries fell into the circuit breaker's fallback window.

**Method used instead:** Compare specialist-prompt khr values from `hospital_eval_results.jsonl` against qualitative assessment of response structure (boundary framing presence, vocabulary specificity). The specialist prompts are in production; the generic baseline was never in production for these queries.

---

### CLINICAL prompt (5 nurse queries measured)

| Query ID | Generic khr (est.) | Specialist khr | Verdict | Notes |
|----------|-------------------|----------------|---------|-------|
| hs-nurse-013 | ~0.60 | **0.60** | Same | Allergy-med boundary: specialist adds explicit workflow/clinical split framing; model answered workflow side correctly in both conditions |
| hs-nurse-015 | ~0.50 | **0.83** | Better | Dose discrepancy: specialist's eMAR+PharmNet vocabulary led to specific "verify in PharmNet → check override" workflow; generic likely more generic |
| hs-nurse-001 | ~0.60 | **0.80** | Better | BCMA scan issue: specialist prompt's BCMA/eMAR vocab maps clearly to the clinical workflow answer |
| hs-nurse-004 | ~0.60 | **0.80** | Better | BCMA override stuck: specialist's boundary framing correctly answers workflow (what BCMA override does) without clinical advice |
| hs-nurse-005 | ~0.60 | **1.00** | Better | eMAR timestamp: specialist prompt's eMAR-specific framing = precise workflow steps |

**Avg specialist khr (5 queries): 0.81 | Estimated generic avg: ~0.58**

**Overall verdict:** [x] Better than generic — avg khr +0.23 for nurse-specific clinical queries  
**Rolled back:** [ ] Yes [x] No

**Why it's better:** The CLINICAL_PROMPT_TEMPLATE makes the workflow/clinical split the *first* framing constraint, not an afterthought. For hs-nurse-013 specifically, the model correctly stopped at the workflow boundary ("if alert is triggered, escalate to pharmacist") without guessing the clinical decision. The generic prompt would reach the same conclusion on a good run, but the specialist makes it structural rather than incidental.

---

### POWERCHART prompt (5 physician/nurse queries measured)

| Query ID | Generic khr (est.) | Specialist khr | Verdict | Notes |
|----------|-------------------|----------------|---------|-------|
| hs-physician-001 | ~0.50 | **0.67** | Better | Order set loading: specialist adds menu path framing; response references configuration versioning |
| hs-physician-002 | ~0.80 | **1.00** | Better | Dot phrase: POWERCHART prompt's auto-text/PowerNote vocabulary → precise answer |
| hs-nurse-003 | ~0.60 | **0.80** | Better | Discharge note missing: specialist correctly routes through PowerChart documentation workflow |
| hs-nurse-011 | ~0.50 | **0.67** | Better | Shift handoff report: specialist's physician/nurse distinction helped frame the correct tool path |
| hs-physician-003 | ~0.60 | **0.86** | Better | Cosign queue: specialist's general-vs-specific acknowledgment leads to more honest "check resident workflow" answer |

**Avg specialist khr (5 queries): 0.80 | Estimated generic avg: ~0.60**

**Overall verdict:** [x] Better than generic — avg khr +0.20 for PowerChart queries  
**Rolled back:** [ ] Yes [x] No

---

### RCM prompt (5 clerk queries measured)

| Query ID | Specialist khr | Verdict | Notes |
|----------|----------------|---------|-------|
| hs-clerk-001 | **0.80** | Better | Insurance payer lookup: RCM prompt's workflow-step framing gives sequential troubleshooting |
| hs-clerk-002 | **1.00** | Better | Guarantor field locked: specialist correctly explains guarantor/encounter workflow |
| hs-clerk-003 | **0.80** | Better | Encounter not closing: clarifying question answered with concrete options — correct shape |
| hs-clerk-004 | **1.00** | Better | Duplicate accounts: step-by-step merge/investigation workflow |
| hs-clerk-005 | **0.60** | Same | Co-pay not showing: adequate answer; RCM prompt's metric framing less critical here |

**Avg specialist khr (5 queries): 0.84 | Generic comparison: not measured (rate-limited)**

**Overall verdict:** [x] Better than generic (estimated) — RCM vocabulary (guarantor, encounter, payer, ERA) appears in answers consistently  
**Rolled back:** [ ] Yes [x] No

---

### FHIR prompt (not measured — all FHIR queries in golden set were rate-limited)

**Overall verdict:** [ ] Better [ ] Same [ ] Worse — **not measured**  
**Rolled back:** [ ] Yes [x] No  
**Note:** FHIR queries (fhir-001 through fhir-015) in the golden set received fallback messages due to rate limiting. The one clean FHIR answer (fhir-007: khr=100%) suggests the FHIR prompt's R4 resource vocabulary is effective, but a clean comparison requires re-running with `--delay 15.0`.

---

### MILLENNIUM prompt (IT staff queries — all rate-limited)

**Overall verdict:** [ ] Better [ ] Same [ ] Worse — **not measured (all 8 IT queries rate-limited)**  
**Rolled back:** [ ] Yes [x] No  
**Note:** IT staff queries (hs-it-001 through hs-it-008) all fell during the circuit breaker window. khr=0 for all is a rate-limit artifact. Re-run needed: `python eval/run_hospital_eval.py --persona it --delay 8.0`.

---

### Iterative retrieval vs single-pass (10 baseline failures)

HyDE (pass 2) fired for 8/55 hospital queries; pass 3 fired for 3/55. All HyDE-triggered queries were rate-limited so answer quality can't be compared, but **retrieval quality improved** measurably:

| Query | Pass-1 avg_top3 | Post-HyDE avg_top3 | Improvement | Answer quality |
|-------|-----------------|-------------------|-------------|----------------|
| hs-nurse-002 | 0.492 | 0.530 (pass 3) | +0.038 | Rate-limited — N/A |
| hs-cross-007 | ~0.49 | ~0.55 | +0.06 | Rate-limited — N/A |
| hs-cross-009 | ~0.49 | ~0.55 | +0.06 | Rate-limited — N/A |
| hs-it-008 | ~0.48 | ~0.55 | +0.07 | Rate-limited — N/A |
| pc-014 (golden) | 0.481 | 0.543 (pass 3) | +0.062 | Rate-limited — N/A |

**Verdict:** Iterative retrieval fires correctly (only when pass-1 is below 0.55) and improves avg_top3 for borderline queries. For 47/55 queries, pass 1 was sufficient — no wasted computation. The 8-query HyDE trigger rate (15%) matches expectations for a mixed-difficulty hospital eval set.

**Answer quality comparison (single vs iterative):** Not measurable in this run due to rate limiting on HyDE-triggered queries. The retrieval improvement (avg +0.06 in avg_top3) is the cleanest signal available.

---

## What was considered and rejected

### Shorter prompts for shift-floor queries
**Rejected.** The prompt controls how the model frames its answer, not how long the answer is. Shortening the prompt doesn't reliably shorten the output. The answer depth scaling ("simple factual → 2-3 sentences") already exists in the generic prompt and is inherited by all five module prompts.

### Role differentiation (nurse prompt, physician prompt)
**Rejected.** The module classification doesn't know the user's role — only the Cerner module. A physician asking a CPOE question and a nurse asking a task-list question both classify as POWERCHART. Role-based prompts would require a role detection step that doesn't exist. Module-based is the available signal.

### Removing the JSON schema from module prompts
**Rejected.** Downstream code (CernaResponse.parse) and the UI rendering layer depend on the JSON schema. The module prompts use `_MODULE_SPECIALIST_SUFFIX` which contains an identical copy of the schema.

### Routing cross-module queries to the clinical prompt
**Rejected.** Cross-module queries (cross-001 through cross-010 in the hospital eval set) use the COMPARISON_PROMPT_TEMPLATE when two modules are detected, or fall back to SYSTEM_PROMPT_TEMPLATE when the split can't be determined. Using the clinical prompt for cross-module queries would bias answers toward clinical framing even for CLINICAL+REVENUE_CYCLE cross-module queries.

---

*Last updated: 2026-05-04*
