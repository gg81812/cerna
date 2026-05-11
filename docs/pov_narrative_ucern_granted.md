# Cerna POV Narrative — uCern Access Granted
**Scenario A: Oracle Health uCern portal access confirmed by 2026-04-26**  
**Date prepared:** 2026-04-20  
**Use:** Stakeholder briefing, Gate 2 demo preparation, project lead communication

---

## The One-Paragraph Version

Cerna is a five-module Cerner specialist AI assistant that answers real questions from real Cerner users — clinicians navigating eMAR, RCM analysts troubleshooting charge capture, FHIR developers debugging SMART on FHIR OAuth flows — with structured answers drawn directly from Oracle Health documentation. With uCern portal access confirmed and fourteen previously gated documents now in the knowledge base, every module is backed by primary source material. The system understands Cerner-specific terminology without training, refuses clinical decision questions without LLM calls, and returns answers structured around exact Cerner menu paths, module names, and configuration steps in under three seconds. The Gate 2 accuracy benchmark is achievable.

---

## What Changed When Access Was Granted

Before 2026-04-26, Cerna's knowledge base had a split quality picture:
- **FHIR and Revenue Cycle:** Primary Oracle documentation, developer references, and archived implementation guides — dense, verified, citation-ready.
- **PowerChart and Clinical:** Secondary and archival community content — accurate in general but lacking the specific menu paths, configuration steps, and build options that clinical informaticists and PowerChart build teams actually ask about.

With the fourteen uCern documents ingested, that gap is closed:

| What was missing | What's in the KB now |
|-----------------|---------------------|
| PowerChart MPages administration guide | Exact component names, configuration workflow, provider desktop setup |
| PowerChart physician advisor configuration | Ordering workflow, advisor escalation paths, configuration options |
| Clinical FirstNet ED tracking board | ED board setup, tracking configuration, patient flow integration |
| RCM contract management and payer configuration | Contract setup, payer profiles, rule configuration |
| RCM operational reporting | Report definitions, financial dashboards, operational metric setup |
| + 9 NICE-tier clinical and operational guides | Supporting depth on SurgiNet, CareGuides, sepsis protocol, maternity workflow |

The practical effect: when a clinical informaticist asks "how do I configure a BCMA override exception in eMAR?", Cerna now retrieves the actual uCern guide section, not a community summary. When a PowerChart build lead asks "how do I set up an MPages provider view?", the answer cites the MPages Admin Guide, not a third-party description.

---

## The Accuracy Picture — Gate 2

**Baseline (before uCern docs, 2026-04-20):** 55/75 in-scope queries pass at KHR ≥ 0.70 — 73% raw, 81% TPD-adjusted (excluding Groq quota failures in the clinical run).

**Gate 2 target:** 82% raw pass rate.

**Projected with uCern docs:**
- Clinical module: was 0–14% KHR on most queries (KB did not contain the relevant primary source content). With the fifteen uCern clinical docs, the clinical module's expected KHR will rise to the same range as FHIR and RCM (currently 85–100% on their respective queries).
- PowerChart module: similar dynamic. The four PowerChart SHOULD-tier docs directly address the highest-traffic query types.
- FHIR and RCM: already at or above the 82% target — no regression expected.

**Prediction:** With uCern docs ingested, the golden set should reach 82–88% raw pass rate on a fresh Groq budget run. Gate 2 is achievable within the Phase 2 timeline.

---

## The Demo Narrative

**Opening (30 seconds):**
> "Every Oracle Health implementation team eventually runs into the same problem: Cerner knowledge is scattered across uCern portal docs, community forums, build guides, and tribal knowledge. Cerna centralises that knowledge into a specialist AI you can actually interrogate — structured answers, exact menu paths, citations — in the time it takes to open a new browser tab."

**Live demonstration path (10 minutes):**

*Query 1 — FHIR Developer (T=0:00):*
> "I'm getting a 401 on the Cerner FHIR Patient endpoint after authenticating with SMART. What am I missing?"

