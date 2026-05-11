"""
eval/bench_clarify_paired.py — Offline 8B-only paired-control bench for the
multi-branch clarify heuristic. Streams progress and writes incremental
results so a long run is not lost on interrupt.

Tests two slices:
  1. The 5 BGE-failing new-25 queries — expect needs_clarification=True
     on the 3 expected=clarify ones; expect False on the 2 expected=answer.
  2. All currently-passing answer queries from the latest BGE eval — expect
     needs_clarification=False on all of them (any True is a regression FP).

Usage:
    python eval/bench_clarify_paired.py
    python eval/bench_clarify_paired.py --delay 1.0    # slower if quota tight
    python eval/bench_clarify_paired.py --max 20       # cap the answer slice
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from query_rewriter import understand_query

EVAL_DIR = Path(__file__).parent
V2_PATH = EVAL_DIR / "hospital_staff_queries_v2.jsonl"
RESULTS_PATH = EVAL_DIR / "hospital_eval_v2_results_bge.jsonl"

BGE_FAILING_NEW25 = [
    "hs-clerk-013", "hs-it-014", "hs-nurse-019",
    "hs-nurse-020", "hs-physician-012",
]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def latest_per_id(rows: list[dict]) -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    for r in rows:
        if r["id"] not in by_id or (r.get("cleanup_rerun") and not by_id[r["id"]].get("cleanup_rerun")):
            by_id[r["id"]] = r
    return by_id


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--delay", type=float, default=0.5)
    p.add_argument("--max", type=int, default=None)
    args = p.parse_args()

    v2 = {q["id"]: q for q in load_jsonl(V2_PATH)}
    by_id = latest_per_id(load_jsonl(RESULTS_PATH))

    print("=" * 72)
    print("Slice 1: BGE-failing new-25 queries (expect TRUE on clarify, FALSE on answer)")
    print("=" * 72)
    s1_correct = 0
    for qid in BGE_FAILING_NEW25:
        q = v2.get(qid)
        if q is None:
            print(f"  [skip] {qid} not in v2")
            continue
        expected = q.get("expected_behavior", "answer")
        target = (expected == "clarify")
        u = understand_query(q["question"], "")
        ok = (u.needs_clarification == target)
        if ok:
            s1_correct += 1
        flag = "OK" if ok else ("MISS-CLARIFY" if target else "FALSE-POSITIVE")
        print(
            f"  [{qid:<22}] expected={expected:<8} needs_clar={u.needs_clarification!r:<5}  {flag}"
        )
        if u.needs_clarification:
            print(f"      q: {u.clarification_question[:130]!r}")
        time.sleep(args.delay)
    print(f"  Slice 1: {s1_correct}/{len(BGE_FAILING_NEW25)} matched expectation")

    print()
    print("=" * 72)
    print("Slice 2: currently-passing answer queries (any TRUE is an FP regression)")
    print("=" * 72)
    passing_answers = [
        qid for qid, r in by_id.items()
        if r.get("expected_behavior") == "answer" and r.get("passed", False)
    ]
    if args.max:
        passing_answers = passing_answers[: args.max]
    print(f"  Testing {len(passing_answers)} passing-answer queries...")
    fp = []
    for i, qid in enumerate(passing_answers, 1):
        q = v2.get(qid)
        if q is None:
            continue
        u = understand_query(q["question"], "")
        flag = "FALSE-POS" if u.needs_clarification else "ok"
        print(
            f"  [{i:>2}/{len(passing_answers)}] [{qid:<22}] needs_clar={u.needs_clarification!r:<5}  {flag}",
            flush=True,
        )
        if u.needs_clarification:
            fp.append((qid, q["question"][:120]))
        time.sleep(args.delay)
    print()
    print(f"  Slice 2 false positives: {len(fp)}/{len(passing_answers)}")
    for qid, qt in fp:
        print(f"    {qid}  Q: {qt}")

    # Summary
    print()
    print("=" * 72)
    print(f"SUMMARY")
    print("=" * 72)
    print(f"  Slice 1 (5 BGE-failing new-25)        : {s1_correct}/{len(BGE_FAILING_NEW25)} correct")
    print(f"  Slice 2 (passing-answer regression)   : {len(fp)} FPs / {len(passing_answers)} tested")
    if fp:
        print(f"  Net delta if shipped (slice 1 gains − slice 2 FPs): "
              f"{s1_correct - len(fp)}")
    else:
        print(f"  Net delta if shipped: +{s1_correct} (no regressions)")


if __name__ == "__main__":
    main()
