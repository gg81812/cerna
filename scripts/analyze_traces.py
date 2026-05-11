"""
scripts/analyze_traces.py — Latency and reliability report from trace_log.jsonl

Usage:
    python scripts/analyze_traces.py
    python scripts/analyze_traces.py --log logs/trace_log.jsonl --last 100

Outputs a summary table: per-step p50/p95/p99 latency, error rates, and
an end-to-end pipeline latency distribution.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * pct
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def load_traces(log_path: str, last_n: int | None = None) -> list[dict]:
    path = Path(log_path)
    if not path.exists():
        print(f"[analyze_traces] log file not found: {log_path}")
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    if last_n:
        lines = lines[-last_n:]
    records = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def analyze(records: list[dict]) -> None:
    if not records:
        print("No trace records found.")
        return

    total = len(records)
    errors = sum(1 for r in records if r.get("error"))
    print(f"\n=== Cerna Trace Analysis ({total} requests) ===")
    print(f"  Error rate: {errors}/{total} ({100*errors/total:.1f}%)")

    # End-to-end latency
    e2e = sorted(r.get("total_ms", 0) for r in records)
    print(f"\nEnd-to-end latency (ms):")
    print(f"  p50={_percentile(e2e, 0.5):.0f}  p95={_percentile(e2e, 0.95):.0f}  "
          f"p99={_percentile(e2e, 0.99):.0f}  max={max(e2e):.0f}  mean={sum(e2e)/len(e2e):.0f}")

    # Intent distribution
    intent_counts: dict[str, int] = defaultdict(int)
    for r in records:
        intent_counts[r.get("intent", "unknown")] += 1
    print(f"\nIntent distribution:")
    for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
        print(f"  {intent:<20} {count:4d}  ({100*count/total:.1f}%)")

    # Per-step latency
    step_latencies: dict[str, list[float]] = defaultdict(list)
    step_errors: dict[str, int] = defaultdict(int)
    for r in records:
        for step in r.get("steps", []):
            name = step.get("step", "unknown")
            ms = step.get("duration_ms", 0)
            step_latencies[name].append(ms)
            if not step.get("success", True):
                step_errors[name] += 1

    print(f"\nPer-step latency (ms):")
    header = f"  {'Step':<20} {'Count':>6}  {'p50':>6}  {'p95':>6}  {'p99':>6}  {'Errors':>7}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for step, latencies in sorted(step_latencies.items(), key=lambda x: -sum(x[1])/max(len(x[1]),1)):
        sl = sorted(latencies)
        errs = step_errors.get(step, 0)
        print(
            f"  {step:<20} {len(sl):>6}  "
            f"{_percentile(sl, 0.5):>6.0f}  {_percentile(sl, 0.95):>6.0f}  "
            f"{_percentile(sl, 0.99):>6.0f}  {errs:>7}"
        )

    # Slow query flag (> 5000ms end-to-end)
    slow = [r for r in records if r.get("total_ms", 0) > 5000]
    if slow:
        print(f"\nSlow requests (>5s): {len(slow)}")
        for r in slow[:5]:
            q = r.get("query", "")[:60]
            print(f"  [{r.get('total_ms', 0)}ms] {q!r}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Analyze Cerna trace logs")
    parser.add_argument("--log", default="logs/trace_log.jsonl", help="Path to trace_log.jsonl")
    parser.add_argument("--last", type=int, default=None, help="Analyze only the last N requests")
    args = parser.parse_args()

    # Resolve path relative to project root (script is in scripts/)
    log_path = args.log
    if not os.path.isabs(log_path):
        project_root = Path(__file__).parent.parent
        log_path = str(project_root / log_path)

    records = load_traces(log_path, args.last)
    analyze(records)


if __name__ == "__main__":
    main()
