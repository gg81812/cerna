# Golden Set Evaluation Baseline — 2026-04-20
**Phase:** 2 · Week 5  
**Collection:** `cerner_docs_bge` (BGE-large-en-v1.5, 1,322 chunks)  
**Eval script:** `eval/run_eval.py` per-module with `--delay 6–12`  
**Pass criterion:** keyword_hit_rate ≥ 0.70 (in-scope) · refusal_correct = True (OOS)

---

## Overall Result

| Scope | Queries | Pass | Pass Rate | Avg KHR |
|-------|---------|------|-----------|---------|
| FHIR | 15 | 13 | **86.7%** | 88.5% |
| Revenue Cycle | 15 | 13 | **86.7%** | 83.8% |
| PowerChart | 15 | 12 | **80.0%** | 81.5% |
| Millennium | 15 | 10 | **66.7%** | 74.4% |
| Clinical | 15 | 7 | **46.7%** | 45.7% |
| **In-scope total** | **75** | **55** | **73.3%** | **74.8%** |
| Out-of-scope | 10 | 9 | **90.0%** | n/a |
| **All modules** | **85** | **64** | **75.3%** | — |

### TPD-Adjusted Rate

7 queries returned a Groq "daily quota exhausted" error (KHR = 0.0) rather than a real answer failure. Excluding these infrastructure failures:

| Scope | Valid queries | Pass | Adjusted rate |
|-------|--------------|------|---------------|
| In-scope | 68 | 55 | **80.9%** |
| All modules | 78 | 64 | **82.1%** |

**Infrastructure note:** The clinical module was run last in the day's budget cycle (100k TPD). Six clinical queries hit the quota wall mid-run. These are scheduling/infrastructure failures, not retrieval or answer-quality regressions. The clinical module's real capability is estimated at ~67–73% based on the 8 queries that did receive answers (avg KHR 74.7% on answered queries).

---

## 10 Worst Failures

Ranked by KHR (lowest first). TPD failures listed with retrieval score to show the chunk was actually found — the LLM simply had no budget to generate.

| # | ID | KHR | Question | Top Chunk | Root Cause |
|---|-----|-----|----------|-----------|------------|
| 1 | clin-001 | 0.0% | What is eMAR in Cerner? | 0.695 | **TPD quota exhaustion** — daily token budget hit; easy query would have passed |
| 2 | clin-006 | 0.0% | How does the eMAR medication administration workflow work? | 0.756 | **TPD quota exhaustion** — highest chunk score in clinical batch |
| 3 | clin-008 | 0.0% | How does scheduling work in Cerner for outpatient appointments? | 0.696 | **TPD quota exhaustion** |
| 4 | clin-009 | 0.0% | How is discharge planning documented in Cerner clinical workflows? | 0.746 | **TPD quota exhaustion** |
| 5 | clin-012 | 0.0% | How does nursing documentation work in PowerChart for clinical assessments? | 0.706 | **TPD quota exhaustion** |
| 6 | mil-010 | 0.0% | How do I upgrade a Cerner Millennium environment? | 0.725 | **TPD quota exhaustion** — Millennium ran before Clinical; budget clipped final query |
| 7 | clin-014 | 14.3% | What are the build steps to configure BCMA overrides and exception workflows? | 0.396 | **Retrieval gap** — chunk score below DYM threshold (0.40); "BCMA overrides" build doc absent from KB; fell to did-you-mean path; only keyword "BCMA" found |
| 8 | clin-004 | 16.7% | What is FirstNet in Cerner? | 0.649 | **TPD partial** — LLM returned quota error; partial KHR from static keyword match in refusal boilerplate |
| 9 | pc-003 | 60.0% | What are patient lists in PowerChart? | 0.732 | **Missing vocabulary** — response described the feature accurately but never used "census" or "filter"; expected keywords ["patient list","PowerChart","census","location","filter"] — 3/5 hit |
| 10 | mil-005 | 60.0% | What is the Millennium domain architecture? | 0.675 | **Missing vocabulary** — response focused on tier names (App/DB/Interface) but omitted "nodes" and "services"; expected ["domain","architecture","Millennium","nodes","services"] — 3/5 hit |

### Detailed Traces for Non-TPD Failures

**clin-014** — Retrieval gap (KHR 14.3%, top_chunk 0.396)  
- *Query:* "What are the build steps to configure BCMA overrides and exception workflows?"  
- *Retrieved:* top_chunk below DYM threshold — system fell to did-you-mean path  
- *Response:* "I'm not sure which Cerner topic you're asking about. Here are some related searches…"  
- *Expected keywords:* BCMA, override, exception, build, configuration, workflow, Cerner  
- *Diagnosis:* No BCMA-override build doc in the KB; the `clin-bcma-override.md` source document may be missing or not chunked.

**pc-003** — Vocabulary mismatch (KHR 60.0%, top_chunk 0.732)  
- *Query:* "What are patient lists in PowerChart?"  
- *Response excerpt:* "patient lists are a way to organize and display patient information in a customized view. They can be used to track patients with specific conditions, medications, or appointments…"  
- *Expected keywords:* patient list, PowerChart, census, location, filter  
- *Missing:* "census" (clinical census list), "filter" (list filter configuration)  
- *Diagnosis:* Response is accurate but generic; KB chunk covers basic concept, not census-list or filter-config depth.

