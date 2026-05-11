"""
eval/bench_clarify_classifier.py — Bench-test the extended understand_query()
classifier against the 55 captured hospital-eval queries.

Purpose: gate the multi-branch clarify heuristic (Phase 1 Item 2) BEFORE any
pipeline wiring or full hospital-eval re-run. Calls only the 8B classifier
(no retrieval, no 70B) → cheap signal on:
  - recall: how many of the 11 Bin A residual queries get flagged?
  - precision: how many of the 40 currently-passing expected=answer queries
                get flagged as false positives?

Ship-criterion (per Phase 1 prompt):
  - 6+ Bin A cases flagged → ship
  - 0–1 expected=answer queries flagged as needs_clarification → no regression
  - if FP > 1, tighten the prompt and re-run

Usage:
    python eval/bench_clarify_classifier.py
    python eval/bench_clarify_classifier.py --delay 1.5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Load .env so the 8B Groq client can authenticate
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if ENV_PATH.exists():
    import os
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from query_rewriter import understand_query

QUERIES_PATH   = Path(__file__).resolve().parent / "hospital_staff_queries.jsonl"
CORRECTED_PATH = Path(__file__).resolve().parent / "hospital_eval_results_corrected.jsonl"
OUTPUT_PATH    = Path(__file__).resolve().parent / "clarify_bench_results.jsonl"

# The 11 Bin A residual queries (expected=clarify, actual=answer in corrected baseline)
BIN_A_IDS = {
    "hs-nurse-003", "hs-nurse-007", "hs-nurse-012", "hs-nurse-014",
    "hs-clerk-006", "hs-clerk-010", "hs-physician-005",
    "hs-cross-001", "hs-cross-004", "hs-cross-005", "hs-cross-007",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=1.5,
                    help="Seconds between 8B calls (default 1.5)")
    args = ap.parse_args()

    queries = [json.loads(l) for l in QUERIES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    corrected = {
        json.loads(l)["id"]: json.loads(l)
        for l in CORRECTED_PATH.read_text(encoding="utf-8").splitlines() if l.strip()
    }

    print(f"Loaded {len(queries)} queries; {len(corrected)} corrected results")
    print(f"Calling 8B classifier with {args.delay}s spacing...")
    print()

    out = []
    # Incremental write — open in append mode so partial progress is recoverable
    # if the run is killed mid-way. Truncate first so we start clean.
    OUTPUT_PATH.write_text("", encoding="utf-8")
    for i, q in enumerate(queries, 1):
        qid = q["id"]
        question = q["question"]
        cr = corrected.get(qid, {})
        expected_behavior = q.get("expected_behavior", "answer")
        passed_corrected  = cr.get("passed", False)

        t0 = time.time()
        try:
            u = understand_query(question)
            needs    = u.needs_clarification
            cqq      = u.clarification_question
            intent   = u.intent
            error    = ""
        except Exception as exc:
            needs, cqq, intent = False, "", "error"
            error = str(exc)[:200]
        dt = time.time() - t0

        is_bin_a = qid in BIN_A_IDS
        record = {
            "id":                     qid,
            "persona":                q["persona"],
            "expected_behavior":      expected_behavior,
            "passed_corrected":       passed_corrected,
            "is_bin_a":               is_bin_a,
            "intent":                 intent,
            "needs_clarification":    needs,
            "clarification_question": cqq,
            "question":               question,
            "error":                  error,
            "elapsed_s":              round(dt, 2),
        }
        out.append(record)
        # Write incrementally so partial progress is observable from another
        # process (e.g. when polling progress during a long run).
        with OUTPUT_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        flag = "FLAG" if needs else "    "
        marker = "[A]" if is_bin_a else "   "
        print(f"  [{i:02d}/{len(queries)}] {marker} {qid:<22} {flag} intent={intent:<16} {dt:>5.1f}s ", end="", flush=True)
        if needs:
            print(f"-> {cqq[:80]}", flush=True)
        else:
            print(flush=True)

        if args.delay > 0 and i < len(queries):
            time.sleep(args.delay)

    print(f"\nFinal: {OUTPUT_PATH}", flush=True)

    # ── Summary ──────────────────────────────────────────────────────────────
    bin_a_flagged    = [r for r in out if r["is_bin_a"]    and r["needs_clarification"]]
    bin_a_missed     = [r for r in out if r["is_bin_a"]    and not r["needs_clarification"]]
    fp_passing       = [r for r in out
                        if r["needs_clarification"]
                        and not r["is_bin_a"]
                        and r["expected_behavior"] == "answer"
                        and r["passed_corrected"]]
    other_flagged    = [r for r in out
                        if r["needs_clarification"]
                        and not r["is_bin_a"]
                        and not (r["expected_behavior"] == "answer" and r["passed_corrected"])]

    print()
    print("=" * 70)
    print("BENCH-TEST SUMMARY")
    print("=" * 70)
    print(f"Bin A targets recalled       : {len(bin_a_flagged)}/11")
    for r in bin_a_flagged:
        print(f"  + {r['id']:<22} q='{r['clarification_question'][:70]}'")
    if bin_a_missed:
        print(f"Bin A targets MISSED         : {len(bin_a_missed)}/11")
        for r in bin_a_missed:
            print(f"  - {r['id']:<22} (intent={r['intent']})")

    print()
    print(f"FP — currently-passing answer queries flagged: {len(fp_passing)}/40")
    for r in fp_passing:
        print(f"  ! {r['id']:<22} q='{r['clarification_question'][:70]}'")

    print()
    print(f"Other flagged (non-Bin-A, non-FP)            : {len(other_flagged)}")
    for r in other_flagged:
        marker = f"exp={r['expected_behavior']}, passed={r['passed_corrected']}"
        print(f"  ? {r['id']:<22} {marker:<28} q='{r['clarification_question'][:60]}'")

    print()
    print("Ship-criterion check:")
    print(f"  Bin A recall  >= 6  : {'PASS' if len(bin_a_flagged) >= 6 else 'FAIL'}  ({len(bin_a_flagged)})")
    print(f"  FP on passing <= 1  : {'PASS' if len(fp_passing) <= 1 else 'TIGHTEN'}  ({len(fp_passing)})")


if __name__ == "__main__":
    main()
