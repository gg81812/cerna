# uCern Access Decision — Project Leadership Action Required
**Project:** Cerna · Cerner / Oracle Health AI Specialist  
**Phase:** 2 · Week 5  
**Date:** 2026-04-19  
**Owner required:** See Section 3  
**Decision deadline:** See Section 3

---

## The Issue in One Sentence

The 14 documents that would make Cerna's PowerChart and Clinical modules credible and demo-ready are gated behind uCern portal access — and the project has treated access as a passive waiting item for multiple weeks, when it is the single highest-leverage action available.

---

## 1. What uCern Access Would Unlock

The following 14 documents are in the KB Population Guide as MUST or SHOULD items. They require uCern/Oracle Help Center login to download. None of them have public substitutes at sufficient depth.

| # | Module | File | Priority | Why It Matters |
|---|--------|------|----------|----------------|
| 1 | Millennium | `millennium-oci-hosting-architecture.txt` | SHOULD | OCI hosting and cloud architecture — common client question during Cerner migrations |
| 2 | Millennium | `millennium-performance-tuning.txt` | NICE | Millennium performance guides — specific to uCern implementation contexts |
| 3 | PowerChart | `powerchart-workflow-mpages-admin.txt` | **SHOULD** | MPages administration and workflow configuration — highest query impact among PowerChart questions |
| 4 | PowerChart | `powerchart-physician-advisor-config.txt` | **SHOULD** | Physician advisor configuration guide — second-highest query impact |
| 5 | PowerChart | `powerchart-bpa-guide.txt` | NICE | Best Practice Advisory (BPA) configuration — sepsis, fall risk, infection prevention alerts |
| 6 | PowerChart | `powerchart-dynamic-documentation.txt` | NICE | Dynamic documentation / FlexTables — commonly asked in Cerner build projects |
| 7 | Clinical | `clinical-ed-tracking-board-firstnet.txt` | **SHOULD** | FirstNet ED tracking board configuration — common ED workflow question |
| 8 | Clinical | `clinical-surginet-perioperative.txt` | NICE | SurgiNet perioperative workflow — covers OR/anesthesia build questions |
| 9 | Clinical | `clinical-careguides-pathways.txt` | NICE | CareGuides and clinical pathway configuration — evidence-based order set build |
| 10 | Clinical | `clinical-sepsis-alert-protocol.txt` | NICE | Sepsis BPA alert protocol setup — high-stakes clinical safety question |
| 11 | Clinical | `clinical-maternity-ob-workflow.txt` | NICE | Maternity/OB workflow configuration — labor and delivery build questions |
| 12 | RCM | `rcm-contract-pay-configuration.txt` | **SHOULD** | Contract management and payer configuration — front-end RCM build |
| 13 | RCM | `rcm-operational-reporting.txt` | **SHOULD** | RCM operational reporting setup — performance analytics questions |
| 14 | RCM | `rcm-case-management-utilization.txt` | NICE | Case management and utilization review configuration |

**Impact if all 14 are added:** PowerChart goes from 0 primary sources to 2 SHOULD-tier verifiable documents (items 3–4). Clinical adds 5 Cerner-specific workflow documents (items 7–11). RCM gets 2 operational configuration references (items 12–13). The POV narrative can include PowerChart and Clinical as real demo modules rather than "limited coverage."

---

## 2. Three Scenarios

### Scenario A — Access lands in 2–4 weeks

**What it enables:** Add all 14 documents to the KB. PowerChart and Clinical become fully credible demo modules. Benchmark accuracy improves for clinical workflow and CPOE queries. Phase 2 POV demo can include all five modules.

**Phase 2 / Phase 3 shape:** Phase 2 demo (within 2 weeks) focuses on FHIR + RCM as the strongest modules. Phase 3 opens PowerChart and Clinical depth once documents are ingested. This is the planned trajectory.

**Required actions:** Identify the specific Accenture Oracle Health engagement credentials (or personal Oracle account from a project team member already credentialed). Download the 14 documents, convert PDF exports to .txt, add to `data/[module]/`, run `python ingest.py` and `python scripts/ingest_bge.py`.

