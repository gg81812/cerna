# Cerna KB Gap Inventory
**Project:** Cerna · Cerner / Oracle Health AI Specialist  
**Phase:** 2 · Week 5  
**Date:** 2026-04-19  
**Scope:** Every file in `data/` classified into 5 buckets against the KB Population Guide Sections 1–5

---

## Bucket Definitions

| # | Label | Description |
|---|-------|-------------|
| **B1** | Present — primary source | Official document from the cited URL; scrape path is verifiable today (Oracle docs, HL7 specs, GitHub repo, CDC/ANA) |
| **B2** | Present — secondary source | Third-party explainer, consultant blog, vendor marketing page, professional association summary — legitimate but not the authoritative original |
| **B3** | Present — AI-synthesized or unverifiable | Explicitly marked `SYNTHETIC KNOWLEDGE BASE`, or sourced from `wiki.cerner.com` paths that are no longer publicly accessible and cannot be independently verified |
| **B4** | Absent — publicly available | Listed in the KB guide's BLOCKED or NOT FOUND rows; document exists at a public URL but was not collected |
| **B5** | Absent — gated | Requires uCern portal, Oracle Help Center login, or Accenture internal access |

> **On wiki.cerner.com files:** The old Cerner Confluence wiki (`wiki.cerner.com/display/public/…`) was publicly accessible until Oracle Health migrated content to the Oracle Help Center. Files with `# RETRIEVED: 2026-04-01` and wiki.cerner.com URLs cannot be re-fetched today to verify authenticity. For demo purposes, treat as **unverifiable** — the content may be genuine historical scrapes, but they cannot be cited or confirmed by an SME against a live URL.

---

## Executive Summary

| Stat | Value |
|------|-------|
| Total files in `data/` (excluding READMEs) | **109** |
| Bucket 1 — verified primary | **37 (34%)** |
| Bucket 2 — legitimate secondary | **27 (25%)** |
| Bucket 3 — unverifiable / synthetic | **45 (41%)** |
| Bucket 4 — absent, publicly collectible | **21** |
| Bucket 5 — absent, gated | **14** |

**The critical finding:** 41% of the KB is unverifiable. It is concentrated in PowerChart (87% B3), Clinical (67% B3), and Millennium (53% B3). FHIR is the only module with a credible, verifiable foundation.

---

## Module 1 — FHIR & APIs

### File Classification (39 content files)

| File | Bucket | Source | Notes |
|------|--------|--------|-------|
| fhir-allergy-intolerance.md | **B1** | github.com/cerner/fhir.cerner.com | GitHub repo, real endpoint examples |
| fhir-appointment.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-binary-resource.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-care-plan.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-condition-resource.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-coverage-resource.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-diagnostic-report.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-document-reference.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-encounter-resource.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-goal-resource.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-immunization-resource.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-location-resource.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-medication-administration.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-medication-request.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-observation-resource.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-organization-resource.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-patient-resource.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-practitioner-resource.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-procedure-resource.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-r4-overview.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-related-person.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-slot-resource.md | **B1** | github.com/cerner/fhir.cerner.com | |
| fhir-smart-app-build-guide.txt | **B1** | docs.oracle.com (SMART build guide) | |
| fhir-faqs-common-issues.txt | **B1** | docs.oracle.com (FHIR FAQs) | |
| fhir-oracle-api-r4-overview.txt | **B1** | docs.oracle.com (R4 API overview) | |
| fhir-smart-app-overview.txt | **B1** | docs.oracle.com, Doc ID G37938-01 | Has document ID — verifiable |
| fhir-smart-app-provisioning.txt | **B1** | docs.oracle.com (SMART provisioning) | |
| fhir-smart-on-fhir-spec.txt | **B1** | docs.smarthealthit.org | HL7 SMART spec |
| fhir-us-core-implementation-guide.txt | **B1** | hl7.org/fhir/us/core | HL7 official |
| fhir-hl7-appointment.txt | **B1** | hl7.org/fhir/R4/appointment.html | HL7 spec page |
| fhir-hl7-medication-request.txt | **B1** | hl7.org/fhir/R4/medicationrequest.html | |
| fhir-hl7-observation.txt | **B1** | hl7.org/fhir/R4/observation.html | |
| fhir-hl7-patient.txt | **B1** | hl7.org/fhir/R4/patient.html | |
| fhir-engineering-blog-posts.txt | **B2** | engineering.cerner.com/ | Official but blog content |
| fhir-hl7-fhir-integration.txt | **B2** | 6b.health/insight/ | Consultant blog despite "HL7" in name |
| fhir-oracle-developer-program.txt | **B2** | 6b.health/insight/ | |
| fhir-cerner-integration-deep-dive.txt | **B2** | tactionsoft.com/blog/ | Third-party blog |
| fhir-smart-tutorial.txt | **B2** | kyledcrews.medium.com / engineering.cerner.com | Personal blog + Cerner eng blog |
| fhir-developer-program-guide.txt | **B3** | wiki.cerner.com (SYNTHETIC marker) | Explicitly AI-generated |

