"""
eval/reclassify_hospital_eval.py — Reclassify hospital_eval_results.jsonl with
the corrected behavior detector (the 2026-05-06 keyword bug fix).

No Groq usage — operates on the captured `response_excerpt` field of each
record. The original eval did not preserve full response text, so this
reclassification is performed on the 400-character excerpt. That is a
limitation: a `clarify`-shape question that appears past character 400 will
not be detected here. In practice the truncated excerpt covers the start of
the **DIRECT ANSWER** block, where genuine clarification questions tend to
appear; mid-response clarifications past 400 chars are uncommon.

Usage:
    python eval/reclassify_hospital_eval.py
    python eval/reclassify_hospital_eval.py --input eval/hospital_eval_results.jsonl
                                            --output eval/hospital_eval_results_corrected.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.run_hospital_eval import (
    _detect_behavior,
    _classify_fail_mode,
)

DEFAULT_INPUT  = Path(__file__).parent / "hospital_eval_results.jsonl"
DEFAULT_OUTPUT = Path(__file__).parent / "hospital_eval_results_corrected.jsonl"


def reclassify(record: dict) -> dict:
    """Apply the corrected detector to one record's response_excerpt and
    re-derive behavior_match / passed / fail_mode."""
    excerpt           = record.get("response_excerpt") or ""
    expected_behavior = record.get("expected_behavior", "answer")
    expected_keywords = []  # not stored; keep keyword_hit_rate from original
    keyword_hit_rate  = record.get("keyword_hit_rate", 0.0)
    confidence        = record.get("confidence", "medium")

    # The original detector also looks at refusal text and did_you_mean
    # state, but those weren't preserved in the JSONL. Fall back to inferring
    # from the original `actual_behavior` field: if the original classified
    # as "refuse", the safest assumption is the refusal path fired.
    original_actual = record.get("actual_behavior")
    refusal_text    = ""
    did_you_mean    = []

    new_actual = _detect_behavior(
        response_text=excerpt,
        refusal=refusal_text,
        did_you_mean=did_you_mean,
        # response_mode wasn't captured; the redirect branch is gated by
        # response_mode=="low" which we approximate via confidence=="low".
        response_mode=("low" if confidence == "low" else "medium"),
        direct_answer=excerpt,
    )

    # If original detector said "refuse" (which requires a non-empty refusal
    # path the JSONL didn't capture), trust the original on this dimension —
    # the corrected detector running on the excerpt alone will under-detect
    # refusals. The keyword-bug fix only affects clarify, not refuse.
    if original_actual == "refuse" and new_actual != "refuse":
        new_actual = "refuse"

    new_match = (new_actual == expected_behavior)

    if expected_behavior in ("clarify", "refuse", "redirect"):
        new_passed = new_match
    else:
        new_passed = (keyword_hit_rate >= 0.6) and new_match

    new_fail_mode = _classify_fail_mode(
        new_passed, expected_behavior, new_actual, confidence, keyword_hit_rate
    )

    out = dict(record)
    out["actual_behavior_original"] = original_actual
    out["actual_behavior"]          = new_actual
    out["behavior_match_original"]  = record.get("behavior_match")
    out["behavior_match"]           = new_match
    out["passed_original"]          = record.get("passed")
    out["passed"]                   = new_passed
    out["fail_mode_original"]       = record.get("fail_mode")
    out["fail_mode"]                = new_fail_mode
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input",  default=str(DEFAULT_INPUT))
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = ap.parse_args()

    records = [json.loads(l) for l in open(args.input, encoding="utf-8")]
    corrected = [reclassify(r) for r in records]

    with open(args.output, "w", encoding="utf-8") as f:
        for r in corrected:
            f.write(json.dumps(r) + "\n")

    # ── Summary ──────────────────────────────────────────────────────────────
    total = len(corrected)
    orig_pass = sum(1 for r in corrected if r["passed_original"])
    new_pass  = sum(1 for r in corrected if r["passed"])

    print("=" * 70)
    print("HOSPITAL-STAFF RECLASSIFICATION — SUMMARY")
    print("=" * 70)
    print(f"Total queries        : {total}")
    print(f"Original pass rate   : {orig_pass}/{total} ({orig_pass/total*100:.1f}%)")
    print(f"Corrected pass rate  : {new_pass}/{total} ({new_pass/total*100:.1f}%)")
    print(f"Delta                : {new_pass - orig_pass:+d}")

    # Fail-to-pass and pass-to-fail flips
    f2p = [r for r in corrected if not r["passed_original"] and r["passed"]]
    p2f = [r for r in corrected if r["passed_original"] and not r["passed"]]
    print(f"\nFail → Pass flips    : {len(f2p)}")
    for r in f2p:
        conf = r.get("confidence", "?")
        print(
            f"  {r['id']:<22} persona={r['persona']:<10} "
            f"orig_actual={r['actual_behavior_original']:<8} "
            f"new_actual={r['actual_behavior']:<8} conf={conf}"
        )
    print(f"\nPass → Fail flips    : {len(p2f)}")
    for r in p2f:
        conf = r.get("confidence", "?")
        print(
            f"  {r['id']:<22} persona={r['persona']:<10} "
            f"orig_actual={r['actual_behavior_original']:<8} "
            f"new_actual={r['actual_behavior']:<8} conf={conf}"
        )

    # Per-persona deltas
    print("\nPer-persona deltas:")
    for persona in ("nurse", "clerk", "physician", "it", "cross"):
        sub = [r for r in corrected if r["persona"] == persona]
        if not sub: continue
        orig_p = sum(1 for r in sub if r["passed_original"])
        new_p  = sum(1 for r in sub if r["passed"])
        n = len(sub)
        print(
            f"  {persona:<10}: {orig_p}/{n} ({orig_p/n*100:.0f}%) → "
            f"{new_p}/{n} ({new_p/n*100:.0f}%)  Δ {new_p-orig_p:+d}"
        )

    # Bad-failure check (the safety-relevant claim)
    bad_orig = sum(1 for r in corrected if r["fail_mode_original"] == "bad")
    bad_new  = sum(1 for r in corrected if r["fail_mode"] == "bad")
    print(f"\nBad failures         : {bad_orig} (original) → {bad_new} (corrected)")

    # High-confidence failures pre/post
    high_orig = [r for r in corrected if not r["passed_original"] and r["confidence"] == "high"]
    high_new  = [r for r in corrected if not r["passed"] and r["confidence"] == "high"]
    print(f"High-conf failures   : {len(high_orig)} (original) → {len(high_new)} (corrected)")
    print("  Residual high-conf failures (corrected):")
    for r in high_new:
        print(
            f"    {r['id']:<22} expected={r['expected_behavior']:<8} "
            f"actual={r['actual_behavior']:<8} khr={r['keyword_hit_rate']:.0%}"
        )

    # Cross-tab of expected vs new actual
    from collections import defaultdict
    ct = defaultdict(lambda: defaultdict(int))
    for r in corrected:
        ct[r["expected_behavior"]][r["actual_behavior"]] += 1
    print("\nExpected × Actual (corrected):")
    for exp in sorted(ct):
        for act in sorted(ct[exp]):
            print(f"  expected={exp:<8} actual={act:<8} count={ct[exp][act]}")

    print(f"\nWrote: {args.output}")


if __name__ == "__main__":
    main()
