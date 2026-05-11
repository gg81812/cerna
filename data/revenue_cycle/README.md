# Revenue Cycle — Cerna Knowledge Module

## Purpose
This module covers Cerner's Clinically Driven Revenue Cycle (CDRC) end-to-end:
charge capture from clinical documentation, charge review and reconciliation,
claims generation and submission, patient accounting, patient access (scheduling,
registration, insurance verification), RevElate (Cerner's cloud-based RCM
platform), Clinical Documentation Improvement (CDI), Health Information
Management (HIM) coding, denial management, and operational reporting.
Cerna uses these documents to answer revenue cycle analyst, biller, coder,
and RCM implementation questions.

---

## Documents in This Folder

### Publicly Available (downloaded by scripts/scrape_kb.py)

| Filename | Source | Status |
|---|---|---|
| rcm-cerner-product-overview.txt | cerner.com | scraper |
| rcm-charge-capture-reconciliation.txt | cerecore.net | scraper |
| rcm-cdrc-concept-explained.txt | techtarget.com | scraper |
| rcm-medcare-workflow-guide.txt | medcaremso.com | scraper |
| rcm-implementation-build-guide.txt | ghit.digital | scraper |

### uCern — Manual Download Required

| Filename | Priority | Gate |
|---|---|---|
| rcm-overview-module-map.txt | MUST | Gate 1 (Week 2) |
| rcm-charge-capture-configuration.txt | MUST | Gate 1 (Week 2) |
| rcm-charge-review-workflow.txt | MUST | Gate 1 (Week 2) |
| rcm-claims-management-guide.txt | MUST | Gate 1 (Week 2) |
| rcm-patient-accounting-user-guide.txt | MUST | Gate 1 (Week 2) |
| rcm-patient-access-guide.txt | SHOULD | Gate 2 (Week 3+) |
| rcm-revelate-product-guide.txt | SHOULD | Gate 2 (Week 3+) |
| rcm-cdi-integration-guide.txt | SHOULD | Gate 2 (Week 3+) |
| rcm-denial-management-guide.txt | SHOULD | Gate 2 (Week 3+) |
| rcm-him-coding-guide.txt | SHOULD | Gate 2 (Week 3+) |
| rcm-operational-reporting-guide.txt | SHOULD | Gate 2 (Week 3+) |

**ACTION REQUIRED**: Raise uCern access request immediately — approval takes 2–5 business days.

---

## How to Obtain Each Document

### Public documents (automated):
```
python scripts/scrape_kb.py
```

### uCern documents (manual):
1. Log in to https://cernercentral.com
2. Navigate to uCern > Search
3. Use the exact search terms listed in the placeholder files
4. Download PDF or copy text content
5. Replace the placeholder file with the actual content
6. Re-run: `python ingest.py`

---

## File Naming Convention
- Lowercase only
- Words separated by hyphens (`-`)
- Module prefix: `rcm-`
- Extension: `.txt`
- Examples: `rcm-charge-capture-configuration.txt`, `rcm-claims-management-guide.txt`

---

## What Cerna Must Be Able to Answer from This Module

- How Cerner's Clinically Driven Revenue Cycle (CDRC) philosophy links clinical documentation to billing
- How charge capture is triggered from clinical orders and documentation in Millennium
- How to configure charge review queues and reconcile charges before claim submission
- How claims are generated, scrubbed, and submitted through Cerner's clearinghouse
- How patient accounting (AR management, payment posting, collections) works in Cerner
- What RevElate is and how it differs from legacy Cerner RCM modules
- How CDI (Clinical Documentation Improvement) integrates with Cerner coding workflows
- How to manage denial queues and work denied claims to resolution
- How HIM coders use Cerner for ICD-10 and CPT coding
- What RCM reports are available and how to interpret key revenue cycle KPIs
