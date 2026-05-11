"""
eval/analyze_v2_results.py — Compute Phase 2 v2 eval breakdown.

Reads eval/hospital_eval_v2_results.jsonl (80 queries) and produces:
- Overall pass rate
- Per-module pass rate
- Per-persona pass rate
- New-25 vs Original-55 pass rates (regression check)
- Latency stats
- Bad-failure count

The "new 25" are identified by id ranges:
  hs-it-009..hs-it-017          (9 IT queries — FHIR + Millennium expansion)
  hs-nurse-016..hs-nurse-022    (7 nurse queries)
  hs-physician-011..hs-physician-014  (4 physician queries)
  hs-clerk-013..hs-clerk-017    (5 clerk queries)

Run:
    python eval/analyze_v2_results.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

EVAL_DIR = Path(__file__).parent
RESULTS_V2 = EVAL_DIR / "hospital_eval_v2_results.jsonl"

NEW_25_IDS = (
    [f"hs-it-{i:03d}" for i in range(9, 18)]
    + [f"hs-nurse-{i:03d}" for i in range(16, 23)]
    + [f"hs-physician-{i:03d}" for i in range(11, 15)]
    + [f"hs-clerk-{i:03d}" for i in range(13, 18)]
)


def _pct(n: int, d: int) -> str:
    return f"{n}/{d} ({round(n/d*100, 1)}%)" if d else f"{n}/0 (n/a)"


def main():
    if not RESULTS_V2.exists():
        print(f"ERROR: {RESULTS_V2} not found. Run `python eval/run_hospital_eval.py --version v2` first.")
        sys.exit(1)

    rows: list[dict] = []
    with open(RESULTS_V2, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    total = len(rows)
    passed = sum(1 for r in rows if r["passed"])
    bad_fails = sum(1 for r in rows if r["fail_mode"] == "bad")
    honest_fails = sum(1 for r in rows if r["fail_mode"] == "honest")
    cls_correct = sum(1 for r in rows if r["classification_correct"])
    behav_match = sum(1 for r in rows if r["behavior_match"])
    latencies = [r["latency_ms"] for r in rows if r.get("latency_ms", 0) > 0]
    avg_ms = round(sum(latencies) / len(latencies)) if latencies else 0
    p95_ms = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    print("=" * 72)
    print("Cerna — Phase 2 Hospital Eval v2 Breakdown")
    print(f"Source: {RESULTS_V2.name}")
    print("=" * 72)
    print(f"\n[OVERALL]  Pass: {_pct(passed, total)}")
    print(f"           Classification correct : {_pct(cls_correct, total)}")
    print(f"           Behavior match         : {_pct(behav_match, total)}")
    print(f"           Honest fails           : {honest_fails}")
    print(f"           Bad fails              : {bad_fails}  (target: 0)")
    print(f"           Latency avg / p95      : {avg_ms} ms / {p95_ms} ms")

    # Per persona
    print("\n[BY PERSONA]")
    by_persona: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_persona[r["persona"]].append(r)
    for persona in ("nurse", "clerk", "physician", "it", "cross"):
        subset = by_persona.get(persona, [])
        if subset:
            n = len(subset)
            p = sum(1 for r in subset if r["passed"])
            print(f"  {persona:<12}: {_pct(p, n)}")

    # Per module (uses expected_module field)
    print("\n[BY MODULE]")
    by_mod: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_mod[r.get("expected_module", "UNKNOWN")].append(r)
    for mod in sorted(by_mod):
        subset = by_mod[mod]
        n = len(subset)
        p = sum(1 for r in subset if r["passed"])
        print(f"  {mod:<14}: {_pct(p, n)}")

    # New-25 vs Original-55
    new_rows = [r for r in rows if r["id"] in NEW_25_IDS]
    orig_rows = [r for r in rows if r["id"] not in NEW_25_IDS]
    new_pass = sum(1 for r in new_rows if r["passed"])
    orig_pass = sum(1 for r in orig_rows if r["passed"])
    print("\n[NEW vs ORIGINAL]  (regression check)")
    print(f"  New 25 queries (FHIR/Millennium/PowerChart/RCM/Clinical exp.): {_pct(new_pass, len(new_rows))}")
    print(f"  Original 55 queries                                          : {_pct(orig_pass, len(orig_rows))}")
    print(f"  Phase 1 corrected baseline on original 55                    : 36/55 (65.5%)")
    if len(orig_rows) == 55:
        delta = orig_pass - 36
        sign = "+" if delta >= 0 else ""
        print(f"  Delta vs Phase 1 baseline                                        : {sign}{delta} ({sign}{round(delta/55*100,1)}pp)")

    # New-25 broken down by module — covers which module the KB expansion most helped
    print("\n[NEW 25 BY MODULE]")
    new_by_mod: dict[str, list[dict]] = defaultdict(list)
    for r in new_rows:
        new_by_mod[r.get("expected_module", "UNKNOWN")].append(r)
    for mod in sorted(new_by_mod):
        subset = new_by_mod[mod]
        n = len(subset)
        p = sum(1 for r in subset if r["passed"])
        print(f"  {mod:<14}: {_pct(p, n)}")

    # Failures listing
    print("\n[FAILURES]")
    fails = [r for r in rows if not r["passed"]]
    if not fails:
        print("  None.")
    else:
        for r in fails:
            tag = "[NEW]" if r["id"] in NEW_25_IDS else "[ORIG]"
            print(f"  {tag} {r['id']:<22} {r['fail_mode'].upper():<8} khr={r['keyword_hit_rate']:.0%}  conf={r['confidence']}  behav={r['actual_behavior']}")

    print("\n" + "=" * 72)


if __name__ == "__main__":
    main()
