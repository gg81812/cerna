# KB Status After Cleanup — Steps 1–3
**Date:** 2026-04-19  
**Phase:** 2 · Week 5  
**Purpose:** Document the KB state after synthetic file removal (Step 1), wiki reclassification (Steps 2–3), and manifest key bug fix.

---

## Summary of Changes Applied

| Change | Scope | Impact |
|--------|-------|--------|
| 11 SYNTHETIC files added to INGEST_EXCLUDE | FHIR ×1, Millennium ×3, PowerChart ×5, Clinical ×2 | −89 chunks (Step 1 baseline: 1,192 → 1,103) |
| 1 B3-suspect wiki file added to INGEST_EXCLUDE | Clinical: `clinical-bcma-barcode-admin-guide.txt` | −additional Clinical chunks |
| 33 wiki files reclassified: doc_source → archival_secondary, source_weight → 0.7 | All modules | Downstream source_quality metadata in retriever |
| Manifest key bug fixed in ingest.py | All modules | Manifest lookup was always returning `{}` (keys used parent-relative paths, manifest uses project-relative). Now fixed: `os.path.relpath(path, BASE_DIR)` |
| `fhir-communication-resource.md` added | FHIR | +1 new official Cerner FHIR R4 document |
| `source_quality` metadata field added to ingest pipeline | All | Chunks now carry `primary` / `secondary` / `archival_secondary` tag for UI source badges |

---

## Chunk Counts

| Stage | Chunks | Notes |
|-------|--------|-------|
| Baseline (all docs, no exclusions) | 1,192 | Phase 2 Week 3 baseline |
| After Step 1 (11 SYNTHETIC excluded) | 1,103 | Bug: manifest key was silently failing; all docs chunked with prose strategy |
| **After Steps 2–3 (full cleanup + manifest key fix)** | **1,322** | **Current state** |

The +219 delta from Step 1 to Step 3 is explained by the manifest key fix: FHIR spec documents now correctly use the `reference` strategy (600 chars / 50 overlap) instead of the `prose` fallback (1000 chars / 150 overlap), producing finer-grained chunks from the same text.

### By Chunking Strategy
| Strategy | Chunks | Notes |
|----------|--------|-------|
| reference | 437 | FHIR spec, official Oracle docs (600-char chunks) |
| workflow | 408 | eMAR, CPOE, build guides, step-heavy docs (1500-char) |
| prose | 477 | Overviews, architecture, blog posts (1000-char) |
| **Total** | **1,322** | |

---

## Per-Module Document Counts

| Module | Real Docs | Excluded | Notes |
|--------|-----------|---------|-------|
| Millennium | 16 | 3 | Excluded: ccl-performance-tuning, code-sets-guide, discern-rules-engine (SYNTHETIC) |
| PowerChart | 10 | 5 | Excluded: ai-integration-context, ai-predictive-ordering, cpoe-alert-configuration, hl7-lab-integration, order-sets-cpoe-config (SYNTHETIC) |
| Revenue Cycle | 18 | 0 | All real docs retained |
| FHIR | 39 | 1 | 1 SYNTHETIC excluded (developer-program-guide); Communication resource added |
| Clinical | 15 | 3 | Excluded: bcma-barcode-admin-guide (B3-suspect wiki), firstnet-ed-tracking (SYNTHETIC), surginet-perioperative (SYNTHETIC) |
| **Total** | **98** | **12** | |

---

## Source Quality Distribution

After the manifest key fix and archival_secondary reclassification, chunks now carry the correct `source_quality` tag in ChromaDB metadata:

| source_quality | Approximate Chunk Count | Sources |
|---------------|------------------------|---------|
| primary | ~440 | Official FHIR R4 specs (hl7_cerner, official), Oracle docs |
| secondary | ~300 | Engineering blog posts, third-party Cerner guides |
| archival_secondary | ~580 | wiki.cerner.com archive (pre-Oracle migration), reweighted to 0.7 |

The `source_quality` field flows through: ChromaDB metadata → `RetrievedChunk.source_quality` → `chunk_to_dict` → `_deduplicate_sources` → UI source pills.

---

## Collections State

| Collection | Embedding Model | Chunks | Status |
|-----------|----------------|--------|--------|
| `cerner_docs` (MiniLM) | all-MiniLM-L6-v2 (384-dim) | 1,322 | ✅ Complete |
| `cerner_docs_bge` (BGE) | BAAI/bge-large-en-v1.5 (1024-dim) | 1,103 | ⏳ Rebuilding — will be 1,322 after current run |

The BGE collection is being rebuilt from the updated MiniLM collection. Until it completes, the active collection (set by `COLLECTION=cerner_docs_bge` in `.env`) will serve slightly stale embeddings.

---

## Module Demo Readiness (Updated)

| Module | Status | Primary Sources | Archival Coverage | Notes |
|--------|--------|----------------|-------------------|-------|
| FHIR & APIs | **Demo-ready** | 35+ primary | None | Strongest module. 21st Cures compliance coverage. |
| Revenue Cycle | **Demo-ready** | 18 real docs | None | RevElate + CDRC model. Competitive differentiator. |
| Millennium | **Demo-ready with disclaimer** | 5+ primary (CCL OSS, platform guides) | 7 wiki | CCL answers should cite version/Oracle migration caveat |
| PowerChart | **Limited — archival only** | 0 primary | 10 wiki | All real docs are wiki archive. Verify with Oracle Help Center. |
| Clinical | **Limited — archival only** | 0 primary | 15 wiki | Same. BCMA guide excluded. FirstNet excluded. |

**For Phase 2 POV demo:** Lead with FHIR + Revenue Cycle. Use Millennium for platform architecture questions. Treat PowerChart and Clinical as bonus coverage with explicit disclaimer.

---

## Configuration Files Changed

| File | Change |
|------|--------|
| `config.py` | Added `INGEST_EXCLUDE` (12 files) |
| `ingest.py` | Added exclusion check, fixed manifest key bug (`BASE_DIR` not `os.path.dirname(BASE_DIR)`), added `source_quality` metadata, replaced `shutil.rmtree` with collection-level delete |
| `retriever.py` | Added `source_quality` field to `RetrievedChunk` dataclass |
| `state.py` | Added `source_quality` to `chunk_to_dict` and `dict_to_chunk` |
| `pipeline.py` | Added `source_quality` to `_deduplicate_sources` output |
| `ui/components.py` | Path B positioning: updated prompts/chips, module labels, banners, source pill quality badges |
| `ui/styles.py` | CSS for archival/primary source pills and module banner |
| `scripts/doc_manifest.json` | 33 wiki files → archival_secondary + weight 0.7; Communication resource added |

---

*KB cleanup complete: 2026-04-19 · Phase 2 Week 5*