**FHIR subtotals — B1: 33 · B2: 5 · B3: 1**

### Absent Sources

| Item | Bucket | Priority | Est. Collection Time | Notes |
|------|--------|----------|---------------------|-------|
| fhir-hl7-r4-specification.txt | **B4** | MUST | 30 min | hl7.org/fhir/R4/ — SSL cert error; browser download |
| fhir-cerner-fhir-portal.txt | **B4** | MUST | 20 min | fhir.cerner.com — blocked; browser copy |
| fhir-practitioner-role.md | **B4** | SHOULD | 15 min | GitHub archive zip — one download gets all 3 |
| fhir-medication-statement.md | **B4** | SHOULD | 5 min | Same zip as above |
| fhir-communication-resource.md | **B4** | SHOULD | 5 min | Same zip as above |
| fhir-revenue-cycle-rest-api.txt | **B4** | MUST | 30 min | Search docs.oracle.com — Oracle RCM REST API |
| fhir-financial-transaction-api.txt | **B4** | SHOULD | 30 min | Search docs.oracle.com — Financial Transaction FHIR |

### FHIR Demo Readiness: **Demo-ready**

97% of present files are B1 or B2. The single B3 file (fhir-developer-program-guide.txt) should be removed. 7 absent items would improve coverage but are not blockers — the current 39 files fully cover R4 resource definitions, SMART flows, and Oracle-specific implementation guidance.

---

## Module 2 — Millennium

### File Classification (19 content files)

| File | Bucket | Source | Notes |
|------|--------|--------|-------|
| millennium-oracle-health-docs-hub.txt | **B1** | docs.oracle.com/en/industries/health/ | Oracle official docs hub |
| millennium-platform-apis-index.txt | **B1** | docs.oracle.com/millennium-platform-apis/ | Oracle official |
| millennium-oracle-wikipedia.txt | **B2** | en.wikipedia.org/wiki/Oracle_Cerner | Background/overview only |
| millennium-6b-integration-overview.txt | **B2** | 6b.health/services/ | Consultant integration guide |
| millennium-ccl-open-source.txt | **B2** | engineering.cerner.com/post/ | Cerner engineering blog |
| millennium-developer-program.txt | **B2** | 6b.health/insight/ | |
| millennium-implementation-guide.txt | **B2** | ghit.digital/insight/ | Consulting firm guide |
| millennium-integration-pathways.txt | **B2** | tactionsoft.com/blog/ | Third-party blog |
| millennium-mpages-explained.txt | **B2** | ehrenhancify.com/oracle-health-mpages/ | Third-party explainer |
| millennium-ccl-programmer-reference.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| millennium-discern-analytics-admin.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| millennium-domain-administration-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| millennium-mpages-development-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| millennium-release-notes-current.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable; "current" is a stale label |
| millennium-security-user-management.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| millennium-upgrade-planning-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| millennium-code-sets-guide.txt | **B3** | SYNTHETIC | Explicitly AI-generated |
| millennium-ccl-performance-tuning.txt | **B3** | SYNTHETIC | Explicitly AI-generated |
| millennium-discern-rules-engine.txt | **B3** | SYNTHETIC | Explicitly AI-generated |

**Millennium subtotals — B1: 2 · B2: 7 · B3: 10**

> **B3 defensibility note:** The 3 SYNTHETIC files are clearly AI-generated and indefensible. The 7 wiki.cerner.com files are marginally defensible as historical scrapes of the old public wiki, but they cannot be cited against a live URL, and their content may not reflect the current Oracle Health platform state. Treat all 10 as unverifiable in demo contexts.

### Absent Sources

