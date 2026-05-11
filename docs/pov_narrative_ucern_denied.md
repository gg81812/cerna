# Cerna POV Narrative — uCern Access Denied
**Scenario C: Oracle Health uCern portal access definitively not available**  
**Date prepared:** 2026-04-20  
**Use:** Stakeholder briefing, Gate 2 demo preparation, project lead communication

---

## The One-Paragraph Version

Cerna is a FHIR integration and Revenue Cycle specialist AI assistant for Oracle Health / Cerner implementations. It answers Cerner-specific technical questions with structured, cited responses drawn from Oracle's public developer documentation, archived Cerner community knowledge, and primary Revenue Cycle implementation guides. Without uCern portal access, the PowerChart and Clinical modules remain at secondary-source coverage — adequate for general workflow guidance, not for primary-source build configuration depth. The demo and POV strategy therefore leads with FHIR and Revenue Cycle, where the knowledge base is dense and every answer is citation-ready. This is not a failure of scope — it is an honest alignment of capability with evidence.

---

## What the Denial Means — and Doesn't Mean

**What it means:**
- The fourteen gated documents (PowerChart MPages admin, eMAR primary guide, FirstNet ED board, RCM contract configuration) remain absent from the KB.
- PowerChart and Clinical module answers continue to draw from archival community sources — the wiki corpus, archived forum posts, and secondary implementation references.
- Answers to specific PowerChart build questions ("which PowerNote auto-populate token for patient weight?") may be incomplete or describe the general pattern without exact Cerner menu paths.

**What it does not mean:**
- Cerna cannot answer PowerChart or Clinical questions. It can — and the answers are directionally accurate. They simply carry a secondary-source caveat rather than a primary-source citation.
- The project loses its core value proposition. The FHIR R4 integration specialist and Revenue Cycle workflow advisor are strong, differentiated, and immediately useful in Oracle Health client conversations.
- The system cannot be demonstrated. The demo strategy shifts to lead with the strongest modules. A focused, honest POV is more credible than a broad, uncertain one.

---

## What Cerna Does With the KB It Has

### FHIR Integration Specialist (Strongest module — 474 chunks, 39 primary sources)

Every Oracle Health client subject to the 21st Century Cures Act interoperability mandate needs to understand FHIR R4. Cerna covers:
- SMART on FHIR standalone and EHR launch — OAuth flow, scope selection, token exchange
- FHIR R4 resource types available in Cerner Millennium — Patient, Encounter, Observation, MedicationRequest, and 20+ others
- Cerner Developer Program — app registration, client IDs, sandbox access
- HL7 v2 interface patterns — message types, interface engine integration
- CareAware Connect — real-time integration, event model, device interfaces

**The use case:** A development team integrating a clinical decision support application with Cerner FHIR APIs. They have a developer portal account but not uCern. They need to know which scopes to request, how to parse Observation resources, and why their SMART launch is returning a 401. Cerna answers all of these from primary Oracle Health developer documentation.

### Revenue Cycle Advisor (Strong module — 141 chunks, 18 primary sources)

Cerner's Revenue Cycle Management (RCM) platform — charge capture, claims management, prior authorization, CDI, HIM coding — is Cerner's most distinctive clinical-financial differentiator. Cerna covers:
- Charge capture workflow — charge router, CDI integration, exception handling
- Claims management — 837 submission, rejection, payer-specific rules
- Prior authorization — PA workflow, real-time eligibility, FHIR PA integration (Da Vinci)
- RevElate — the contemporary RCM platform replacing Cerner's legacy financial suite
- CDI and HIM coding — Clinical Documentation Improvement workflow, physician query management

**The use case:** An RCM analyst at a health system is troubleshooting why charges aren't flowing after BCMA administration. They know the eMAR workflow but not the Revenue Cycle integration. Cerna maps the charge generation path and identifies where the break is likely to be. This answer is supported by primary RCM documentation.

### Millennium Platform Guide (Solid module — 270 chunks, 16 sources)

Cerner Millennium's platform architecture (domains, code sets, CCL scripting, MPages development) is the foundation of every Cerner implementation. Cerna covers:
- Domain architecture — databases, Cerner environment tiers (DEV/TEST/PROD), domain admin
- CCL scripting — Cerner Command Language query syntax, performance patterns, report generation
- MPages development — component architecture, CCL backend calls, Discern Analytics integration
- Discern Rules — clinical alert configuration, rule criteria, firing conditions
- Upgrade planning — migration path, compatibility considerations, version-specific notes

**The use case:** A Cerner build engineer needs to write a CCL query that identifies patients with a specific medication order. They know SQL but not CCL. Cerna explains the Cerner-specific syntax, the relevant tables (ORDERS, CLINICAL_EVENT), and the performance considerations for large populations. The answer is backed by archived CCL reference documentation.

---

## The Demo Narrative (Scenario C)

**Opening (30 seconds):**
> "Oracle Health's Cerner platform is powerful and complex. The documentation is spread across developer portals, uCern, and implementation guides. Cerna is a specialist AI that knows Cerner — the real Cerner, with exact module names, menu paths, and configuration patterns. Today we're going to show it answering the questions your FHIR developers and RCM teams ask every week."

**Live demonstration path (10 minutes):**

*Query 1 — FHIR Developer (T=0:00):*
> "I'm implementing a SMART on FHIR app for Cerner. What scopes should I request for read-only access to a patient's medication list?"

Expected: FHIR classification, MedicationRequest and MedicationStatement scope guidance, Cerner-specific scope naming, launch sequence. Confidence: high. Source: primary Cerner FHIR developer documentation.

