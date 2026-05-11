# UI Disclaimer Path Verification — 2026-04-20
**Phase:** 2 · Week 5  
**Collection:** `cerner_docs_bge` · **Method:** Programmatic pipeline verification + component code inspection  
**Note:** Visual browser verification was not performed (no live Streamlit session). All signals are captured at the orchestrator/pipeline boundary and matched against `ui/components.py` rendering logic.

---

## Summary

| Path | Expected UI Element | Pipeline Signal | Status |
|------|---------------------|-----------------|--------|
| PowerChart query | LIMITED banner + POWERCHART label | `classification=POWERCHART` | ✅ PASS |
| Clinical query | LIMITED banner + CLINICAL label | `classification=CLINICAL` | ✅ PASS |
| FHIR query | FHIR module label, no LIMITED | `classification=FHIR` | ✅ PASS |
| Millennium query | MILLENNIUM module label | `classification=MILLENNIUM` | ✅ PASS |
| High-confidence answer | Green/no badge | `confidence=high` | ✅ PASS |
| OOS/clinical refusal | CONFIDENCE: LOW badge | `confidence=low` | ✅ PASS |
| Casual greeting | No LOW badge | `confidence=high` (after bug fix) | ✅ PASS (fix verified) |
| Did-You-Mean path | Suggestion chips, no answer | `prepared.did_you_mean` populated | ⚠ PARTIAL (see note) |
| Archival source pill | ⚠ archival pill on source | `source_quality=archival_secondary` | ✅ PASS (code path verified) |
| Primary source pill | Primary-styled pill | `source_quality=primary` | ✅ PASS (code path verified) |
| Secondary source pill | Default pill | `source_quality=secondary` | ✅ PASS |

---

## Scenario Results

### 1–3. PowerChart Queries (LIMITED Module)

Three PowerChart queries run through the full pipeline:

| ID | Query | Classification | Confidence | Refusal | DYM | Top Chunk Score | Top Quality |
|----|-------|---------------|------------|---------|-----|-----------------|-------------|
| pc-ui-1 | What is PowerNote in Cerner? | POWERCHART | high | No | No | 0.728 | secondary |
| pc-ui-2 | How do I configure a patient list in PowerChart? | POWERCHART | high | No | No | 0.554 | secondary |
| pc-ui-3 | How does results review work in PowerChart? | POWERCHART | high | No | No | 0.506 | secondary |

**Expected UI:** Module banner renders ("PowerChart answers are drawn from archival community documentation…"), confidence badge green/absent, source pills in default secondary style.

**Code path verified:** `_MODULE_BANNERS.get("powerchart")` is populated in `ui/components.py:75–82`. `_LIMITED_MODULES = {"powerchart", "clinical"}` at line 72. All three queries correctly classified as `POWERCHART`.

**Status: ✅ PASS** — All 3 correctly route to LIMITED module path.

---

### 4–6. Clinical Queries (LIMITED Module)

| ID | Query | Classification | Confidence | Refusal | DYM | Top Chunk Score | Top Quality |
|----|-------|---------------|------------|---------|-----|-----------------|-------------|
| cli-ui-1 | What is eMAR in Cerner? | CLINICAL | high | No | No | 0.814 | secondary |
| cli-ui-2 | How does BCMA scanning work? | CLINICAL | high | No | No | 0.692 | secondary |
| cli-ui-3 | What is PharmNet in Cerner? | CLINICAL | high | No | No | 0.758 | secondary |

**Note on cli-ui-1:** `understand_query` fell back to a cached/default path (429 TPM rate limit on classify model mid-run). Still correctly resolved to CLINICAL module.

**Status: ✅ PASS** — All 3 correctly classified as CLINICAL with LIMITED banner path.

---

### 7–8. FHIR Queries (Strong Module, No LIMITED)

| ID | Query | Classification | Confidence | Refusal | DYM | Top Chunk Score |
|----|-------|---------------|------------|---------|-----|-----------------|
| fhir-ui-1 | What FHIR version does Cerner support? | FHIR | high | No | No | 0.681 |
| fhir-ui-2 | How does SMART on FHIR app launch work? | FHIR | high | No | No | 0.629 |

**Expected UI:** FHIR module label visible, no LIMITED banner (FHIR is not in `_LIMITED_MODULES`), confidence badge green.

**Status: ✅ PASS** — No spurious LIMITED banner for FHIR queries.

---

### 9–10. Millennium Queries

| ID | Query | Classification | Confidence | Refusal | DYM | Top Chunk Score |
|----|-------|---------------|------------|---------|-----|-----------------|
| mil-ui-1 | What is CCL scripting in Cerner? | MILLENNIUM | high | No | No | 0.704 |
| mil-ui-2 | What are MPages in Cerner? | MILLENNIUM | high | No | No | 0.538 |

**Status: ✅ PASS** — Correct classification, no LIMITED banner.

---

### 11. Did-You-Mean Scenario

**Query tested:** "powerchat chart orders"  
**Result:** `classification=POWERCHART, confidence=high, dym=False, top_score=0.713`

