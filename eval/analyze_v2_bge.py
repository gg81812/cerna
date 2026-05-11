"""
eval/analyze_v2_bge.py — Phase 2 BGE eval breakdown with rate-limit split.

The BGE re-run hit Groq's 8B TPD wall mid-stream (anticipated by the cleanup
prompt). This analyzer:
  1. Identifies rate-limited queries (confidence=='error' or evidence of 429
     in the response excerpt) and splits the eval into a CLEAN subset and a
     RATE-LIMITED subset.
  2. Computes the headline on CLEAN queries only (the honest BGE measurement).
  3. Reports the rate-limited subset count separately so it can be re-run on
     a fresh-quota day.

Run:
    python eval/analyze_v2_bge.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

EVAL_DIR = Path(__file__).parent
RESULTS_BGE = EVAL_DIR / "hospital_eval_v2_results_bge.jsonl"
RESULTS_MINILM = EVAL_DIR / "hospital_eval_v2_results.jsonl"

NEW_25_IDS = (
    [f"hs-it-{i:03d}" for i in range(9, 18)]
    + [f"hs-nurse-{i:03d}" for i in range(16, 23)]
    + [f"hs-physician-{i:03d}" for i in range(11, 15)]
    + [f"hs-clerk-{i:03d}" for i in range(13, 18)]
)


def _is_rate_limited(row: dict) -> bool:
    """A query is rate-limit-affected if any of:
      - confidence == 'error'
      - response excerpt explicitly mentions 429 / rate-limit
      - retrieval surfaced solid chunks (top_chunk_score >= 0.55) BUT confidence=='low'
        AND keyword_hit_rate == 0 — signature of the 70B answer call returning an
        empty/fallback response after exhausting 429 retries while retrieval
        worked normally."""
    conf = row.get("confidence", "")
    if conf == "error":
        return True
    excerpt = (row.get("response_excerpt") or "").lower()
    if "rate_limit" in excerpt or "rate limit" in excerpt or "429" in excerpt:
        return True
    top = row.get("top_chunk_score", 0) or 0
    khr = row.get("keyword_hit_rate", 0) or 0
    if top >= 0.55 and conf == "low" and khr == 0 and not row.get("passed"):
        return True
    return False


def _pct(n: int, d: int) -> str:
    return f"{n}/{d} ({round(n/d*100, 1)}%)" if d else f"{n}/0 (n/a)"


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    rows = _load(RESULTS_BGE)
    if not rows:
        print(f"ERROR: {RESULTS_BGE} not found.")
        sys.exit(1)

    n = len(rows)
    rate_limited = [r for r in rows if _is_rate_limited(r)]
    clean = [r for r in rows if not _is_rate_limited(r)]

    print("=" * 76)
    print("Cerna - Phase 2 BGE-verified eval (with rate-limit split)")
    print(f"Source: {RESULTS_BGE.name}")
    print("=" * 76)

    print(f"\nTotal queries        : {n}")
    print(f"Rate-limited (8B TPD): {len(rate_limited)}")
    print(f"Clean (BGE measured) : {len(clean)}")

    # ---------- Topline (raw, all 80) ----------
    print("\n" + "-" * 30 + " RAW (all 80, includes rate-limited) " + "-" * 9)
    passed = sum(1 for r in rows if r["passed"])
    bad = sum(1 for r in rows if r["fail_mode"] == "bad")
    print(f"  Pass rate    : {_pct(passed, n)}")
    print(f"  Bad failures : {bad}")

    # ---------- Clean (BGE-only) ----------
    print("\n" + "-" * 30 + " CLEAN (rate-limit excluded - HONEST BGE) " + "-" * 4)
    if clean:
        c_pass = sum(1 for r in clean if r["passed"])
        c_bad = sum(1 for r in clean if r["fail_mode"] == "bad")
        print(f"  Pass rate    : {_pct(c_pass, len(clean))}")
        print(f"  Bad failures : {c_bad}")

        # Per-persona on clean
        print("\n  By persona (clean):")
        by_p: dict[str, list[dict]] = defaultdict(list)
        for r in clean:
            by_p[r["persona"]].append(r)
        for p in ("nurse", "clerk", "physician", "it", "cross"):
            sub = by_p.get(p, [])
            if sub:
                pp = sum(1 for r in sub if r["passed"])
                print(f"    {p:<12}: {_pct(pp, len(sub))}")

        # Per-module on clean
        print("\n  By module (clean):")
        by_m: dict[str, list[dict]] = defaultdict(list)
        for r in clean:
            by_m[r.get("expected_module", "UNKNOWN")].append(r)
        for m in sorted(by_m):
            sub = by_m[m]
            mp = sum(1 for r in sub if r["passed"])
            print(f"    {m:<14}: {_pct(mp, len(sub))}")

        # New vs original (clean)
        clean_new = [r for r in clean if r["id"] in NEW_25_IDS]
        clean_orig = [r for r in clean if r["id"] not in NEW_25_IDS]
        new_pass = sum(1 for r in clean_new if r["passed"])
        orig_pass = sum(1 for r in clean_orig if r["passed"])
        print("\n  New vs Original (clean only):")
        print(f"    New 25 (clean subset)   : {_pct(new_pass, len(clean_new))}")
        print(f"    Original 55 (clean)     : {_pct(orig_pass, len(clean_orig))}")
        print(f"    Phase 1 BGE baseline (orig 55): 36/55 (65.5%)")

    # ---------- Rate-limited diagnostic ----------
    print("\n" + "-" * 30 + " RATE-LIMITED (re-run needed)  " + "-" * 16)
    if rate_limited:
        print(f"  Affected query IDs:")
        for r in rate_limited:
            print(f"    {r['id']:<22} expected_module={r.get('expected_module','?'):<14} confidence={r.get('confidence','?')}")
    else:
        print("  None.")

    # ---------- Compare to MiniLM ----------
    mini_rows = _load(RESULTS_MINILM)
    if mini_rows and clean:
        mini_pass = sum(1 for r in mini_rows if r["passed"])
        clean_pass = sum(1 for r in clean if r["passed"])
        print("\n" + "-" * 30 + " BGE vs MiniLM " + "-" * 30)
        print(f"  MiniLM (Phase 2): {_pct(mini_pass, len(mini_rows))}")
        print(f"  BGE clean       : {_pct(clean_pass, len(clean))}")

        # New 25 head-to-head
        mini_new = [r for r in mini_rows if r["id"] in NEW_25_IDS]
        mini_new_pass = sum(1 for r in mini_new if r["passed"])
        clean_new = [r for r in clean if r["id"] in NEW_25_IDS]
        clean_new_pass = sum(1 for r in clean_new if r["passed"])
        print(f"  New 25 (MiniLM)        : {_pct(mini_new_pass, len(mini_new))}")
        print(f"  New 25 (BGE clean)     : {_pct(clean_new_pass, len(clean_new))}")

        # Original 55 head-to-head
        mini_orig = [r for r in mini_rows if r["id"] not in NEW_25_IDS]
        mini_orig_pass = sum(1 for r in mini_orig if r["passed"])
        clean_orig = [r for r in clean if r["id"] not in NEW_25_IDS]
        clean_orig_pass = sum(1 for r in clean_orig if r["passed"])
        print(f"  Original 55 (MiniLM)   : {_pct(mini_orig_pass, len(mini_orig))}")
        print(f"  Original 55 (BGE clean): {_pct(clean_orig_pass, len(clean_orig))}")
        print(f"  Phase 1 BGE baseline   : 36/55 (65.5%)")

    print("\n" + "=" * 76)


if __name__ == "__main__":
    main()
