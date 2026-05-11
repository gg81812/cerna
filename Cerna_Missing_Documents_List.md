# Cerna KB — Missing Documents List (Updated)
**Project:** Cerna · Cerner / Oracle Health AI Specialist  
**Phase:** 2 · Week 5 POV  
**Date Updated:** 2026-04-19  
**Prepared by:** Cerna KB Population Audit  

---

## Status Key

| Symbol | Meaning |
|--------|---------|
| ✅ COLLECTED | File scraped and saved to `data/[module]/` |
| ⚠️ BLOCKED | URL returned 403 / TLS error / timeout — manual download needed |
| ❌ NOT FOUND | URL returned 404 — find alternate source |
| 🔒 GATED | Requires uCern portal login — request access |

---

## How to Read This Document

| Column | Meaning |
|--------|---------|
| **Priority** | MUST = core KB gap · SHOULD = significant coverage gap · NICE = supplementary |
| **Access** | PUBLIC = no login required · GATED = uCern portal login required |
| **Filename** | Target filename to save under `data/[module]/` |
| **Source** | URL or system to retrieve from |

---

## Module 1 — FHIR & APIs

### 1.1 PUBLIC Sources

| # | Status | Priority | Filename | Source URL |
|---|--------|----------|----------|------------|
| 1 | ✅ COLLECTED | MUST | `fhir-smart-tutorial.txt` | engineering.cerner.com/smart-on-fhir-tutorial/ |
| 2 | ✅ COLLECTED | MUST | `fhir-oracle-api-r4-overview.txt` | docs.oracle.com (FHIR R4 overview) |
| 3 | ✅ COLLECTED | MUST | `fhir-smart-app-build-guide.txt` | docs.oracle.com/build-smart-on-fhir-apps/ |
| 4 | ✅ COLLECTED | MUST | `fhir-smart-app-overview.txt` | docs.oracle.com/smart-developer-overview/ |
| 5 | ✅ COLLECTED | MUST | `fhir-smart-app-provisioning.txt` | docs.oracle.com/smart-app-provisioning/ |
| 6 | ✅ COLLECTED | MUST | `fhir-faqs-common-issues.txt` | docs.oracle.com/fhir-faqs-common-issues/ |
| 7 | ❌ NOT FOUND | MUST | `fhir-revenue-cycle-rest-api.txt` | docs.oracle.com/revenue-cycle-management/rcrst/ — try searching Oracle docs for "Revenue Cycle REST API" |
| 8 | ✅ COLLECTED | MUST | `fhir-oracle-health-docs-hub.txt` | docs.oracle.com/en/industries/health/ — saved as `millennium-oracle-health-docs-hub.txt` |
| 9 | ⚠️ BLOCKED | MUST | `fhir-hl7-r4-specification.txt` | hl7.org/fhir/R4/ — SSL cert error; download manually from hl7.org/fhir/R4/ |
| 10 | ✅ COLLECTED | MUST | `fhir-smart-on-fhir-spec.txt` | docs.smarthealthit.org/ |
| 11 | ✅ COLLECTED | MUST | `fhir-engineering-blog-posts.txt` | engineering.cerner.com/blog/ |
| 12 | ⚠️ BLOCKED | MUST | `fhir-cerner-fhir-portal.txt` | fhir.cerner.com/ — blocked by security policy; access via browser and copy text |
| 13 | ⚠️ BLOCKED | SHOULD | `fhir-practitioner-role.md` | GitHub repo cerner/fhir.cerner.com archived May 2024; download from https://github.com/cerner/fhir.cerner.com/archive/refs/heads/main.zip |
| 14 | ⚠️ BLOCKED | SHOULD | `fhir-medication-statement.md` | Same — extract from downloaded zip |
| 15 | ⚠️ BLOCKED | SHOULD | `fhir-communication-resource.md` | Same — extract from downloaded zip |
| 16 | ✅ COLLECTED | SHOULD | `fhir-hl7-patient.txt` | hl7.org/fhir/R4/patient.html |
| 17 | ✅ COLLECTED | SHOULD | `fhir-hl7-medication-request.txt` | hl7.org/fhir/R4/medicationrequest.html |
| 18 | ✅ COLLECTED | SHOULD | `fhir-hl7-appointment.txt` | hl7.org/fhir/R4/appointment.html |
| 19 | ✅ COLLECTED | SHOULD | `fhir-hl7-observation.txt` | hl7.org/fhir/R4/observation.html |
| 20 | ✅ COLLECTED | SHOULD | `fhir-us-core-implementation-guide.txt` | hl7.org/fhir/us/core/ |
| 21 | ✅ COLLECTED | SHOULD | `fhir-cerner-integration-deep-dive.txt` | tactionsoft.com/blog/cerner-oracle-health-integration-guide/ |
| 22 | ✅ COLLECTED | SHOULD | `fhir-oracle-developer-program.txt` | 6b.health/insight/oracle-health-cerner-api-integration/ |
| 23 | ❌ NOT FOUND | SHOULD | `fhir-financial-transaction-api.txt` | docs.oracle.com (financial transaction FHIR) — search Oracle docs for "Financial Transaction FHIR API" |