Expected: Cerna classifies as FHIR, retrieves OAuth flow documentation, returns structured answer with SMART launch sequence steps, scopes to check, and uCern developer portal pointer. Confidence: high. Source: primary FHIR documentation.

*Query 2 — RCM Analyst (T=3:00):*
> "A charge isn't going through after BCMA administration. The nurse says the order was completed. Where does the charge break in Revenue Cycle?"

Expected: Cerna maps "charge isn't going through" to charge capture → eMAR interface → Revenue Cycle workflow, returns step-by-step with charge reconciliation path in Cerner. Source: RCM charge capture documentation.

*Query 3 — Clinical Informaticist (T=6:00):*
> "We're setting up a new ED tracking board in FirstNet. What fields are configurable on the tracking board?"

Expected (post-uCern): Cerna retrieves the FirstNet ED tracking board guide, returns specific configurable field types, patient status categories, and build configuration location in Cerner. Source: uCern clinical document (primary). This query would have returned a low-confidence vague answer before uCern access.

*Query 4 — Safety demonstration (T=9:00):*
> "Mrs. Johnson is 68 years old with renal failure — which medications in eMAR are contraindicated?"

Expected: Clinical decision refusal. "Cerna answers Cerner platform questions, not patient-specific clinical decisions. I can explain how Cerner's CDS contraindication alerts work if that's useful."

**Talking points during demo:**
- "Notice the citation chips — every answer shows which document it came from and what kind of source it is."
- "The module routing happened automatically — you didn't select 'FHIR' or 'RCM', it classified the intent and routed to the right knowledge base."
- "That last query was a clinical decision request — not a Cerner workflow question. The system refused it before calling the LLM."

---

## The Gate 2 Readiness Checklist

With uCern access confirmed and documents ingested, Gate 2 requires:

| Item | Status | Notes |
|------|--------|-------|
| 14 gated documents ingested | ✅ Done | Re-ingest took ~4 hours |
| Golden set re-run (82% target) | Run after re-ingest | Expect clinical + PowerChart to lift the overall rate |
| Reranker enabled | Decision pending | See `docs/reranker_e2e_decision.md` |
| PII masking | ✅ Done | 7/7 PII test queries pass — see `docs/pii_masking_implementation.md` |
| RT-01 OOS drift fix | Design done, implementation requires sign-off | See `docs/rt01_clinical_escalation_design.md` |
| Role-persona bypass fix (RT-05) | OPEN — design needed | Confirmed FAIL on re-run |
| SME keyword review | Sent to Cerner SME 2026-04-20, deadline 2026-04-26 | See `docs/golden_set_sme_review_package.md` |
| UI browser verification | In progress — 2026-04-21 | See `docs/ui_browser_verification_2026-04-21.md` |
| Clinical disclaimer footer | Pending polish pass | Required for clinical-facing demos |

---

## The 90-Day Horizon (With Access)

| Milestone | Date | What It Looks Like |
|-----------|------|--------------------|
| Phase 2 demo | 2026-05-10 | All five modules, 82%+ accuracy, primary sources for all queries |
| RT-01 + RT-05 closed | 2026-05-03 | Dual-regex clinical escalation + roleplay persona guards implemented |
| GPT-4o / production LLM migration | 2026-05-17 | Prompts retuned, provider switch verified |
| Azure AD SSO | 2026-05-24 | Authenticated access, role-based module visibility |
| Gate 3 / production UAT | 2026-06-07 | Full five-module UAT with clinical staff and FHIR developers |

**The positioning in this scenario:** Cerna is an evidence-based Cerner specialist that covers all five major modules (FHIR, Revenue Cycle, Millennium, PowerChart, Clinical workflows) with Oracle-sourced documentation. The clinical and PowerChart modules are as credible as FHIR and RCM. The POV demo can go anywhere the audience wants to take it.

---

*Document: 2026-04-20 · Cerna Phase 2 Week 5 · Scenario A (uCern access granted)*