| Item | Bucket | Priority | Est. Collection Time | Notes |
|------|--------|----------|---------------------|-------|
| millennium-oracle-community-forums.txt | **B4** | MUST | 60–90 min | community.oracle.com — 403; needs login + thread selection |
| millennium-oracle-cerner-overview.txt | **B4** | SHOULD | 30 min | Search medium.com for Millennium overview article |
| millennium-oci-hosting-architecture.txt | **B5** | SHOULD | — | OCI hosting docs — uCern portal |
| millennium-performance-tuning.txt | **B5** | NICE | — | Millennium perf tuning — uCern portal |

### Millennium Demo Readiness: **Demo-ready with disclaimer**

47% of present files are B1/B2, covering the platform landscape adequately for executive-level discussion. The B2 set (6b.health, engineering.cerner.com, ghit.digital) provides enough context to answer "what is Millennium" and "how does integration work." **However:** no B1 primary technical reference exists for CCL, MPages development, or Discern Analytics — the specific questions a developer would ask. Do not demo deep Millennium developer questions; refer to Oracle Help Center in follow-ups.

---

## Module 3 — PowerChart

### File Classification (15 content files)

| File | Bucket | Source | Notes |
|------|--------|--------|-------|
| powerchart-implementation-build.txt | **B2** | ghit.digital/insight/ | Consulting guide |
| powerchart-mpages-overview.txt | **B2** | ehrenhancify.com/ | Third-party explainer |
| powerchart-clinical-decision-support.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| powerchart-cpoe-order-entry-workflow.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| powerchart-medication-reconciliation.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| powerchart-patient-list-configuration.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| powerchart-powernote-documentation.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| powerchart-results-review-inbox.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| powerchart-touch-mobile-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| powerchart-user-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| powerchart-ai-integration-context.txt | **B3** | SYNTHETIC | Explicitly AI-generated |
| powerchart-ai-predictive-ordering.txt | **B3** | SYNTHETIC | Explicitly AI-generated |
| powerchart-cpoe-alert-configuration.txt | **B3** | SYNTHETIC | Explicitly AI-generated |
| powerchart-hl7-lab-integration.txt | **B3** | SYNTHETIC | Explicitly AI-generated |
| powerchart-order-sets-cpoe-config.txt | **B3** | SYNTHETIC | Explicitly AI-generated |

**PowerChart subtotals — B1: 0 · B2: 2 · B3: 13**

> **B3 defensibility note:** 5 SYNTHETIC files are indefensible. The 8 wiki.cerner.com files cover core PowerChart workflows (CPOE, patient lists, medication reconciliation, PowerNote, results review) — content that is highly likely to be asked about in any demo. This content reads plausibly correct but cannot be verified. Any Cerner-credentialed audience member could challenge it.

### Absent Sources

| Item | Bucket | Priority | Est. Collection Time | Notes |
|------|--------|----------|---------------------|-------|
| powerchart-oracle-community-forums.txt | **B4** | MUST | 60–90 min | community.oracle.com — 403; needs login |
| powerchart-cerner-ehr-consulting.txt | **B4** | SHOULD | 20 min | capminds.com — TLS error; browser copy |
| powerchart-workflow-mpages-admin.txt | **B5** | SHOULD | — | MPages admin config — uCern portal |
| powerchart-physician-advisor-config.txt | **B5** | SHOULD | — | Physician advisor config — uCern portal |
| powerchart-bpa-guide.txt | **B5** | NICE | — | BPA (Best Practice Advisory) — uCern portal |
| powerchart-dynamic-documentation.txt | **B5** | NICE | — | Dynamic documentation / FlexTables — uCern portal |

### PowerChart Demo Readiness: **Not demo-ready**

13 of 15 files (87%) are unverifiable. The 2 B2 files (ghit.digital, ehrenhancify.com) provide only high-level overviews. If an SME asks "how do I configure patient list filters" or "how does CPOE alert fatigue management work," every answer will come from unverifiable B3 content. Without the gated uCern docs or genuine Oracle Help Center scrapes, the PowerChart module cannot be credibly presented to a healthcare IT audience.

---

## Module 4 — Revenue Cycle

### File Classification (18 content files)