**FHIR Public subtotal: 16 collected · 5 manual · 2 not found**

### 1.2 GATED Sources (uCern Login Required)

*None identified for FHIR — all primary sources are public.*

---

## Module 2 — Millennium

### 2.1 PUBLIC Sources

| # | Status | Priority | Filename | Source URL |
|---|--------|----------|----------|------------|
| 1 | ⚠️ BLOCKED | MUST | `millennium-oracle-community-forums.txt` | community.oracle.com/customerconnect — 403; log in and manually copy key discussion threads |
| 2 | ✅ COLLECTED | MUST | `millennium-oracle-health-docs-hub.txt` | docs.oracle.com/en/industries/health/ |
| 3 | ✅ COLLECTED | MUST | `millennium-platform-apis-index.txt` | docs.oracle.com/millennium-platform-apis/index.html |
| 4 | ❌ NOT FOUND | SHOULD | `millennium-oracle-cerner-overview.txt` | Medium article not found; try searching medium.com for "Oracle Cerner Millennium overview" and save the best result |
| 5 | ✅ COLLECTED | SHOULD | `millennium-6b-integration-overview.txt` | 6b.health/services/.../oracle-health-cerner-integration/ |
| 6 | ✅ COLLECTED | NICE | `millennium-oracle-wikipedia.txt` | en.wikipedia.org/wiki/Oracle_Cerner |

**Millennium Public subtotal: 4 collected · 1 manual · 1 not found**

### 2.2 GATED Sources (uCern Login Required)

| # | Status | Priority | Filename | Notes |
|---|--------|----------|----------|-------|
| 1 | 🔒 GATED | SHOULD | `millennium-oci-hosting-architecture.txt` | OCI hosting and cloud architecture documentation |
| 2 | 🔒 GATED | NICE | `millennium-performance-tuning.txt` | Millennium performance tuning guides |

---

## Module 3 — PowerChart

### 3.1 PUBLIC Sources

| # | Status | Priority | Filename | Source URL |
|---|--------|----------|----------|------------|
| 1 | ⚠️ BLOCKED | MUST | `powerchart-oracle-community-forums.txt` | community.oracle.com — 403; log in and manually copy key discussions |
| 2 | ⚠️ BLOCKED | SHOULD | `powerchart-cerner-ehr-consulting.txt` | capminds.com/cerner/ — TLS cert error; open in browser, copy text, save as .txt |

**PowerChart Public subtotal: 0 collected · 2 manual**

### 3.2 GATED Sources (uCern Login Required)

