"""
eval/rerun_specific_ids.py — Re-run specific v2 query ids through the full
pipeline (orchestrator + 70B answer) and append results to a target JSONL.

Used to validate behavior changes (e.g. clarify-heuristic update) on a
small slice without spending tokens on the full 80-query eval.

Usage:
    python eval/rerun_specific_ids.py --ids hs-clerk-013,hs-it-014 --output eval/probe_clarify_fix.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator import Orchestrator
from eval.run_hospital_eval import evaluate_single, load_hospital_set


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ids", required=True,
                   help="Comma-separated list of v2 query ids to re-run")
    p.add_argument("--output", required=True,
                   help="Output JSONL path (overwritten on each run)")
    p.add_argument("--delay", type=float, default=4.0)
    p.add_argument("--marker", type=str, default="probe_run",
                   help="String marker to add to each row (e.g. 'clarify_fix_probe')")
    args = p.parse_args()

    ids = [s.strip() for s in args.ids.split(",") if s.strip()]
    queries = load_hospital_set(persona_filter=None, version="v2")
    by_id = {q["id"]: q for q in queries}
    missing = [i for i in ids if i not in by_id]
    if missing:
        print(f"ERROR: ids not found in v2: {missing}")
        sys.exit(1)

    print(f"Re-running {len(ids)} queries; marker={args.marker}")
    orch = Orchestrator()

    out_rows = []
    for i, qid in enumerate(ids, 1):
        item = by_id[qid]
        print(
            f"[{i:02d}/{len(ids)}] {qid:<22} {item['question'][:55]}...",
            end=" ",
            flush=True,
        )
        result = evaluate_single(orch, item)
        result[args.marker] = True
        out_rows.append(result)
        status = "PASS" if result["passed"] else f"FAIL({result['fail_mode']})"
        print(
            f"{status:<12} khr={result['keyword_hit_rate']:.0%}  "
            f"conf={result['confidence']}  behav={result['actual_behavior']}  "
            f"{result['latency_ms']}ms"
        )
        if args.delay > 0 and i < len(ids):
            time.sleep(args.delay)

    out_path = Path(args.output)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r) + "\n")

    passed = sum(1 for r in out_rows if r["passed"])
    print()
    print("=" * 64)
    print(f"Done. {passed}/{len(out_rows)} pass.  Written to {out_path}")
    # Compare to expected_behavior outcomes
    for r in out_rows:
        marker = "PASS" if r["passed"] else "FAIL"
        print(
            f"  {r['id']:<22} expected={r['expected_behavior']:<8} "
            f"actual={r['actual_behavior']:<8} {marker}"
        )


if __name__ == "__main__":
    main()