| File | Bucket | Source | Notes |
|------|--------|--------|-------|
| rcm-hfma-revenue-cycle.txt | **B2** | hfma.org/revenue-cycle-management/ | HFMA official (professional org) |
| rcm-cdrc-techtarget-article.txt | **B2** | techtarget.com/searchhealthit/ | Industry publication |
| rcm-cdrc-concept-explained.txt | **B2** | techtarget.com/revcyclemanagement/ | Industry publication |
| rcm-cerner-product-overview.txt | **B2** | cerner.com/en/solutions/rcm | Oracle/Cerner marketing page |
| rcm-cpt-lookup-ama.txt | **B2** | ama-assn.org/practice-management/cpt/ | AMA official (standard codes) |
| rcm-charge-capture-reconciliation.txt | **B2** | cerecore.net/ | Third-party RCM services blog |
| rcm-medcare-workflow-guide.txt | **B2** | medcaremso.com/ehr-billing-service/cerner/ | Third-party Cerner billing blog |
| rcm-overview-module-map.txt | **B2** | oracle.com/health/revenue-cycle-management/ | Oracle marketing (not technical docs) |
| rcm-implementation-build-guide.txt | **B2** | ghit.digital/insight/ | Consulting firm guide |
| rcm-cdi-integration-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| rcm-charge-capture-configuration.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| rcm-charge-review-workflow.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| rcm-claims-management-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| rcm-denial-management-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| rcm-him-coding-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| rcm-patient-access-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| rcm-patient-accounting-user-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| rcm-revelate-product-guide.txt | **B3** | SYNTHETIC | Explicitly AI-generated |

**Revenue Cycle subtotals — B1: 0 · B2: 9 · B3: 9**

> **B3 defensibility note:** rcm-revelate-product-guide.txt is indefensible (explicit SYNTHETIC marker). The 8 wiki.cerner.com files cover core RCM workflows (charge capture, charge review, CDI, HIM coding, claims management, denial management, patient access, patient accounting) — exactly the operational content clients ask about. Same problem as PowerChart: plausible content, unverifiable source.

### Absent Sources

| Item | Bucket | Priority | Est. Collection Time | Notes |
|------|--------|----------|---------------------|-------|
| rcm-oracle-community-forums.txt | **B4** | MUST | 60–90 min | community.oracle.com — 403; needs login |
| rcm-billing-claims-solution.txt | **B4** | MUST | 30 min | Search oracle.com for billing/claims solution |
| rcm-financial-transaction-fhir.txt | **B4** | SHOULD | 30 min | Search docs.oracle.com for Financial Transaction API |
| rcm-ehr-integration-overview.txt | **B4** | SHOULD | 20 min | Any public source for Cerner EHR billing integration |
| rcm-cerner-consulting-rcm.txt | **B4** | SHOULD | 20 min | capminds.com — TLS error; browser copy |
| rcm-icd10-reference-cms.txt | **B4** | SHOULD | 30 min | cms.gov/Medicare/Coding/ICD10 — timeout; manual download |
| rcm-nucc-place-of-service-codes.txt | **B4** | NICE | 20 min | nucc.org — 404; navigate directly to Place of Service codes |
| rcm-contract-pay-configuration.txt | **B5** | SHOULD | — | Contract/payer configuration — uCern portal |
| rcm-operational-reporting.txt | **B5** | SHOULD | — | RCM operational reporting — uCern portal |
| rcm-case-management-utilization.txt | **B5** | NICE | — | Case management/utilization review — uCern portal |

### Revenue Cycle Demo Readiness: **Demo-ready with disclaimer**

50% of files are B2, covering CDRC philosophy, HFMA benchmarks, CPT/ICD coding context, and Oracle product marketing. Enough to discuss RCM at a conceptual level. **However:** all detailed configuration and workflow content (charge capture rules, CDI integration, claims management, denial workflows) is B3/unverifiable. A rev cycle analyst would identify gaps immediately. Tag answers about RCM configuration as "outline the approach" rather than "here is the exact Cerner configuration step."

---

## Module 5 — Clinical Workflows

### File Classification (18 content files)