**Time to execute once access is confirmed:** ~4 hours (download + ingest + benchmark run).

---

### Scenario B — Access is uncertain or delayed indefinitely

**What this means for the project:** uCern access is contingent on Oracle Health engagement credentials, which require active client project involvement. If no team member has current Oracle Health project access, obtaining credentials could take 4–12 weeks through Oracle's partner program.

**Adjustment required:** Cerna's positioning permanently narrows to **FHIR Integration + Revenue Cycle Specialist** for Phase 2 demo and client POV. PowerChart and Clinical come off the active demo scope. The KB inventory and cerna_status_and_pov.md should be updated to reflect this.

**The POV for this scenario is still strong:** FHIR R4 + SMART on FHIR is the primary regulatory driver for every Oracle Health client under the 21st Century Cures Act. Revenue Cycle (CDRC model) is Cerner's most distinctive competitive differentiator. These two modules together cover the two questions clients are actually asking: "How do we comply with interoperability mandates?" and "How do we extract more value from our RCM investment?"

**This is not a failure scenario.** A focused, credible FHIR + RCM specialist is more valuable in a client conversation than a broad but unverifiable five-module assistant.

---

### Scenario C — Access is definitively denied

**What this means:** No team member can obtain Oracle Health credentials, and the project is not on an active Oracle Health engagement that would provide portal access.

**Required pivot:** The project cannot build a credible Cerner clinical or PowerChart KB without uCern access. The options are:

1. **Community-sourced content:** Oracle CustomerConnect forums (community.oracle.com) require an Oracle account but are accessible with a free Oracle developer account. This provides lower-depth Q&A content, not primary documentation.
2. **SME-authored content:** Have a Cerner-experienced team member write verified content based on firsthand implementation experience. This is legitimate but requires a week of writing time.
3. **Paid third-party content:** KLAS Research, Chilmark Research, or similar healthcare IT analysts publish Cerner-specific content that could be licensed. Cost and licensing complexity may be prohibitive.
4. **Scope reduction:** Retire PowerChart and Clinical from the Cerna roadmap entirely. Reposition as a FHIR + RCM + Millennium platform specialist. This is defensible if the FHIR module continues to expand with Oracle docs.

---

## 3. Required Decision

> **By 2026-04-26** (one week from today), the project needs **[project lead / Accenture engagement manager]** to confirm:
>
> 1. Does any team member currently hold active Oracle Health uCern credentials (from a current or recent Oracle Health engagement)?
> 2. If yes, can they access the uCern Help Center and download these 14 documents?
> 3. If no, which of the three scenarios above (B or C) should the team plan against?
>
> This decision gates the Phase 2 POV narrative, the Week 6 deliverables, and the Phase 3 module roadmap. Without a confirmed answer, the project will default to **Scenario B** positioning — FHIR + RCM focus — in all external materials.

**If Scenario A is confirmed:** Provide the credentials to the person running ingest. The technical path is well-documented in `Cerna_Missing_Documents_List.md` and `docs/kb_gap_inventory.md`.

**If Scenario B is confirmed:** Update `docs/cerna_status_and_pov.md` Section 6 (POV) to reflect the FHIR + RCM positioning and retire the PowerChart / Clinical demo scenarios from the Week 6 plan.

**If Scenario C is confirmed:** Escalate to project leadership for a scope discussion before investing further Phase 3 KB work.

---

## 4. Context: Why This Has Been Passive Until Now

The KB Population Guide (Section 5.2 and equivalent sections) listed uCern content as "GATED — requires portal access" without assigning an owner or a date. The Missing Documents List tracked these as `🔒 GATED` items with no resolution path.

The gap has been visible in every audit document since Week 3. It was not escalated because it looked like a technical dependency (get access → download docs) rather than a business decision. It is a business decision: which engagement model and team configuration gives this project access to Oracle Health's proprietary documentation ecosystem.

This document exists to make that decision explicit, time-bounded, and owned.

---

*Prepared: 2026-04-19 · Cerna Phase 2 Week 5 POV*  
*Decision required by: 2026-04-26 · Owner: [project lead]*