| # | Status | Priority | Filename | Notes |
|---|--------|----------|----------|-------|
| 1 | 🔒 GATED | SHOULD | `powerchart-workflow-mpages-admin.txt` | MPages administration and workflow configuration |
| 2 | 🔒 GATED | SHOULD | `powerchart-physician-advisor-config.txt` | Physician advisor configuration guide |
| 3 | 🔒 GATED | NICE | `powerchart-bpa-guide.txt` | Best Practice Advisory (BPA) configuration guide |
| 4 | 🔒 GATED | NICE | `powerchart-dynamic-documentation.txt` | Dynamic documentation / FlexTables guide |

---

## Module 4 — Revenue Cycle

### 4.1 PUBLIC Sources

| # | Status | Priority | Filename | Source URL |
|---|--------|----------|----------|------------|
| 1 | ⚠️ BLOCKED | MUST | `rcm-oracle-community-forums.txt` | community.oracle.com — 403; log in and manually copy key discussions |
| 2 | ❌ NOT FOUND | MUST | `rcm-billing-claims-solution.txt` | wcrt.webstaging.cerner.com — URL appears dead; search for "Cerner billing claims solution" on cerner.com or oracle.com |
| 3 | ❌ NOT FOUND | SHOULD | `rcm-financial-transaction-fhir.txt` | docs.oracle.com (FHIR financial transaction) — search Oracle docs for "Financial Transaction" |
| 4 | ✅ COLLECTED | SHOULD | `rcm-cdrc-techtarget-article.txt` | techtarget.com/searchhealthit/definition/revenue-cycle-management-RCM |
| 5 | ❌ NOT FOUND | SHOULD | `rcm-ehr-integration-overview.txt` | cpamedicalbilling.com — 404; search for "Cerner EHR medical billing integration" |
| 6 | ⚠️ BLOCKED | SHOULD | `rcm-cerner-consulting-rcm.txt` | capminds.com — TLS cert error; open in browser and copy text |
| 7 | ✅ COLLECTED | SHOULD | `rcm-hfma-denial-benchmarks.txt` | hfma.org/revenue-cycle-management/ — saved as `rcm-hfma-revenue-cycle.txt` |
| 8 | ⚠️ BLOCKED | SHOULD | `rcm-icd10-reference-cms.txt` | cms.gov/Medicare/Coding/ICD10 — timeout; open manually at cms.gov and download the ICD-10-CM 2025 code description file |
| 9 | ✅ COLLECTED | SHOULD | `rcm-cpt-lookup-ama.txt` | ama-assn.org/cpt |
| 10 | ❌ NOT FOUND | NICE | `rcm-nucc-place-of-service-codes.txt` | nucc.org — 404; try nucc.org directly and navigate to Place of Service code set |

**Revenue Cycle Public subtotal: 3 collected · 3 manual · 4 not found**

### 4.2 GATED Sources (uCern Login Required)

| # | Status | Priority | Filename | Notes |
|---|--------|----------|----------|-------|
| 1 | 🔒 GATED | SHOULD | `rcm-contract-pay-configuration.txt` | Contract management and payer configuration |
| 2 | 🔒 GATED | SHOULD | `rcm-operational-reporting.txt` | RCM operational reporting setup |
| 3 | 🔒 GATED | NICE | `rcm-case-management-utilization.txt` | Case management and utilization review config |

---

## Module 5 — Clinical Workflows

### 5.1 PUBLIC Sources