**mil-005** — Vocabulary mismatch (KHR 60.0%, top_chunk 0.675)  
- *Query:* "What is the Millennium domain architecture?"  
- *Response excerpt:* "three primary tiers: Application, Database, and Interface… key server types including PRISMNODE, MCP, MPSERVER, and CVLINK"  
- *Expected keywords:* domain, architecture, Millennium, nodes, services  
- *Missing:* "nodes" (despite PRISMNODE being named), "services" (server services not discussed as "services")  
- *Diagnosis:* Expected keyword "nodes" is present as "PRISMNODE" — keyword match is too literal. Expected keyword "services" is a vocabulary gap in the KB chunk.

---

## SME Review Status

**`eval/golden_set.jsonl` has NOT been SME-reviewed.**

The golden set was machine-authored in Phase 2 Week 4. Expected keywords were written based on Cerner documentation knowledge but have not been validated by a Cerner-certified SME. Known issues:

1. Some expected keywords are overly specific vocabulary that the correct answer might express differently (e.g., "census" for patient lists, "nodes" for architecture).
2. The clinical module keywords may use nursing/clinical terminology that the KB chunks express via synonyms.
3. Difficulty labels (easy/medium/hard) are self-assessed.

**Recommended action before Gate 2:** Have a Cerner SME review the 15 clinical and 15 Millennium expected keyword lists specifically, as these modules have the lowest pass rates and highest risk of false-negative keyword mismatches.

---

## Gate 2 Target

| Scenario | Target | Rationale |
|----------|--------|-----------|
| Raw pass rate (KHR ≥ 0.70) | **82%** | Re-running clinical with fresh TPD budget should recover 4–5 TPD failures; SME keyword review may flip 2–3 borderline fails to passes |
| TPD-adjusted pass rate | **85%** | With clean budget, answer quality on clinical is estimated 67–73%; combined with FHIR/RC/PC strength should reach 85% |
| OOS refusal rate | **95%** | oos-009 (Epic vs MyChart comparison) requires a scoping tweak — low effort fix |

**Gate 2 definition:** ≥ 82% raw pass rate (KHR ≥ 0.70) across all 75 in-scope queries on a fresh-budget run, with ≥ 90% OOS refusal rate.

**Current gap:** 55/75 = 73.3% raw → need 62/75 = 82.7% → need 7 more passes.  
Achievable via: (a) re-run 6 TPD failures with fresh budget (~5 expected passes), (b) clin-014 BCMA override KB gap fix (1 pass), (c) keyword review for pc-003/mil-005 (up to 2 passes).

---

## Per-Module Notes

**FHIR (88.5% avg KHR, 86.7% pass)** — Strongest module. The two failures (fhir-004, fhir-012) both scored 0.667 — they answered correctly but missed one expected keyword. fhir-012 "open source CCL project" is a weak KB area (no `open.cerner.com` content indexed).

**Revenue Cycle (83.8% avg KHR, 86.7% pass)** — Strong performance. Two borderline failures: rc-012 (patient accounting, missed "AR"/"accounts receivable"), rc-015 (CDI/physician query, missed "CDI workflow" depth). Neither is a retrieval failure — both are vocabulary mismatches.

**PowerChart (81.5% avg KHR, 80.0% pass)** — Good. Three failures all under 0.7: pc-003 (census/filter vocab), pc-011 (mobile/tablet keywords missed), pc-012 (FYI alert config depth). No retrieval gaps.

**Millennium (74.4% avg KHR, 66.7% pass)** — Below target. 1 TPD failure, 4 genuine partial-KHR fails. mil-005/mil-006/mil-012/mil-015 all show the KB has Millennium content but response vocabulary doesn't match expected keywords closely enough. mil-007 and mil-014 show JSON parse errors (malformed LLM JSON — confidence degraded to `medium` but KHR still passed).

**Clinical (45.7% avg KHR, 46.7% pass)** — Severely impacted by TPD. 6 zero-KHR failures are all TPD. Of the 9 answered queries, 7 passed (77.8%), matching the target. The 2 real failures are: clin-014 (BCMA override retrieval gap) and clin-015 (PowerChart AI — "AI-powered" context is thin in KB). **Do not treat 46.7% as a valid quality signal — re-run this module with dedicated budget.**

**Out-of-Scope (90% pass)** — One failure: oos-009 "How does Epic's patient portal compare to MyChart?" — the system answered because MyChart is a Cerner product and it detected the Cerner angle. This is a true edge case (partially in-scope). Consider adding a "competitive comparison" OOS class or scoping the refusal to pure competitive-comparison queries.

---

*Eval run: 2026-04-20 · Phase 2 Week 5 · collection: cerner_docs_bge 1322 chunks · models: llama-3.3-70b-versatile (gen), llama3-8b-8192 (classify)*