| File | Bucket | Source | Notes |
|------|--------|--------|-------|
| clinical-cdc-immunization.txt | **B1** | cdc.gov/vaccines/hcp/imz-schedules/ | CDC official immunization schedules |
| clinical-ana-nursing-standards.txt | **B1** | nursingworld.org/practice-policy/ | ANA official position statements |
| clinical-ai-scribe-powerchart.txt | **B2** | notev.ai/blog/ | AI vendor blog about Cerner integration |
| clinical-implementation-build-guide.txt | **B2** | ghit.digital/insight/ | Consulting firm build guide |
| clinical-ismp-main.txt | **B2** | ismp.org (via ECRI redirect) | ISMP medication safety content |
| clinical-joint-commission-safety.txt | **B2** | americandatanetwork.com (JC content) | Third-party reprinting JC 2025 NPSGs |
| clinical-bcma-barcode-admin-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| clinical-discharge-planning-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| clinical-emar-user-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| clinical-firstnet-ed-tracking.txt | **B3** | SYNTHETIC | Explicitly AI-generated |
| clinical-medication-administration-workflow.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| clinical-nursing-assessment-documentation.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| clinical-patient-safety-event-reporting.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| clinical-pharmnet-pharmacy-workflow.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| clinical-powerforms-admin-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| clinical-powerplans-admin-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| clinical-scheduling-configuration-guide.txt | **B3** | wiki.cerner.com/public/… | Old Cerner wiki — unverifiable |
| clinical-surginet-perioperative.txt | **B3** | SYNTHETIC | Explicitly AI-generated |

**Clinical subtotals — B1: 2 · B2: 4 · B3: 12**

> **B3 defensibility note:** clinical-firstnet-ed-tracking.txt and clinical-surginet-perioperative.txt are explicitly SYNTHETIC and indefensible. The 10 wiki.cerner.com files cover the entire Cerner clinical workflow stack: BCMA, eMAR, PharmNet, PowerForms, PowerPlans, discharge planning, nursing assessment, medication administration, patient safety events, and scheduling. This is exactly the content a clinical informaticist would query. All 10 are unverifiable. If a hospital CIO or clinical analyst asks "how does BCMA verification work in Cerner," the answer will come from B3 content that cannot be traced to an authoritative source.

> **The honesty problem:** The B2 sources (CDC, ANA, ISMP, Joint Commission) document clinical standards and patient safety best practices — they do not document how Cerner's software works. If the B3 files are removed, the clinical module retains CDC immunization schedules and ANA nursing position statements. These cannot answer any Cerner-specific clinical workflow question. The module would be effectively empty for its intended purpose.

### Absent Sources

| Item | Bucket | Priority | Est. Collection Time | Notes |
|------|--------|----------|---------------------|-------|
| clinical-oracle-community-forums.txt | **B4** | MUST | 60–90 min | community.oracle.com — 403; needs login |
| clinical-ismp-safety-guidelines.txt | **B4** | SHOULD | 30 min | ismp.org/guidelines — ECRI login; institutional or paid access |
| clinical-cms-medication-safety.txt | **B4** | SHOULD | 30 min | cms.gov/medicare/quality — persistent timeout; manual download |
| clinical-ed-tracking-board-firstnet.txt | **B5** | SHOULD | — | FirstNet ED tracking config — uCern portal |
| clinical-surginet-perioperative.txt | **B5** | NICE | — | SurgiNet perioperative guide — uCern portal |
| clinical-careguides-pathways.txt | **B5** | NICE | — | CareGuides and clinical pathways — uCern portal |
| clinical-sepsis-alert-protocol.txt | **B5** | NICE | — | Sepsis BPA alert protocol — uCern portal |
| clinical-maternity-ob-workflow.txt | **B5** | NICE | — | Maternity/OB workflow — uCern portal |

### Clinical Demo Readiness: **Not demo-ready**

67% of files are B3. Strip the B3 content and the module has 2 CDC/ANA files that cover clinical standards, not Cerner software. There is no verifiable primary source for BCMA, eMAR, PharmNet, PowerForms, or PowerPlans. The gated uCern sources (5 items) are the correct fix but require portal access. Collecting the 3 B4 items adds general clinical safety context but still leaves the Cerner-specific workflow gap unfilled.

---

## Module-Level Summary

| Module | Files | B1 | B2 | B3 | Demo Readiness |
|--------|-------|----|----|----|----|
| FHIR & APIs | 39 | 33 (85%) | 5 (13%) | 1 (2%) | **Demo-ready** |
| Millennium | 19 | 2 (11%) | 7 (37%) | 10 (53%) | **Demo-ready with disclaimer** |
| PowerChart | 15 | 0 (0%) | 2 (13%) | 13 (87%) | **Not demo-ready** |
| Revenue Cycle | 18 | 0 (0%) | 9 (50%) | 9 (50%) | **Demo-ready with disclaimer** |
| Clinical | 18 | 2 (11%) | 4 (22%) | 12 (67%) | **Not demo-ready** |
| **TOTAL** | **109** | **37 (34%)** | **27 (25%)** | **45 (41%)** | — |