| # | Status | Priority | Filename | Source URL |
|---|--------|----------|----------|------------|
| 1 | ⚠️ BLOCKED | MUST | `clinical-oracle-community-forums.txt` | community.oracle.com — 403; log in and manually copy key discussions |
| 2 | ✅ COLLECTED | MUST | `clinical-hl7-medication-request.txt` | hl7.org/fhir/R4/medicationrequest.html — saved as `fhir-hl7-medication-request.txt`; copy or symlink |
| 3 | ✅ COLLECTED | MUST | `clinical-joint-commission-safety.txt` | jointcommission.org / americandatanetwork.com (2025 NPSGs) |
| 4 | ✅ COLLECTED | SHOULD | `clinical-hl7-appointment.txt` | hl7.org/fhir/R4/appointment.html — saved as `fhir-hl7-appointment.txt`; copy or symlink |
| 5 | ✅ COLLECTED | SHOULD | `clinical-hl7-observation.txt` | hl7.org/fhir/R4/observation.html — saved as `fhir-hl7-observation.txt`; copy or symlink |
| 6 | ✅ COLLECTED | SHOULD | `clinical-ana-nursing-standards.txt` | nursingworld.org/practice-policy/nursing-excellence/ |
| 7 | ⚠️ BLOCKED | SHOULD | `clinical-ismp-safety-guidelines.txt` | ismp.org/guidelines — redirects to ECRI login; purchase ISMP membership or access via institutional login |
| 8 | ✅ COLLECTED | SHOULD | `clinical-ismp-main.txt` | ismp.org (via ECRI redirect) |
| 9 | ⚠️ BLOCKED | SHOULD | `clinical-cms-medication-safety.txt` | cms.gov — persistent timeout; open manually at cms.gov and navigate to quality measures |
| 10 | ✅ COLLECTED | NICE | `clinical-cdc-immunization.txt` | cdc.gov/vaccines/hcp/imz-schedules/ |

**Clinical Public subtotal: 7 collected · 3 manual**

### 5.2 GATED Sources (uCern Login Required)

| # | Status | Priority | Filename | Notes |
|---|--------|----------|----------|-------|
| 1 | 🔒 GATED | SHOULD | `clinical-ed-tracking-board-firstnet.txt` | FirstNet ED tracking board configuration |
| 2 | 🔒 GATED | NICE | `clinical-surginet-perioperative.txt` | SurgiNet perioperative workflow guide |
| 3 | 🔒 GATED | NICE | `clinical-careguides-pathways.txt` | CareGuides and clinical pathway configuration |
| 4 | 🔒 GATED | NICE | `clinical-sepsis-alert-protocol.txt` | Sepsis BPA alert protocol setup |
| 5 | 🔒 GATED | NICE | `clinical-maternity-ob-workflow.txt` | Maternity / OB workflow configuration |

---

## Grand Total Summary (Updated)

| Module | Collected | Manual Needed | Not Found | Gated | Total Remaining |
|--------|-----------|---------------|-----------|-------|-----------------|
| FHIR & APIs | 16 | 5 | 2 | 0 | **7** |
| Millennium | 4 | 1 | 1 | 2 | **4** |
| PowerChart | 0 | 2 | 0 | 4 | **6** |
| Revenue Cycle | 3 | 3 | 4 | 3 | **10** |
| Clinical | 7 | 3 | 0 | 5 | **8** |
| **TOTAL** | **30** | **14** | **7** | **14** | **35** |

> **30 files collected automatically. 35 still require manual action.**

---

## Manual Collection Instructions

### ⚠️ BLOCKED — Browser Copy Required (14 files)

Open each URL in your browser, select all text (Ctrl+A), paste into a .txt file, and save to the correct `data/[module]/` folder.

| Filename | URL | Module Folder |
|----------|-----|---------------|
| `fhir-hl7-r4-specification.txt` | https://hl7.org/fhir/R4/ | `data/fhir/` |
| `fhir-cerner-fhir-portal.txt` | https://fhir.cerner.com/ | `data/fhir/` |
| `millennium-oracle-community-forums.txt` | https://community.oracle.com/customerconnect | `data/millennium/` |
| `powerchart-oracle-community-forums.txt` | https://community.oracle.com/customerconnect | `data/powerchart/` |
| `powerchart-cerner-ehr-consulting.txt` | https://capminds.com/cerner/ | `data/powerchart/` |
| `rcm-oracle-community-forums.txt` | https://community.oracle.com/customerconnect | `data/revenue_cycle/` |
| `rcm-cerner-consulting-rcm.txt` | https://capminds.com/cerner-ehr/ | `data/revenue_cycle/` |
| `rcm-icd10-reference-cms.txt` | https://www.cms.gov/Medicare/Coding/ICD10 | `data/revenue_cycle/` |
| `clinical-oracle-community-forums.txt` | https://community.oracle.com/customerconnect | `data/clinical/` |
| `clinical-ismp-safety-guidelines.txt` | https://www.ismp.org/guidelines | `data/clinical/` |
| `clinical-cms-medication-safety.txt` | https://www.cms.gov/medicare/quality | `data/clinical/` |
| `fhir-practitioner-role.md` | Download https://github.com/cerner/fhir.cerner.com/archive/refs/heads/main.zip then extract `content/millennium/r4/...` | `data/fhir/` |
| `fhir-medication-statement.md` | Same zip download as above | `data/fhir/` |
| `fhir-communication-resource.md` | Same zip download as above | `data/fhir/` |

