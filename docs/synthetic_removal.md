# Synthetic File Removal — Step 1 Execution Log
**Date:** 2026-04-19  
**Phase:** 2 · Week 5  
**Purpose:** Remove AI-generated synthetic files from the ingest pipeline to improve KB accuracy.

---

## What Was Done

11 files bearing the `SYNTHETIC KNOWLEDGE BASE` marker were identified across 4 modules and excluded from ingest via the `INGEST_EXCLUDE` frozenset in `config.py`. Files remain on disk; exclusion is pipeline-only (no deletion).

---

## Excluded Files

| # | Module | Filename | Reason |
|---|--------|----------|--------|
| 1 | FHIR | `fhir-developer-program-guide.txt` | SYNTHETIC marker — AI-generated content, no primary source |
| 2 | Millennium | `millennium-code-sets-guide.txt` | SYNTHETIC marker |
| 3 | Millennium | `millennium-ccl-performance-tuning.txt` | SYNTHETIC marker |
| 4 | Millennium | `millennium-discern-rules-engine.txt` | SYNTHETIC marker |
| 5 | PowerChart | `powerchart-ai-integration-context.txt` | SYNTHETIC marker |
| 6 | PowerChart | `powerchart-ai-predictive-ordering.txt` | SYNTHETIC marker |
| 7 | PowerChart | `powerchart-cpoe-alert-configuration.txt` | SYNTHETIC marker |
| 8 | PowerChart | `powerchart-hl7-lab-integration.txt` | SYNTHETIC marker |
| 9 | PowerChart | `powerchart-order-sets-cpoe-config.txt` | SYNTHETIC marker |
| 10 | Clinical | `clinical-firstnet-ed-tracking.txt` | SYNTHETIC marker |
| 11 | Clinical | `clinical-surginet-perioperative.txt` | SYNTHETIC marker |

---

## Chunk Counts

| Metric | Value |
|--------|-------|
| Chunks before removal (baseline) | 1,192 |
| Chunks after removal | 1,103 |
| Delta | −89 chunks |

The 89-chunk reduction is distributed across 4 modules: FHIR (−1 file), Millennium (−3 files), PowerChart (−5 files), Clinical (−2 files). RCM was unaffected.

Per-module chunk counts after the full Step 3 cleanup (BCMA exclusion + manifest re-tag + re-ingest) are documented in `docs/kb_status_after_cleanup.md`.

---

## Module Viability Assessment

No module dropped below a viable retrieval threshold:

| Module | Files Removed | Assessment |
|--------|--------------|------------|
| FHIR | 1 | Unaffected — 37+ real documents remain; strongest module |
| Millennium | 3 | Viable — 7+ real documents remain (CCL reference, platform guide, SMART/OAuth) |
| PowerChart | 5 | **Constrained** — 14 active docs, all B2-archival wiki. No primary sources. Demo requires disclaimer. |
| Clinical | 2 | **Constrained** — 15 active docs, majority B2-archival wiki. Same caveat as PowerChart. |
| RCM | 0 | Unaffected — 18 active documents, solid CDRC + RevElate coverage |

PowerChart and Clinical were already the weakest modules before removal. Removing synthetic content makes their retrieval boundaries more honest, not less functional — the KB no longer returns plausible-sounding fabricated content for questions it cannot answer accurately.

---

## Code Changes

**`config.py`** — Added `INGEST_EXCLUDE` frozenset (bottom of file):
```python
INGEST_EXCLUDE: frozenset = frozenset({
    "fhir-developer-program-guide.txt",
    "millennium-code-sets-guide.txt",
    "millennium-ccl-performance-tuning.txt",
    "millennium-discern-rules-engine.txt",
    "powerchart-ai-integration-context.txt",
    "powerchart-ai-predictive-ordering.txt",
    "powerchart-cpoe-alert-configuration.txt",
    "powerchart-hl7-lab-integration.txt",
    "powerchart-order-sets-cpoe-config.txt",
    "clinical-firstnet-ed-tracking.txt",
    "clinical-surginet-perioperative.txt",
})
```

**`ingest.py`** — Added exclusion check in `load_module()` before placeholder check; replaced `shutil.rmtree` with collection-level `chromadb.PersistentClient.delete_collection()` to preserve the `cerner_docs_bge` collection across rebuilds.

---

## Ingest Commands Run

```bash
python ingest.py
# → 1,103 chunks stored to cerner_docs (MiniLM collection)

python scripts/ingest_bge.py
# → re-embeds 1,103 chunks into cerner_docs_bge (BGE-large-en-v1.5)
```

The BGE re-embed was triggered immediately after the MiniLM ingest. Both collections reflect the same 1,103-chunk corpus after these runs.

---

*Step 1 complete — proceed to Step 2 (wiki spot-check) and Step 3 (manifest cleanup + re-ingest).*