---

## Bucket 4 — Complete List (Absent, Publicly Collectible)

All 21 items in the order I would collect them on a scraper day. Items are grouped by collection method to minimize context-switching.

### Group A: Oracle docs.oracle.com — Scraper (2–3 hours total)

| # | Module | File | URL | Priority | Time |
|---|--------|------|-----|----------|------|
| 1 | FHIR | fhir-revenue-cycle-rest-api.txt | Search docs.oracle.com "Revenue Cycle REST API Millennium" | MUST | 30 min |
| 2 | FHIR | fhir-financial-transaction-api.txt | Search docs.oracle.com "Financial Transaction FHIR" | SHOULD | 30 min |
| 3 | RCM | rcm-financial-transaction-fhir.txt | Same Oracle docs search as #2; likely same page | SHOULD | 5 min |
| 4 | RCM | rcm-billing-claims-solution.txt | Search oracle.com "billing claims solution" | MUST | 30 min |

### Group B: GitHub archive — One download, multiple files (35 min)

| # | Module | File | URL | Priority | Time |
|---|--------|------|-----|----------|------|
| 5 | FHIR | fhir-practitioner-role.md | github.com/cerner/fhir.cerner.com — download main.zip | SHOULD | 15 min |
| 6 | FHIR | fhir-medication-statement.md | Same zip | SHOULD | 5 min |
| 7 | FHIR | fhir-communication-resource.md | Same zip | SHOULD | 5 min |

### Group C: Static public sites — Browser copy (2.5 hours)

| # | Module | File | URL | Priority | Time |
|---|--------|------|-----|----------|------|
| 8 | FHIR | fhir-hl7-r4-specification.txt | hl7.org/fhir/R4/ | MUST | 30 min |
| 9 | FHIR | fhir-cerner-fhir-portal.txt | fhir.cerner.com | MUST | 20 min |
| 10 | PowerChart | powerchart-cerner-ehr-consulting.txt | capminds.com/cerner/ (TLS error) | SHOULD | 20 min |
| 11 | RCM | rcm-cerner-consulting-rcm.txt | capminds.com/cerner-ehr/ (TLS error) | SHOULD | 20 min |
| 12 | RCM | rcm-ehr-integration-overview.txt | Any public Cerner EHR billing integration source | SHOULD | 20 min |
| 13 | RCM | rcm-icd10-reference-cms.txt | cms.gov/Medicare/Coding/ICD10 | SHOULD | 30 min |
| 14 | RCM | rcm-nucc-place-of-service-codes.txt | nucc.org | NICE | 20 min |
| 15 | Clinical | clinical-ismp-safety-guidelines.txt | ismp.org/guidelines (ECRI login needed) | SHOULD | 30 min |
| 16 | Clinical | clinical-cms-medication-safety.txt | cms.gov/medicare/quality | SHOULD | 30 min |
| 17 | Millennium | millennium-oracle-cerner-overview.txt | Search medium.com "Oracle Cerner Millennium overview" | SHOULD | 30 min |

### Group D: Oracle Community forums — Requires login (4–6 hours)

| # | Module | File | URL | Priority | Time |
|---|--------|------|-----|----------|------|
| 18 | FHIR-adjacent | (covered by existing FHIR docs) | — | — | — |
| 19 | Millennium | millennium-oracle-community-forums.txt | community.oracle.com/customerconnect | MUST | 90 min |
| 20 | PowerChart | powerchart-oracle-community-forums.txt | community.oracle.com/customerconnect | MUST | 90 min |
| 21 | RCM | rcm-oracle-community-forums.txt | community.oracle.com/customerconnect | MUST | 90 min |
| 22 | Clinical | clinical-oracle-community-forums.txt | community.oracle.com/customerconnect | MUST | 90 min |

> **Forum note:** Oracle CustomerConnect forums require an Oracle account or healthcare organization login. The 4 forum files are listed as MUST in the guide because community-sourced Q&A is the closest public analog to uCern support content. However, these are the most time-intensive items and may not be collectible without prior Oracle account setup. Time estimate: 4–6 hours if the login exists; blocked indefinitely without it.

### Scraper Day Time Estimates

