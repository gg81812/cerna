# Millennium Platform — Cerna Knowledge Module

## Purpose
This module covers the Cerner Millennium EHR platform in full: system
architecture, domain and environment administration, CCL (Command and Control
Language) scripting, MPages framework development, Discern Analytics reporting,
upgrade lifecycle planning, OCI (Oracle Cloud Infrastructure) hosting, and
security/user management. Cerna uses these documents to answer administrator,
developer, and implementation consultant questions about the Millennium platform.

---

## Documents in This Folder

### Publicly Available (downloaded by scripts/scrape_kb.py)

| Filename | Source | Status |
|---|---|---|
| millennium-mpages-explained.txt | ehrenhancify.com | scraper |
| millennium-implementation-guide.txt | ghit.digital | scraper |
| millennium-integration-pathways.txt | tactionsoft.com | scraper |
| millennium-developer-program.txt | 6b.health | scraper |
| millennium-ccl-open-source.txt | engineering.cerner.com | scraper |

### uCern — Manual Download Required

| Filename | Priority | Gate |
|---|---|---|
| millennium-domain-administration-guide.txt | MUST | Gate 1 (Week 2) |
| millennium-ccl-programmer-reference.txt | MUST | Gate 1 (Week 2) |
| millennium-release-notes-current.txt | MUST | Gate 1 (Week 2) |
| millennium-mpages-development-guide.txt | SHOULD | Gate 2 (Week 3+) |
| millennium-discern-analytics-admin.txt | SHOULD | Gate 2 (Week 3+) |
| millennium-security-user-management.txt | SHOULD | Gate 2 (Week 3+) |
| millennium-upgrade-planning-guide.txt | SHOULD | Gate 2 (Week 3+) |
| millennium-oci-reference-architecture.txt | SHOULD | Gate 2 (Week 3+) |

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
- Module prefix: `millennium-`
- Extension: `.txt`
- Examples: `millennium-domain-administration-guide.txt`, `millennium-ccl-programmer-reference.txt`

---

## What Cerna Must Be Able to Answer from This Module

- How Millennium domain architecture is structured (MDF, environments, appservers)
- How to write and debug CCL scripts including common functions and system calls
- How to build and deploy MPages components (custom views in Millennium)
- How Discern Analytics works and how to create custom reports
- What the Millennium release cycle looks like and how upgrades are managed
- How user accounts, roles, and security policies are configured in Millennium
- How Millennium is deployed on Oracle Cloud Infrastructure (OCI)
- How to troubleshoot common Millennium platform issues
- What third-party integrations are possible through standard Millennium APIs
