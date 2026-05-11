"""
eval/profile_latency.py — Per-step latency profiler for the Cerna pipeline.

Runs queries through the pipeline, reads the trace log, and produces a breakdown
of where time is spent. Identifies the top bottlenecks by step and by query.

Usage:
    python eval/profile_latency.py                          # 55 hospital-staff queries
    python eval/profile_latency.py --source golden          # 75 golden-set queries
    python eval/profile_latency.py --source hospital --n 10 # quick sample
    python eval/profile_latency.py --cached                 # warm cache run (2nd pass)

Output: printed summary + logs/latency_profile.jsonl

Target budgets:
  Cached queries:  < 2000 ms total
  Cold queries:    < 5000 ms total
  Refusal paths:   < 1000 ms total
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator import Orchestrator

HOSPITAL_SET = Path(__file__).parent / "hospital_staff_queries.jsonl"
GOLDEN_SET   = Path(__file__).parent / "golden_set.jsonl"
OUTPUT_FILE  = Path(__file__).parent.parent / "logs" / "latency_profile.jsonl"

_TARGET_CACHED_MS  = 2000
_TARGET_COLD_MS    = 5000
_TARGET_REFUSAL_MS = 1000


def load_queries(source: str, n: int | None = None) -> list[dict]:
    path = HOSPITAL_SET if source == "hospital" else GOLDEN_SET
    queries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                queries.append(json.loads(line))
    if n:
        queries = queries[:n]
    return queries


def run_with_trace(orch: Orchestrator, question: str, module_hint: str | None) -> dict:
    t0 = time.monotonic()
    try:
        prepared    = orch.prepare(question, [], module_hint=module_hint)
        cerna_resp  = orch.generate_structured(prepared)
        total_ms    = int((time.monotonic() - t0) * 1000)
        is_refusal  = bool(prepared.refusal)
        confidence  = cerna_resp.confidence
        state       = prepared._state or {}
        trace       = state.get("trace", [])
    except Exception as exc:
        total_ms   = int((time.monotonic() - t0) * 1000)
        is_refusal = False
        confidence = "error"
        trace      = []
        print(f"  ERROR: {exc}")

    return {
        "question":    question[:80],
        "total_ms":    total_ms,
        "is_refusal":  is_refusal,
        "confidence":  confidence,
        "trace":       trace,
    }


def print_latency_report(records: list[dict], cache_hit_set: set[str]) -> None:
    total    = len(records)
    cold     = [r for r in records if r["question"] not in cache_hit_set]
    cached   = [r for r in records if r["question"] in cache_hit_set]
    refusals = [r for r in records if r["is_refusal"]]

    def _stats(items: list[dict]) -> str:
        if not items:
            return "n/a"
        lats = [i["total_ms"] for i in items]
        avg  = int(sum(lats) / len(lats))
        p50  = sorted(lats)[len(lats) // 2]
        p95  = sorted(lats)[int(len(lats) * 0.95)]
        return f"avg={avg}ms  p50={p50}ms  p95={p95}ms  max={max(lats)}ms"

    print("\n" + "=" * 70)
    print("LATENCY PROFILE — SUMMARY")
    print("=" * 70)
    print(f"Total queries: {total}")
    print(f"  Cold  ({len(cold)}):    {_stats(cold)}")
    print(f"  Cached({len(cached)}):  {_stats(cached)}")
    print(f"  Refusals({len(refusals)}): {_stats(refusals)}")

    # Budget violations
    cold_violations = [r for r in cold if r["total_ms"] > _TARGET_COLD_MS]
    cached_violations = [r for r in cached if r["total_ms"] > _TARGET_CACHED_MS]
    refusal_violations = [r for r in refusals if r["total_ms"] > _TARGET_REFUSAL_MS]
    print(f"\nBudget violations:")
    print(f"  Cold   > {_TARGET_COLD_MS}ms:    {len(cold_violations)}/{len(cold)}")
    print(f"  Cached > {_TARGET_CACHED_MS}ms: {len(cached_violations)}/{len(cached)}")
    print(f"  Refusal> {_TARGET_REFUSAL_MS}ms:   {len(refusal_violations)}/{len(refusals)}")

    # Per-step breakdown
    step_totals: dict[str, list[int]] = defaultdict(list)
    for r in records:
        for event in r.get("trace", []):
            step = event.get("step", "unknown")
            ms   = event.get("duration_ms", 0)
            step_totals[step].append(ms)

    if step_totals:
        print("\n-- Per-step averages (across all queries) ----------------------------------")
        sorted_steps = sorted(
            step_totals.items(), key=lambda x: sum(x[1]) / len(x[1]), reverse=True
        )
        for step, durations in sorted_steps:
            avg_ms  = int(sum(durations) / len(durations))
            max_ms  = max(durations)
            n_fired = len(durations)
            pct     = round(avg_ms / max(1, sum(
                int(sum(d) / len(d)) for d in step_totals.values()
            )) * 100, 1)
            print(f"  {step:<25} avg={avg_ms:>5}ms  max={max_ms:>6}ms  fired={n_fired:>3}x  ({pct}% of avg total)")

    # Top 5 slowest queries
    slow = sorted(records, key=lambda r: r["total_ms"], reverse=True)[:5]
    print("\n-- Top 5 slowest queries --------------------------------------------")
    for r in slow:
        print(f"  {r['total_ms']:>6}ms  {r['question']}")

    # Bottleneck identification
    if step_totals:
        top_step, top_durs = sorted_steps[0]
        avg_top = int(sum(top_durs) / len(top_durs))
        print(f"\n-- Top bottleneck: {top_step} (avg {avg_top}ms) -------------------------")
        if "retrieve" in top_step:
            print("  -> Check: are ChromaDB queries batched? Is vertical filter reducing search space?")
        elif "generate" in top_step:
            print("  -> Check: is streaming enabled? Can classification + generation overlap?")
        elif "understand" in top_step:
            print("  -> Check: is the understand LLM call cached? Can it use the fast model?")
        elif "rerank" in top_step:
            print("  -> Check: is the cross-encoder model running on GPU? Can RERANK_TOP_K be reduced?")
        elif "safety" in top_step or "classify" in top_step:
            print("  -> Check: is this a regex check (fast) or an LLM call (slow)?")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source",  default="hospital", choices=["hospital", "golden"],
                        help="Which eval set to profile (default: hospital)")
    parser.add_argument("--n",       type=int,   default=None,
                        help="Number of queries to run (default: all)")
    parser.add_argument("--cached",  action="store_true",
                        help="Run the same queries twice — second pass measures cache benefit")
    parser.add_argument("--delay",   type=float, default=2.0,
                        help="Seconds between queries to avoid rate limits (default: 2.0)")
    args = parser.parse_args()

    queries = load_queries(args.source, args.n)
    print(f"Loaded {len(queries)} queries from {args.source} set")

    orch = Orchestrator()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    all_records: list[dict] = []
    cache_hit_set: set[str] = set()

    # First pass (cold)
    print(f"\nPass 1 — cold run ({len(queries)} queries)")
    for i, q in enumerate(queries, 1):
        question = q["question"]
        hint     = q.get("module") if q.get("module") != "out_of_scope" else None
        print(f"  [{i:02d}] {question[:60]}…", end=" ", flush=True)
        record = run_with_trace(orch, question, hint)
        all_records.append({**record, "pass": "cold"})
        print(f"{record['total_ms']}ms  conf={record['confidence']}")
        if args.delay > 0 and i < len(queries):
            time.sleep(args.delay)

    # Second pass (cached) — same queries again
    if args.cached:
        print(f"\nPass 2 — cached run ({len(queries)} queries)")
        for i, q in enumerate(queries, 1):
            question = q["question"]
            hint     = q.get("module") if q.get("module") != "out_of_scope" else None
            print(f"  [{i:02d}] {question[:60]}…", end=" ", flush=True)
            record = run_with_trace(orch, question, hint)
            cache_hit_set.add(question)
            all_records.append({**record, "pass": "cached"})
            print(f"{record['total_ms']}ms  conf={record['confidence']}")
            if args.delay > 0 and i < len(queries):
                time.sleep(args.delay)

    # Write results
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, default=str) + "\n")
    print(f"\nResults written to: {OUTPUT_FILE}")

    # Summary
    cold_records   = [r for r in all_records if r["pass"] == "cold"]
    cached_records = [r for r in all_records if r["pass"] == "cached"]

    print_latency_report(cold_records, set())
    if cached_records:
        print("\n\n-- Cached pass summary ---------------------------------------------")
        print_latency_report(cached_records, cache_hit_set)


if __name__ == "__main__":
    main()
