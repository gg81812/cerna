# Scraper Run — 2026-04-19
**Phase:** 2 · Week 5  
**Scope:** KB Population Guide Groups A and B only (per Step 4 instructions)  
**Operator:** Cerna automated collection

---

## Summary

| Group | Target Files | Collected | Failed | Reason |
|-------|-------------|-----------|--------|--------|
| A — Oracle public docs | 4 | 0 | 4 | oracle.com/health returns HTTP 403; files do not exist on Millennium Platform APIs index |
| B — GitHub cerner/fhir.cerner.com archive | 3 | 1 | 2 | 2 files don't exist in the archived repo |
| **Total** | **7** | **1** | **6** | |

---

## Group A — Oracle Public Documentation (4 targets)

All Group A targets were checked against the Oracle Millennium Platform APIs index and direct oracle.com/health URLs.

**Outcome: 0 of 4 collected.**

| File | Target URL Pattern | Outcome | Reason |
|------|--------------------|---------|--------|
| `fhir-revenue-cycle-rest-api.txt` | oracle.com Millennium Platform APIs / Revenue Cycle | Not found | Not listed on Millennium Platform APIs public index |
| `fhir-financial-transaction-api.txt` | oracle.com Millennium Platform APIs / Financial Transaction | Not found | Not listed on Millennium Platform APIs public index |
| `rcm-financial-transaction-fhir.txt` | oracle.com FHIR financial transaction endpoints | Not found | No public Oracle page for this; FHIR financial endpoints are not published in the R4 sandbox documentation |
| `rcm-billing-claims-solution.txt` | oracle.com/health/revenue-cycle/patient-accounting/ (RevElate) | HTTP 403 | oracle.com/health serves HTTP 403 to automated requests; content confirmed to exist via web search results but cannot be scraped programmatically |

**RevElate content confirmed as existing** (via search results):
- oracle.com/health/revenue-cycle/patient-accounting/ — product page
- oracle.com/webfolder/community/oraclehealth/roadmaps/ — Revenue Cycle Feature Playbook PDF
- Multiple healthcare IT analyst references (Healthcare IT Leaders, BayCare implementation press release)

**Action required:** rcm-billing-claims-solution.txt can only be collected via browser. Open oracle.com/health/revenue-cycle/patient-accounting/ and oracle.com/webfolder/community/oraclehealth/roadmaps/ in a browser, copy the substantive content to `data/revenue_cycle/rcm-billing-claims-solution.txt`, and re-run ingest.

---

## Group B — GitHub Archive: cerner/fhir.cerner.com (3 targets)

The cerner/fhir.cerner.com repository was archived by GitHub in May 2024. It is read-only and publicly accessible.

**Content structure discovered:** Resources are organized at `content/millennium/r4/[category]/[resource-name]/[resource-name].md`

| File | GitHub Path Checked | Outcome | Reason |
|------|--------------------|---------|--------|
| `fhir-communication-resource.md` | `content/millennium/r4/clinical/request-and-response/communication.md` | **Collected** | File exists; full API documentation with search, retrieve, create, patch operations |
| `fhir-practitioner-role.md` | `content/millennium/r4/individuals/practitioner-role.md` | Not found (404) | PractitionerRole is not implemented in Cerner FHIR R4; resource does not appear in the repo's documented individuals resources |
| `fhir-medication-statement.md` | `content/millennium/r4/medications/medication-statement.md` | Not found (404) | MedicationStatement was deprecated in FHIR R4 and is not implemented by Cerner; resource does not exist in the repo |

---

## File Added to KB

### `data/fhir/fhir-communication-resource.md`

- **Source:** github.com/cerner/fhir.cerner.com (archived May 2024), `content/millennium/r4/clinical/request-and-response/communication.md`
- **Content:** Cerner FHIR R4 Communication resource reference — search parameters (`_id`, `category`, `recipient`, `received`, `-email-status`), retrieve by ID, create (POST), patch (PATCH/JSON Patch RFC 6902)
- **Format:** Markdown, ERB template tags stripped and replaced with plain notes
- **Sandbox tenant ID documented:** `ec2458f2-1e24-41c8-b71b-0e701af7583d`
- **Custom extensions documented:** `reply-to` (Reference), `email-status` (CodeableConcept)
- **Manifest classification:** doc_source=official, doc_type=spec, priority_tier=should, source_weight=1.0
- **Source quality:** primary

This file should be tagged in `scripts/doc_manifest.json` before the next ingest run to ensure it receives primary-tier weights.

---

## Impact Assessment

| Module | Before scraper run | After scraper run | Delta |
|--------|-------------------|-------------------|-------|
| FHIR | 23 active files | 24 active files | +1 (Communication resource) |
| Revenue Cycle | 18 active files | 18 active files | +0 |

The Communication resource adds coverage for:
- Secure messaging / care team communication workflows
- In-app notification retrieval via FHIR
- FHIR message payload handling (Binary resource integration)
- Patch operations on existing communications

---

## Unresolved Items

The following KB Population Guide targets remain uncollected after this scraper run:

| File | Priority | Path to Resolution |
|------|----------|--------------------|
| `rcm-billing-claims-solution.txt` | SHOULD | Browser collection from oracle.com/health/revenue-cycle/ |
| `fhir-revenue-cycle-rest-api.txt` | NICE | May not exist as a public Oracle document; check Oracle Help Center directly |
| `fhir-financial-transaction-api.txt` | NICE | Same as above |
| `rcm-financial-transaction-fhir.txt` | NICE | Same as above |

The 14 uCern-gated documents (Groups C–E) remain blocked pending the access decision documented in `docs/ucern_access_decision.md`.

---

*Scraper run completed: 2026-04-19 · Phase 2 Week 5*
