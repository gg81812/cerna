# PowerChart — Cerna Knowledge Module

## Purpose
This module covers PowerChart, Cerner's primary clinical documentation and order
management application used by physicians, nurses, and other clinicians. Topics
include patient list configuration, CPOE order entry, results review and inbox
management, PowerNote clinical documentation, PowerChart Touch (mobile),
MPages-based workflow views embedded in PowerChart, SMART app integration,
medication reconciliation, and clinical decision support (CDS) rules.
Cerna uses these documents to answer clinician workflow and build/configuration
questions about PowerChart.

---

## Documents in This Folder

### Publicly Available (downloaded by scripts/scrape_kb.py)

| Filename | Source | Status |
|---|---|---|
| powerchart-implementation-build.txt | ghit.digital | scraper |
| powerchart-mpages-overview.txt | ehrenhancify.com | scraper |
| powerchart-ai-integration-context.txt | notev.ai | scraper |

### uCern — Manual Download Required

| Filename | Priority | Gate |
|---|---|---|
| powerchart-user-guide.txt | MUST | Gate 1 (Week 2) |
| powerchart-patient-list-configuration.txt | MUST | Gate 1 (Week 2) |
| powerchart-cpoe-order-entry-workflow.txt | MUST | Gate 1 (Week 2) |
| powerchart-powernote-documentation.txt | MUST | Gate 1 (Week 2) |
| powerchart-results-review-inbox.txt | SHOULD | Gate 2 (Week 3+) |
| powerchart-touch-mobile-guide.txt | SHOULD | Gate 2 (Week 3+) |
| powerchart-medication-reconciliation.txt | SHOULD | Gate 2 (Week 3+) |
| powerchart-clinical-decision-support.txt | SHOULD | Gate 2 (Week 3+) |
| powerchart-workflow-mpages-admin.txt | SHOULD | Gate 2 (Week 3+) |

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
- Module prefix: `powerchart-`
- Extension: `.txt`
- Examples: `powerchart-user-guide.txt`, `powerchart-cpoe-order-entry-workflow.txt`

---

## What Cerna Must Be Able to Answer from This Module

- How to configure a PowerChart patient list (bands, filters, columns)
- How to enter a CPOE order including medication, lab, radiology, and referral orders
- How PowerNote works and how to build note templates using dot-phrases and auto-text
- How to review results in the inbox and manage result routing rules
- How PowerChart Touch differs from the desktop version and its clinical use cases
- How to configure clinical decision support alerts and order sets in CPOE
- How medication reconciliation workflow functions across care transitions
- How SMART apps are embedded in PowerChart using MPages
- How to troubleshoot common PowerChart workflow issues reported by clinicians