### ❌ NOT FOUND — Find Alternate Source (7 files)

| Filename | Search Query | Module Folder |
|----------|-------------|---------------|
| `fhir-revenue-cycle-rest-api.txt` | Search docs.oracle.com for "Revenue Cycle REST API Millennium" | `data/fhir/` |
| `fhir-financial-transaction-api.txt` | Search docs.oracle.com for "Financial Transaction FHIR" | `data/fhir/` |
| `millennium-oracle-cerner-overview.txt` | Search medium.com for "Oracle Cerner Millennium overview" | `data/millennium/` |
| `rcm-billing-claims-solution.txt` | Search oracle.com or cerner.com for "billing claims solution" | `data/revenue_cycle/` |
| `rcm-financial-transaction-fhir.txt` | Search docs.oracle.com for "Financial Transaction FHIR API" | `data/revenue_cycle/` |
| `rcm-ehr-integration-overview.txt` | Search for "Cerner EHR revenue cycle integration overview" — any public source | `data/revenue_cycle/` |
| `rcm-nucc-place-of-service-codes.txt` | Visit nucc.org directly → Code Sets → Place of Service | `data/revenue_cycle/` |

### 🔒 GATED — uCern Portal Access Required (14 files)

Request access through your Accenture Oracle Health project credentials. Priority order:

1. `powerchart-workflow-mpages-admin.txt` — highest query impact
2. `powerchart-physician-advisor-config.txt` — high query impact
3. `rcm-contract-pay-configuration.txt` — frequent RCM config question
4. `rcm-operational-reporting.txt` — common admin workflow question
5. `clinical-ed-tracking-board-firstnet.txt` — common clinical config question
6. `millennium-oci-hosting-architecture.txt`
7. `rcm-case-management-utilization.txt`
8. `clinical-surginet-perioperative.txt`
9. `clinical-careguides-pathways.txt`
10. `clinical-sepsis-alert-protocol.txt`
11. `clinical-maternity-ob-workflow.txt`
12. `powerchart-bpa-guide.txt`
13. `powerchart-dynamic-documentation.txt`
14. `millennium-performance-tuning.txt`

---

## Duplicate / Shared Files — Copy Across Modules

These files were saved in FHIR but are also needed in Clinical. Copy them:

```bash
copy data\fhir\fhir-hl7-medication-request.txt data\clinical\clinical-hl7-medication-request.txt
copy data\fhir\fhir-hl7-appointment.txt data\clinical\clinical-hl7-appointment.txt
copy data\fhir\fhir-hl7-observation.txt data\clinical\clinical-hl7-observation.txt
```

---

## After Collecting Any File

Run the full pipeline:

```bash
python scripts/tag_documents.py
python ingest.py
```

Or for a quick single-module re-ingest, edit `ingest.py` to process only the target module folder.

---

## Notes

- `.txt` files: Plain text, strip HTML, keep headings and body content
- `.md` files: Keep as markdown — ingestion pipeline handles both
- uCern gated docs: Export as PDF, convert to .txt before ingestion
- Community forum threads: Copy 10–20 most relevant Q&A threads per module; save as single .txt with clear headings per thread

---

*Document last updated: 2026-04-19 · Cerna Phase 2 Week 5 POV*  
*Auto-scraped: 30 files · Manual still needed: 35 files*
