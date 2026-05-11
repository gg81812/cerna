# POV Positioning Changes — Path B UI Implementation
**Date:** 2026-04-19  
**Phase:** 2 · Week 5  
**Purpose:** Document the UI changes that implement Path B (FHIR + Revenue Cycle specialist) positioning, including module disclaimers and source quality signals.

---

## Background

The wiki spot-check (Step 2) established:
- FHIR and Revenue Cycle: primary-source coverage, demo-ready
- Millennium: archival + primary hybrid, demo-ready with disclaimer
- PowerChart and Clinical: archival-only (wiki.cerner.com archive), limited coverage

Path B positioning means the UI surface accurately reflects these coverage levels. A demo that signals its own boundaries is more credible than one that claims depth it doesn't have.

---

## Changes Made

### 1. Module Chip Labels (`ui/components.py` — MODULES dict)

| Module | Before | After |
|--------|--------|-------|
| PowerChart | `PowerChart` | `PowerChart (limited)` |
| Clinical | `Clinical` | `Clinical (limited)` |
| All others | Unchanged | Unchanged |

The `(limited)` suffix appears in the module selector dropdown and in the active-module badge in the header bar. It signals to users before they ask that these modules have constrained coverage.

---

### 2. Sample Suggestions (`SUGGESTIONS` list)

Removed two PowerChart-centric suggestions. Replaced with FHIR and Revenue Cycle queries.

**Before:**
```
- "How do I configure PowerChart patient lists?"
- "eMAR medication admin workflow"
```

**After (replacement slots):**
```
- "How do I search for a patient using the FHIR R4 API?"
- "What is RevElate and how does it differ from legacy Cerner Revenue Cycle?"
```

**Retained:**
- FHIR R4 authorization flow
- Revenue Cycle charge capture
- Millennium domain architecture
- CCL scripting best practices

---

### 3. Quick-Start Prompt Chips (`PROMPT_CHIPS` list)

Reordered and replaced to lead with FHIR + RCM + Millennium:

**Before:**
```
Millennium domain architecture
PowerChart patient list setup
FHIR R4 patient search params
Revenue Cycle charge routing
CCL scripting best practices
eMAR medication workflows
SMART on FHIR authorization
CDS Hooks integration guide
```

**After:**
```
FHIR R4 patient search params
SMART on FHIR authorization
Revenue Cycle charge routing
RevElate platform overview
Millennium domain architecture
CCL scripting best practices
CDS Hooks integration guide
FHIR Communication resource
```

PowerChart-specific and eMAR chips removed. "RevElate platform overview" and "FHIR Communication resource" added.

---

### 4. Left Panel Intro Bubble (`render_left_panel`)

**Before:**
```
I have deep expertise across Millennium, PowerChart, Revenue Cycle, FHIR & APIs,
and Clinical Workflows. Ask me anything about Cerner.
```

**After:**
```
Strongest on FHIR R4 & APIs and Revenue Cycle.
Solid on Millennium platform & CCL.
PowerChart and Clinical answers draw from archival
community docs — verify with Oracle Help Center.
```

This text appears as the first thing a user sees in the left panel. It accurately sets expectations before the first query.

---

### 5. Per-Response Module Banners (`render_cerna_response`)

A new `classification` parameter was added to `render_cerna_response`. When the LLM classifies a query as POWERCHART, CLINICAL, or MILLENNIUM, a coverage notice is appended below the response card.

**Banner text by module:**

| Module | Banner |
|--------|--------|
| PowerChart | "PowerChart answers are drawn from archival community documentation (wiki.cerner.com, pre-Oracle migration). Navigation paths and configuration options may differ in your Oracle Health environment. Verify with the Oracle Help Center." |
| Clinical | "Clinical workflow answers are drawn from archival community documentation (wiki.cerner.com, pre-Oracle migration). Clinical configuration steps may differ by site and product version. Verify with the Oracle Help Center before implementing." |
| Millennium | "Millennium answers may cite CCL and Discern documentation from the pre-Oracle wiki archive. Validate CCL code and domain configuration against your current Oracle Help Center reference." |

FHIR and Revenue Cycle do not show a banner (primary-source coverage).

**Banner CSS class:** `.module-banner` — amber/yellow tone to be noticed without alarming.

---

### 6. Source Quality Badges in Source Pills

Source pills in the response card now show a quality indicator:

| source_quality | Pill Style | Indicator |
|---------------|-----------|-----------|
| `primary` | Green tint | No extra marker |
| `secondary` | Purple tint (default) | No extra marker |
| `archival_secondary` | Amber tint | `⚠` glyph + tooltip: "Archival community documentation — verify before implementing" |

This flows from ChromaDB metadata → `RetrievedChunk.source_quality` → `_deduplicate_sources` → `render_cerna_response`.

---

### 7. Classification Passed Through Chat History

When replaying stored messages from session history, the stored `vertical` field is passed to `render_cerna_response`, ensuring banners appear consistently on old messages (not just on fresh responses).

---

## Files Changed

| File | Change |
|------|--------|
| `ui/components.py` | MODULES labels, SUGGESTIONS, PROMPT_CHIPS, intro bubble, render_cerna_response signature + banners + source quality pills, render_chat passes vertical |
| `ui/styles.py` | Added `.src-pill-primary`, `.src-pill-archival`, `.module-banner`, `.module-banner-icon` CSS |
| `app.py` | Passes `classification=classification` to `render_cerna_response` |

---

## Step 7 (Conditional)

The wiki spot-check result was 4/5 B2-archival → wiki corpus retained in ingest. Clinical module is NOT fully disabled. The Step 7 `clinical_module_disabled.md` is therefore skipped per instructions: "If wiki content is reclassified as B2-archival → keep in ingest."

Clinical answers are available but gated behind the per-response banner. The module filter selector shows "Clinical (limited)" to signal constrained coverage.

---

*Positioning changes complete: 2026-04-19 · Phase 2 Week 5 POV*
