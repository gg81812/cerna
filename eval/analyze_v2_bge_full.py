"""
eval/analyze_v2_bge_full.py — Recompute Phase 2 BGE headlines on the FULL v2 set.

Reads `eval/hospital_eval_v2_results_bge.jsonl`, which after the cleanup re-run
contains the original 80 rows plus 26 cleanup_rerun rows. For any duplicated
id, the cleanup_rerun row wins. Reports:
  - Overall on full 80 (BGE)
  - Original 55 on BGE
  - New 25 on BGE
  - Per-module pass rate on the new 25 (vs MiniLM 92% reference)
  - Per-persona pass rate on full 80
  - Bad-failure count (re-confirm 0)
  - Latency avg / p95 (full 80, post-rerun, post-rate-limit)
  - Any rows that came back STILL rate-limited (note honestly)
"""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

EVAL_DIR = Path(__file__).parent
RESULTS_FILE = EVAL_DIR / "hospital_eval_v2_results_bge.jsonl"
V1_QUERIES = EVAL_DIR / "hospital_staff_queries.jsonl"
V2_QUERIES = EVAL_DIR / "hospital_staff_queries_v2.jsonl"
RL_MARKER = "temporarily unable to generate a detailed response"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def latest_per_id(rows: list[dict]) -> list[dict]:
    """Cleanup_rerun rows win over original rows for the same id."""
    by_id: dict[str, dict] = {}
    for r in rows:
        i = r["id"]
        if i not in by_id:
            by_id[i] = r
        else:
            if r.get("cleanup_rerun") and not by_id[i].get("cleanup_rerun"):
                by_id[i] = r
    return list(by_id.values())


def fmt_pct(num: int, den: int) -> str:
    if den == 0:
        return "0/0 (n/a)"
    return f"{num}/{den} ({num/den*100:.1f}%)"


def main():
    rows = load_jsonl(RESULTS_FILE)
    raw_total = len(rows)
    rerun_rows = [r for r in rows if r.get("cleanup_rerun")]
    rows = latest_per_id(rows)

    v1 = {q["id"] for q in load_jsonl(V1_QUERIES)}
    v2 = [q["id"] for q in load_jsonl(V2_QUERIES)]
    new_ids = set(v2) - v1
    orig_ids = v1 & set(v2)

    rl_remaining = [r for r in rows if RL_MARKER in r.get("response_excerpt", "").lower()]

    print("=" * 72)
    print(f"Phase 2 BGE — FULL v2 measurement (post cleanup re-run)")
    print(f"Source: {RESULTS_FILE.name}  (raw rows={raw_total}, dedup unique={len(rows)})")
    print(f"Cleanup-rerun rows: {len(rerun_rows)}")
    print("=" * 72)

    # Headline tables ----------------------------------------------------
    overall_pass = sum(1 for r in rows if r["passed"])
    overall_n    = len(rows)
    print(f"\nOVERALL (full 80 BGE)         : {fmt_pct(overall_pass, overall_n)}")

    orig_rows = [r for r in rows if r["id"] in orig_ids]
    orig_pass = sum(1 for r in orig_rows if r["passed"])
    print(f"Original 55 (BGE)             : {fmt_pct(orig_pass, len(orig_rows))}")

    new_rows = [r for r in rows if r["id"] in new_ids]
    new_pass = sum(1 for r in new_rows if r["passed"])
    print(f"New 25 (BGE)                  : {fmt_pct(new_pass, len(new_rows))}")
    print(f"  — MiniLM reference for new 25 was 23/25 (92.0%)")

    print(f"\nStill rate-limited after rerun: {len(rl_remaining)}")
    if rl_remaining:
        for r in rl_remaining:
            print(f"  - {r['id']}  cleanup_rerun={r.get('cleanup_rerun', False)}")

    # Bad-failure count --------------------------------------------------
    bad = sum(1 for r in rows if r["fail_mode"] == "bad")
    honest = sum(1 for r in rows if r["fail_mode"] == "honest")
    print(f"\nBad failures                  : {bad}")
    print(f"Honest failures               : {honest}")

    # Per-module on new-25 ----------------------------------------------
    print(f"\n-- Per-module on the new 25 (vs MiniLM 92% headline) --------------------")
    by_mod: dict[str, list[dict]] = defaultdict(list)
    for r in new_rows:
        by_mod[r["module"]].append(r)
    for mod, items in sorted(by_mod.items()):
        p = sum(1 for r in items if r["passed"])
        print(f"  {mod:<14} : {fmt_pct(p, len(items))}")

    # Per-persona on full 80 --------------------------------------------
    print(f"\n-- Per-persona on full 80 (BGE) ----------------------------------------")
    by_per: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_per[r["persona"]].append(r)
    for per in ("nurse", "clerk", "physician", "it", "cross"):
        items = by_per.get(per, [])
        p = sum(1 for r in items if r["passed"])
        print(f"  {per:<10} : {fmt_pct(p, len(items))}")

    # Per-module on full 80 ---------------------------------------------
    print(f"\n-- Per-module on full 80 (BGE) -----------------------------------------")
    by_mod_full: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_mod_full[r["module"]].append(r)
    for mod, items in sorted(by_mod_full.items()):
        p = sum(1 for r in items if r["passed"])
        print(f"  {mod:<14} : {fmt_pct(p, len(items))}")

    # Latency -----------------------------------------------------------
    lats = [r["latency_ms"] for r in rows if r.get("latency_ms", 0) > 0]
    if lats:
        avg = int(statistics.mean(lats))
        p50 = int(statistics.median(lats))
        s = sorted(lats)
        p95 = s[int(len(s) * 0.95)]
        p99 = s[min(len(s) - 1, int(len(s) * 0.99))]
        print(f"\n-- Latency (end-to-end, full 80 BGE merged) ----------------------------")
        print(f"  avg={avg}ms  p50={p50}ms  p95={p95}ms  p99={p99}ms  max={max(lats)}ms")

    # Confidence/behavior cross-tab -------------------------------------
    print(f"\n-- Confidence distribution --------------------------------------------")
    for k, v in Counter(r["confidence"] for r in rows).items():
        print(f"  {k:<8} : {v}")
    print(f"\n-- Actual behavior distribution ---------------------------------------")
    for k, v in Counter(r["actual_behavior"] for r in rows).items():
        print(f"  {k:<10} : {v}")


if __name__ == "__main__":
    main()
