# FHIR & Integrations — Cerna Knowledge Module

## Purpose
This module covers the Cerner FHIR R4 API surface, SMART on FHIR application
patterns, OAuth 2.0 authorization flows, HL7 v2 messaging, CareAware Connect,
and all integration patterns used when connecting external systems to Cerner
Millennium. Cerna uses these documents to answer developer and integration
questions about building on the Cerner platform.

---

## Documents in This Folder

### Publicly Available (downloaded by scripts/scrape_kb.py)

| Filename | Source | Status |
|---|---|---|
| fhir-r4-overview.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-patient-resource.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-practitioner-resource.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-practitioner-role.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-related-person.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-encounter-resource.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-organization-resource.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-location-resource.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-allergy-intolerance.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-condition-resource.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-medication-request.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-medication-statement.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-observation-resource.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-diagnostic-report.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-document-reference.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-procedure-resource.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-immunization-resource.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-care-plan.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-goal-resource.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-appointment.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-slot-resource.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-coverage-resource.md | GitHub — cerner/fhir.cerner.com | scraper |
| fhir-binary-resource.md | GitHub — cerner/fhir.cerner.com | scraper |

### Additional Documents Listed in Original Spec (add if found)
| Filename | Notes |
|---|---|
| fhir-smart-on-fhir-guide.md | SMART on FHIR launch sequence |
| fhir-oauth2-authorization.md | OAuth 2.0 token flows |
| fhir-smart-app-provisioning.md | CernerCentral SMART app registration |
| fhir-faqs-common-issues.md | Common API errors and solutions |
| fhir-r4-api-overview-oracle.md | Oracle Health docs mirror |
| fhir-revenue-cycle-api.md | FHIR financial resources |
| fhir-hl7-v2-vs-fhir.md | HL7 v2 to FHIR comparison |
| fhir-careaware-connect.md | CareAware Connect architecture |

---

## How to Obtain Each Document

### Public documents (automated):
```
python scripts/scrape_kb.py
```
Source: `https://raw.githubusercontent.com/cerner/fhir.cerner.com/main/content/millennium/`

### Oracle Health Docs (manual):
1. Visit https://docs.oracle.com/en/industries/health/
2. Navigate to Cerner > Millennium > FHIR R4
3. Download or copy content into this folder

### uCern / CernerCentral (manual):
1. Log in to https://cernercentral.com
2. Search by exact filename (minus extension)
3. Download PDF or copy text content

---

## File Naming Convention
- Lowercase only
- Words separated by hyphens (`-`)
- Module prefix: `fhir-`
- Extension: `.md` for FHIR resource docs, `.txt` for guide documents
- Examples: `fhir-patient-resource.md`, `fhir-smart-on-fhir-guide.md`

---

## What Cerna Must Be Able to Answer from This Module

- How to read a Patient resource from the Cerner FHIR R4 API
- What search parameters are supported for each FHIR resource
- How to implement SMART on FHIR app launch (EHR launch and standalone launch)
- What OAuth 2.0 scopes are required for clinical data access
- How to register a SMART app in CernerCentral
- The difference between HL7 v2 messages and FHIR R4 resources in Cerner
- How to retrieve medication, allergy, condition, and observation data via FHIR
- How to use the Coverage and Appointment resources for revenue cycle workflows
- What Cerner-specific extensions exist on standard FHIR resources
- How CareAware Connect fits into the Cerner integration landscape