| Group | Files | Estimated Time | Impact |
|-------|-------|----------------|--------|
| A: Oracle docs search | 4 | 95 min | High — fills FHIR/RCM primary source gaps |
| B: GitHub archive | 3 | 25 min | Medium — adds 3 missing R4 resources |
| C: Static sites | 10 | 3.5 hours | Medium — ICD-10, ISMP, CMS, capminds |
| D: Oracle Community forums | 4 | 4–6 hours | High if login available, blocked otherwise |
| **Total (excl. forums)** | **17** | **~5.5 hours** | Covers most B4 items |
| **Total (incl. forums)** | **21** | **~11 hours** | Full B4 collection |

---

## Three-Path Recommendation

### Path A — Scraper Day (Collect B4)

**Do:** Spend 5–6 hours collecting Groups A, B, C above (skip forums unless Oracle login exists). Re-ingest. Remove the 2 explicit SYNTHETIC files from FHIR (fhir-developer-program-guide.txt) and the 3 SYNTHETIC files from Millennium.

**Impact:** FHIR becomes near-perfect (36–38 B1/B2 files, zero SYNTHETIC). Millennium, RCM get 4–5 additional verifiable files. PowerChart and Clinical remain weak.

**Does not fix:** The B3/wiki.cerner.com problem in PowerChart, Clinical, and Millennium. A scraper day adds public content but cannot replace the 35 unverifiable wiki files.

**When to choose:** Choose this if you need FHIR coverage to be bulletproof and are presenting to a technical FHIR/API audience. The 5-hour investment is worth it for FHIR alone.

---

### Path B — Narrow the POV (FHIR + Revenue Cycle Demo Focus)

**Do:** Remove all B3 files from PowerChart and Clinical from the Chroma index entirely (do not delete from `data/` — just exclude from ingest or tag as `demo_excluded`). Retag the product POV to focus on FHIR/API integration and Revenue Cycle processes. Be explicit in the UI that PowerChart and Clinical workflow content is "coverage limited — coming in Phase 3."

**Impact:** The demo corpus drops to ~50 high-quality files (33 B1 FHIR + 5 B2 FHIR + 9 B2 RCM + 2 B1 Millennium + 7 B2 Millennium) but every answer is defensible. Retrieval quality improves because the index has no garbage.

**Does not fix:** Client expectations if the sales pitch already covers PowerChart and Clinical as full capabilities.

**When to choose:** Choose this if you are presenting to a healthcare IT buyer or Oracle Health team and credibility matters more than breadth. Better to be honest about gaps than to have a demo challenged by an SME.

---

### Path C — Remove Synthetic, Keep Wiki

**Do:** Remove only the 11 explicitly SYNTHETIC files (SYNTHETIC marker in content). Keep the wiki.cerner.com files with a `source_quality: unverified` tag in their metadata. Add a disclaimer to query responses based on those chunks: "This answer draws on archival Cerner documentation that has not been independently verified against the current Oracle Health Help Center."

**Impact:** Index drops by 11 files (marginal). The wiki.cerner.com content stays, preserving PowerChart and Clinical workflow coverage for demo purposes. Risk: a knowledgeable audience member can still challenge the answer's provenance.

**When to choose:** Choose this as a short-term step before either Path A or Path B is executed. It removes the indefensible content (SYNTHETIC) while preserving functional demo coverage. It is not the final state — it is the minimum cleanup needed before any external presentation.

---

## Recommended Sequence

1. **Immediately:** Execute Path C — remove 11 SYNTHETIC files from the ingest index (do not delete from `data/`). Re-run `python ingest.py`. This takes 30 minutes and removes the most indefensible content.

2. **Within a week:** Execute Path A, Groups A + B (Oracle docs search + GitHub archive). ~2 hours. Fills the most impactful FHIR gaps with verifiable primary content.

3. **Before any external demo:** Implement Path B positioning — scope the demo narrative to FHIR + RCM, add "limited coverage" labels for PowerChart and Clinical in the UI. Do not present PowerChart or Clinical workflow answers as authoritative without uCern portal access.

4. **Phase 3 gate:** Obtain uCern/Oracle Help Center credentials. The 14 gated B5 items represent the only path to a fully credible clinical and PowerChart knowledge base. Without them, those modules will always carry an honesty caveat.

---

*Inventory generated: 2026-04-19 · Cerna Phase 2 Week 5 POV*  
*Files classified: 109 present · 35 absent (21 B4 · 14 B5)*
