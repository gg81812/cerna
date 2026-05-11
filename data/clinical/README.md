# Clinical Workflows — Cerna Knowledge Module

## Purpose
This module covers clinical care delivery workflows within Cerner: electronic
Medication Administration Records (eMAR), Barcode Medication Administration
(BCMA), nursing assessment and documentation, PharmNet pharmacy order
management, patient safety event reporting, scheduling and discharge workflows,
Emergency Department tracking (FirstNet), and perioperative management
(SurgiNet). Cerna uses these documents to answer nurse, pharmacist, and clinical
workflow/build questions.

---

## Documents in This Folder

### Publicly Available (downloaded by scripts/scrape_kb.py)

| Filename | Source | Status |
|---|---|---|
| clinical-implementation-build-guide.txt | ghit.digital | scraper |
| clinical-ai-scribe-powerchart.txt | notev.ai | scraper |

### uCern — Manual Download Required

| Filename | Priority | Gate |
|---|---|---|
| clinical-emar-user-guide.txt | MUST | Gate 1 (Week 2) |
| clinical-bcma-barcode-admin-guide.txt | MUST | Gate 1 (Week 2) |
| clinical-nursing-assessment-documentation.txt | MUST | Gate 1 (Week 2) |
| clinical-medication-administration-workflow.txt | MUST | Gate 1 (Week 2) |
| clinical-patient-safety-event-reporting.txt | MUST | Gate 1 (Week 2) |
| clinical-pharmnet-pharmacy-workflow.txt | SHOULD | Gate 2 (Week 3+) |
| clinical-scheduling-configuration-guide.txt | SHOULD | Gate 2 (Week 3+) |
| clinical-powerforms-admin-guide.txt | SHOULD | Gate 2 (Week 3+) |
| clinical-powerplans-admin-guide.txt | SHOULD | Gate 2 (Week 3+) |
| clinical-discharge-planning-guide.txt | SHOULD | Gate 2 (Week 3+) |
| clinical-ed-tracking-board-firstnet.txt | SHOULD | Gate 2 (Week 3+) |
| clinical-surgiNet-perioperative-workflow.txt | SHOULD | Gate 2 (Week 3+) |

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
- Module prefix: `clinical-`
- Extension: `.txt`
- Examples: `clinical-emar-user-guide.txt`, `clinical-bcma-barcode-admin-guide.txt`

---

## What Cerna Must Be Able to Answer from This Module

- How nurses administer medications using the eMAR in Cerner and what each administration status means
- How BCMA barcode scanning works and what to do when a scan fails or triggers an alert
- How nursing assessments and flowsheets are documented in Cerner PowerForms
- How PharmNet processes pharmacist order verification and medication dispensing
- How patient safety events (near misses, adverse events) are reported in Cerner
- How to configure and use the ED tracking board (FirstNet) for ED patient flow
- How SurgiNet manages perioperative workflow from pre-op through PACU
- How Powerforms and Powerplans are built and activated for clinical use
- How scheduling, admission, and discharge workflows flow through Cerner
- What clinical build tasks are required during a Cerner implementation
