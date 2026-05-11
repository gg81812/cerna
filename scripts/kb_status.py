"""
scripts/kb_status.py — Report the current state of the Cerna knowledge base.

Usage (from project root):
    python scripts/kb_status.py

Exit codes:
    0 — all MUST Gate 1 documents are populated with real content
    1 — one or more MUST Gate 1 placeholders remain (CI gate check)
"""

import os
import sys
from pathlib import Path

PLACEHOLDER_MARKER = "PLACEHOLDER — MANUAL DOWNLOAD REQUIRED"

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

MODULES = ["fhir", "millennium", "powerchart", "revenue_cycle", "clinical"]

MODULE_LABELS = {
    "fhir": "FHIR & Integrations",
    "millennium": "Millennium Platform",
    "powerchart": "PowerChart",
    "revenue_cycle": "Revenue Cycle",
    "clinical": "Clinical Workflows",
}


def is_placeholder(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return PLACEHOLDER_MARKER in text
    except OSError:
        return False


def get_priority(path: Path) -> str:
    """Extract priority from a placeholder file. Returns '' for real docs."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.strip().startswith("Priority:"):
                val = line.split(":", 1)[1].strip()
                return val  # e.g. "MUST" or "SHOULD"
    except OSError:
        pass
    return ""


def get_gate(path: Path) -> str:
    """Extract gate from a placeholder file."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.strip().startswith("Gate:"):
                val = line.split(":", 1)[1].strip()
                return val  # e.g. "Gate 1 (Week 2)"
    except OSError:
        pass
    return ""


def scan_module(module: str):
    folder = DATA_DIR / module
    files = []
    if not folder.exists():
        return files
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix in (".md", ".txt") and p.name != "README.md":
            size_kb = p.stat().st_size / 1024
            placeholder = is_placeholder(p)
            priority = get_priority(p) if placeholder else ""
            gate = get_gate(p) if placeholder else ""
            files.append({
                "name": p.name,
                "size_kb": size_kb,
                "placeholder": placeholder,
                "priority": priority,
                "gate": gate,
            })
    return files


def main():
    print("=" * 70)
    print("Cerna Knowledge Base Status Report")
    print("=" * 70)

    total_must = 0
    total_must_populated = 0
    blocking_files = []

    summary_rows = []

    for module in MODULES:
        label = MODULE_LABELS[module]
        files = scan_module(module)

        real_docs = [f for f in files if not f["placeholder"]]
        placeholders = [f for f in files if f["placeholder"]]
        total_kb = sum(f["size_kb"] for f in files)

        summary_rows.append({
            "module": label,
            "total": len(files),
            "real": len(real_docs),
            "placeholders": len(placeholders),
            "kb": total_kb,
        })

        print(f"\n{'-'*70}")
        print(f"  Module: {label}")
        print(f"{'-'*70}")
        print(f"  {'Filename':<52} {'Size KB':>7}  {'Type'}")
        print(f"  {'-'*52}  {'-'*7}  {'-'*15}")

        for f in files:
            ftype = "PLACEHOLDER" if f["placeholder"] else "real doc"
            print(f"  {f['name']:<52} {f['size_kb']:>7.1f}  {ftype}")

        if not files:
            print("  (no documents found)")

        # Gate 1 MUST check
        must_g1 = [f for f in placeholders if f["priority"] == "MUST" and "Gate 1" in f["gate"]]
        for f in must_g1:
            total_must += 1
            blocking_files.append((label, f["name"]))
        total_must += 0  # already counted above
        total_must_populated += len([
            f for f in real_docs
        ])  # real docs are by definition populated

        if must_g1:
            print(f"\n  [BLOCKING] {len(must_g1)} MUST Gate 1 placeholder(s) in this module:")
            for f in must_g1:
                print(f"    !! {f['name']}")

        if not real_docs and files:
            print(
                f"\n  [ERROR] Module {label}: no real documents found — "
                f"Cerna cannot answer {label} questions until documents are added"
            )

    # ── Summary table ─────────────────────────────────────────────────────────
    print(f"\n\n{'='*70}")
    print("SUMMARY TABLE")
    print(f"{'='*70}")
    header = f"  {'Module':<28} {'Total':>5}  {'Real':>5}  {'Placeholders':>12}  {'Est. KB':>8}"
    print(header)
    print(f"  {'-'*28}  {'-'*5}  {'-'*5}  {'-'*12}  {'-'*8}")
    for row in summary_rows:
        print(
            f"  {row['module']:<28} {row['total']:>5}  {row['real']:>5}  "
            f"{row['placeholders']:>12}  {row['kb']:>8.1f}"
        )

    # ── Gate 1 readiness ──────────────────────────────────────────────────────
    # Count all MUST Gate 1 across all modules
    all_must_gate1 = []
    for module in MODULES:
        label = MODULE_LABELS[module]
        files = scan_module(module)
        for f in files:
            if f["placeholder"] and f["priority"] == "MUST" and "Gate 1" in f["gate"]:
                all_must_gate1.append((label, f["name"]))

    # Total MUST Gate 1 defined (placeholders + real)
    # We derive total expected from the README placeholders only — anything
    # that was a placeholder and is now real was counted as real above.
    # For simplicity: total_must_defined = files that are MUST Gate 1 placeholders
    # + real docs that were supposed to be MUST Gate 1 (we can't distinguish after
    # population). So we report: blocking placeholders remaining.
    blocking_count = len(all_must_gate1)

    # Estimate total MUST Gate 1 defined in the spec
    MUST_GATE1_TOTAL = {
        "millennium": 3,   # domain-admin, ccl-reference, release-notes
        "powerchart": 4,   # user-guide, patient-list, cpoe, powernote
        "revenue_cycle": 5, # overview-map, charge-capture, charge-review, claims, patient-acct
        "clinical": 5,     # emar, bcma, nursing-assess, med-admin, patient-safety
        "fhir": 0,         # all FHIR docs are public/scraped
    }
    total_expected = sum(MUST_GATE1_TOTAL.values())
    populated = total_expected - blocking_count

    print(f"\n{'='*70}")
    print(f"GATE 1 READINESS: {populated}/{total_expected} MUST documents populated")
    print(f"{'='*70}")

    if all_must_gate1:
        print(f"\n  Blocking MUST Gate 1 placeholders ({blocking_count}):")
        for module_label, fname in all_must_gate1:
            print(f"    [{module_label}] {fname}")
        print(
            "\n  ACTION: Download these documents from uCern (cernercentral.com)"
            "\n  and replace the placeholder files before running ingest.py"
        )
        sys.exit(1)
    else:
        print("\n  All MUST Gate 1 documents are populated. Ready to run ingest.py")
        sys.exit(0)


if __name__ == "__main__":
    main()