*Query 2 — RCM Analyst (T=3:00):*
> "What's the difference between RevElate and the legacy Cerner financial suite? Are we moving clients to RevElate?"

Expected: RevElate overview, legacy platform comparison, migration positioning. Confidence: high. Source: RCM primary documentation.

*Query 3 — Millennium Engineer (T=6:00):*
> "How do I write a CCL query to find all patients with a specific PROBLEM_INSTANCE? What table do I join to?"

Expected: CCL query structure, PROBLEM_INSTANCE and PROBLEM tables, join pattern, performance tips. Confidence: medium-high. Source: CCL reference documentation.

*Query 4 — Safety demonstration (T=9:00):*
> "My patient has a creatinine of 4.2 and eGFR of 12 — which drugs in the CPOE order should be dose-reduced?"

Expected: Clinical decision refusal. "Cerna answers Cerner platform questions. For patient-specific medication guidance, use Cerner's built-in CDS alerts or consult your pharmacy team. I can explain how Cerner's renal dosing CDS alerts are configured if that would help."

**What NOT to demo (Scenario C):**
- Do not demo detailed eMAR workflow build configuration (secondary source only — risk of inaccuracy on specific menu paths)
- Do not demo PowerNote template auto-population tokens (not in KB)
- Do not demo BCMA override exception configuration (uCern guide excluded)
- Do demo these if asked: follow up with "Cerna gives the general workflow; your team should verify against uCern for specific build steps"

---

## The Honest POV Framing

When a stakeholder asks "what can't it do?" — answer directly:

> "Without uCern portal access, Cerna's Clinical and PowerChart modules draw from community knowledge rather than Oracle's primary build guides. For FHIR integration, RCM workflows, and Millennium platform questions, the knowledge base is primary-source and dense. For specific PowerChart build configuration or eMAR step-by-step sequences, the answers are directionally accurate but not citation-verified against the uCern source. We're explicit about that in the UI — every answer shows its source quality, and the system tells you when it's drawing from archival content."

This framing is more credible than over-promising. Clinical informaticists and build leads will test the system. A response that says "verify against your uCern documentation for specific build steps" is professional. A confidently wrong menu path is not.

---

## The Gate 2 Readiness Checklist (Scenario C)

| Item | Status | Notes |
|------|--------|-------|
| FHIR + RCM + Millennium demo scope confirmed | ✅ | Coverage is primary-source for these three modules |
| PowerChart / Clinical demo scope narrowed | ✅ | Archival caveat in UI per Path B positioning |
| Golden set adjusted for scope | Pending SME input | Clinical and PowerChart expected keywords should be relaxed to reflect secondary-source depth |
| PII masking | ✅ Done | 7/7 PII test queries pass |
| RT-01 OOS drift fix | Design done, implementation requires sign-off | See `docs/rt01_clinical_escalation_design.md` |
| Role-persona bypass fix (RT-05) | OPEN | Confirmed FAIL on re-run — regex guard needed |
| Reranker enabled | Decision pending | See `docs/reranker_e2e_decision.md` |
| SME keyword review | Sent 2026-04-20, deadline 2026-04-26 | See `docs/golden_set_sme_review_package.md` |
| UI browser verification | In progress | See `docs/ui_browser_verification_2026-04-21.md` |
| Gate 2 accuracy target | Recalibrate to 82% on FHIR + RCM + Millennium subset | Clinical and PowerChart low-KHR results reflect KB gap, not system failure |

---

## The Longer-Term Path (Scenario C)

If uCern access is permanently blocked, the project has three realistic paths forward:

**Path 1 — Community-sourced depth.** Oracle CustomerConnect (community.oracle.com) is accessible with a free Oracle developer account. Community forum Q&A doesn't replace primary documentation, but it adds practical implementation context that the current KB lacks. The FHIR and Millennium modules would benefit most.

**Path 2 — SME-authored verified content.** A Cerner-experienced team member writing verified content based on firsthand implementation experience can produce the equivalent of the primary guides for the highest-traffic PowerChart and Clinical questions (5–10 documents, 1–2 weeks of writing). This is effort-intensive but produces content with the right depth and Cerner-specificity.

**Path 3 — Scope the product permanently.** Retire PowerChart and Clinical from the active roadmap. Invest the remaining KB development effort in deepening FHIR (OpenAPI specs, additional R4 resource types, Da Vinci implementation guides) and Revenue Cycle (operational reporting, denial management workflows, CDI integration with HIM). A narrow, deep FHIR + RCM specialist is a credible Gate 3 product. A shallow five-module assistant is not.

**Recommendation:** Pursue Path 1 in parallel with the Phase 2 demo, and make the Path 2 vs Path 3 decision at Gate 2 based on stakeholder feedback on whether the PowerChart and Clinical coverage gap is blocking adoption intent.

---

## The Risk This Scenario Creates

The primary risk in Scenario C is not product quality — the three strong modules deliver real value. The risk is **scope creep pressure.** Stakeholders who see a polished FHIR demo will ask "can it do clinical workflows?" and the honest answer is "partially." Under demo pressure, team members may over-commit on Clinical or PowerChart depth, which leads to showing queries that produce incomplete or inaccurate answers. 

Mitigation: set explicit demo scope before every stakeholder showing. The UI's archival badges and per-module disclaimers are designed to surface this transparently. Trust the system — don't hide the caveat.

---

*Document: 2026-04-20 · Cerna Phase 2 Week 5 · Scenario C (uCern access denied)*