The `understand_query` step rewrote this to "PowerChart medication order entry workflow" — yielding a score well above the DYM threshold (0.40). The DYM path was NOT triggered.

**Finding:** The `understand_query` model (llama3-8b) normalizes vague or misspelled queries very aggressively. Any string with recognizable Cerner vocabulary (even "powerchat") gets rewritten to a well-formed formal query that clears the DYM threshold. In practice, the DYM path fires only for queries where the vocabulary is entirely outside the KB even after rewriting.

**Confirmed DYM trigger** (from golden eval, not this session): `clin-014` "What are the build steps to configure BCMA overrides and exception workflows?" — formal query still retrieved score 0.396 (below threshold 0.40) → hit DYM path → response was "I'm not sure which Cerner topic you're asking about."

**Code path verified:** `app.py:178` — `elif prepared.did_you_mean:` block creates a `CernaResponse` with `confidence="low"` and sets `follow_ups = prepared.did_you_mean`. The follow-up chips render via `query_variants` parameter in `render_cerna_response`. Logic is correct.

**Status: ⚠ PARTIAL** — DYM path code is verified correct, and DID fire on clin-014 in the golden eval. No new DYM trigger found in the 11 standard queries because understand_query normalizes queries effectively. This is the intended behavior; the path is not broken.

---

## Source Quality Pill Verification

### Archival Pill (⚠ archival_secondary)

**ChromaDB state:** 27 chunks with `source_quality=archival_secondary`, all from Millennium (CCL programmer reference, Discern Analytics admin guide — both PLACEHOLDER files requiring manual download).

**Direct semantic query test** ("CCL SELECT data types best practices", module=millennium):
- Top result: `millennium-mpages-development-guide.txt | archival_secondary | 0.556`
- 2nd result: `millennium-ccl-programmer-reference.txt | archival_secondary | 0.546`

Confirms archival chunks ARE retrieved for relevant queries and carry correct `source_quality=archival_secondary`.

**Code path:** `ui/components.py:487–493` — when `sq == "archival_secondary"`, renders `<span class="src-pill src-pill-archival" title="Archival community documentation — verify before implementing">{source} ⚠</span>`.

**Why not triggered in standard UI queries:** The 11 standard queries retrieved secondary content as top chunks because there are 158 secondary vs 27 archival chunks. Archival content only surfaces for specific Millennium CCL/Discern queries that match the placeholder documents. Once the PLACEHOLDER files are replaced with real content (requires manual download), the archival pill frequency may change.

**Status: ✅ PASS** — Archival pill renders correctly when archival chunks are in top-5.

### Primary Pill

**ChromaDB state:** 15 chunks with `source_quality=primary`, from `ucern`, `open_cerner`, `official` doc sources.

**Code path:** `ui/components.py:494–495` — `elif sq == "primary"`, renders `<span class="src-pill src-pill-primary">{source}</span>`.

**Status: ✅ PASS** — Primary pill code path verified, 15 primary chunks exist in collection.

---

## Confidence Badge Behavior

### Casual Greeting Fix (app.py bug fixed this session)
**Bug:** "What is Cerner?" and other casual greetings previously showed CONFIDENCE: LOW badge because `parse_structured("", prepared)` hardcoded `confidence="low"` for any refusal path.

**Fix applied:** `app.py:164–173` — added `if prepared.refusal:` guard before streaming, creates `CernaResponse` directly with `confidence="high" if prepared.intent == "casual" else "low"`.

**Verified:** The fix correctly handles:
- Casual greeting → `intent=casual` → `confidence=high` → green/no badge ✅
- OOS query → `intent=out_of_scope` → `confidence=low` → red LOW badge ✅
- Clinical decision → `intent=clinical_decision` → `confidence=low` → red LOW badge ✅

### Confidence Values Observed
All 11 UI verification queries returned `confidence=high` — expected since all are legitimate in-scope questions with good chunk scores (0.506–0.814).

---

## Module Banner Copy Verification

| Module | Banner shown? | Banner text excerpt |
|--------|---------------|---------------------|
| POWERCHART | Yes (`_LIMITED_MODULES`) | "PowerChart answers are drawn from archival community documentation…" |
| CLINICAL | Yes (`_LIMITED_MODULES`) | "Clinical workflow answers are drawn from archival community documentation…" |
| FHIR | No | (no banner for FHIR) |
| MILLENNIUM | No | (no banner for MILLENNIUM) |
| REVENUE_CYCLE | No | (no banner for REVENUE_CYCLE) |

**Confirmed in `ui/components.py:72–82`.**

---

## Issues Found

None blocking. One observation:

**OOS-009 edge case** (from golden eval): "How does Epic's patient portal compare to MyChart?" → classified as GENERAL (not OOS refusal) because MyChart is a Cerner product. The system answers from the Cerner angle. This is a reasonable behavior (Cerner-side content exists) but the response doesn't include a disclaimer that the Epic-side comparison is outside scope. Low priority.

---

*Verification run: 2026-04-20 · Phase 2 Week 5 · programmatic pipeline verification*
