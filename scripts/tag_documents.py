"""
scripts/tag_documents.py — Inspect every document and produce a metadata manifest.

Infers doc_source, doc_type, priority_tier, source_weight, and last_updated
from filename patterns, folder names, and content heuristics.

Output: scripts/doc_manifest.json
  {
    "data/fhir/fhir-patient-resource.md": {
      "doc_source":    "open_cerner",
      "doc_type":      "spec",
      "priority_tier": "must",
      "source_weight": 0.9,
      "last_updated":  "2025-11-12"
    },
    ...
  }

ingest.py reads this manifest and attaches the fields as chunk metadata.

Usage:
    python scripts/tag_documents.py
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATA_DIR, SCRIPTS_DIR

MANIFEST_PATH = os.path.join(SCRIPTS_DIR, "doc_manifest.json")
OVERRIDES_PATH = os.path.join(SCRIPTS_DIR, "doc_manifest_overrides.json")

# ── Source classification rules ───────────────────────────────────────────────
# Applied in order; first match wins.

_FILENAME_RULES: list[tuple[str, dict]] = [
    # Official Cerner engineering blog / open.cerner.com posts
    (r"(engineering|blog|open-cerner|ccl-open-source|developer-program)", {
        "doc_source": "engineering_blog", "doc_type": "blog",
        "priority_tier": "should", "source_weight": 0.7,
    }),
    # FHIR spec / HL7 resources
    (r"fhir-(r4|resource|patient|appointment|allergy|condition|binary|care|observation|med)", {
        "doc_source": "hl7_cerner", "doc_type": "spec",
        "priority_tier": "must", "source_weight": 0.9,
    }),
    # Cerner product overview / concept docs
    (r"(product-overview|concept|philosophy|cdrc|rcm-cerner)", {
        "doc_source": "open_cerner", "doc_type": "official",
        "priority_tier": "must", "source_weight": 0.9,
    }),
    # Build / implementation / configuration guides
    (r"(build|implementation|config|guide|admin|setup)", {
        "doc_source": "ucern", "doc_type": "official",
        "priority_tier": "must", "source_weight": 1.0,
    }),
    # Reconciliation / workflow / workflow docs
    (r"(reconciliation|workflow|charge-capture|emar|bcma|cpoe|powerchart-ai|clinical-ai)", {
        "doc_source": "ucern", "doc_type": "official",
        "priority_tier": "must", "source_weight": 1.0,
    }),
    # CDI / HIM / revenue cycle detailed
    (r"(cdi|him|denial|claims|revenue|rcm)", {
        "doc_source": "ucern", "doc_type": "official",
        "priority_tier": "must", "source_weight": 1.0,
    }),
    # CCL / MPages / developer content
    (r"(ccl|mpages|millennium-domain|millennium-dev|millennium-ccl)", {
        "doc_source": "open_cerner", "doc_type": "official",
        "priority_tier": "must", "source_weight": 0.9,
    }),
]

# Default when no rule matches
_DEFAULT_META = {
    "doc_source": "third_party", "doc_type": "community",
    "priority_tier": "nice", "source_weight": 0.5,
}

# Source weight overrides by doc_source
_SOURCE_WEIGHTS = {
    "ucern":            1.0,
    "open_cerner":      0.9,
    "hl7_cerner":       0.9,
    "engineering_blog": 0.7,
    "third_party":      0.5,
    "community_forum":  0.3,
}


def _classify_file(filepath: str, fname: str) -> dict:
    """Return doc_source, doc_type, priority_tier, source_weight for a given file."""
    fname_lower = fname.lower().replace("_", "-")
    for pattern, meta in _FILENAME_RULES:
        if re.search(pattern, fname_lower):
            result = dict(meta)
            result["source_weight"] = _SOURCE_WEIGHTS.get(result["doc_source"], 0.5)
            return result
    return dict(_DEFAULT_META)


def _get_mtime(filepath: str) -> str:
    """Return ISO-8601 date of file modification."""
    ts = os.path.getmtime(filepath)
    return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")


def _extract_title(filepath: str) -> str:
    """Try to extract the document title from a # SOURCE: line."""
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("# SOURCE:") or line.startswith("# "):
                    return line.lstrip("# ").strip()
                if line and not line.startswith("---"):
                    return line[:120]
    except OSError:
        pass
    return ""


def build_manifest() -> dict:
    manifest = {}
    total = 0

    for module, dirpath in {
        "millennium":    os.path.join(DATA_DIR, "millennium"),
        "powerchart":    os.path.join(DATA_DIR, "powerchart"),
        "revenue_cycle": os.path.join(DATA_DIR, "revenue_cycle"),
        "fhir":          os.path.join(DATA_DIR, "fhir"),
        "clinical":      os.path.join(DATA_DIR, "clinical"),
    }.items():
        if not os.path.isdir(dirpath):
            continue

        for fname in sorted(os.listdir(dirpath)):
            if not (fname.endswith(".txt") or fname.endswith(".md")):
                continue
            if fname.lower() in ("readme.md",):
                continue

            filepath = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(filepath, os.path.dirname(DATA_DIR)).replace("\\", "/")

            meta = _classify_file(filepath, fname)
            meta["last_updated"] = _get_mtime(filepath)
            meta["title"] = _extract_title(filepath)
            meta["module"] = module

            manifest[rel_path] = meta
            total += 1
            print(f"  {rel_path:<60}  {meta['doc_source']:<18} {meta['priority_tier']}")

    return manifest


def _apply_overrides(manifest: dict) -> int:
    """Merge per-file overrides from doc_manifest_overrides.json (if present).

    The overrides file lets Phase 2+ additions specify metadata (e.g.
    source_quality=archival_secondary, priority_tier=should) that the filename-
    based classifier can't infer. Only listed keys are overwritten; other fields
    from the auto-classification are preserved. Returns the number of files
    patched.
    """
    if not os.path.isfile(OVERRIDES_PATH):
        return 0
    with open(OVERRIDES_PATH, encoding="utf-8") as f:
        overrides = json.load(f)
    n = 0
    for rel_path, patch in overrides.items():
        if rel_path in manifest:
            manifest[rel_path].update(patch)
            n += 1
        else:
            print(f"  [WARN] override key not in manifest: {rel_path}")
    return n


def main():
    print("=" * 60)
    print("Cerna — Document Tagging")
    print("=" * 60)
    print(f"\nScanning {DATA_DIR}…\n")

    manifest = build_manifest()

    patched = _apply_overrides(manifest)
    if patched:
        print(f"\n  Applied {patched} override(s) from {os.path.basename(OVERRIDES_PATH)}")

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"Manifest written: {MANIFEST_PATH}")
    print(f"Total documents : {len(manifest)}")

    # Summary by priority_tier
    from collections import Counter
    tiers = Counter(v["priority_tier"] for v in manifest.values())
    types = Counter(v["doc_type"] for v in manifest.values())
    print(f"\nPriority tiers: {dict(tiers)}")
    print(f"Doc types     : {dict(types)}")
    print("\nRun `python ingest.py` to rebuild ChromaDB with enriched metadata.")


if __name__ == "__main__":
    main()
