"""
eval/summarize_latency_profile.py — Read logs/latency_profile.jsonl and emit
an ASCII-safe per-step breakdown for cold and cached passes (Windows cp1252
won't choke). Companion to the existing profile_latency.py whose Unicode
arrow crashes on Windows.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

LOG_PATH = Path(__file__).parent.parent / "logs" / "latency_profile.jsonl"


def stats_block(label: str, items: list[dict]) -> None:
    if not items:
        print(f"  {label}: n/a")
        return
    lats = [i["total_ms"] for i in items if i.get("total_ms", 0) >= 0]
    if not lats:
        print(f"  {label}: n/a")
        return
    avg = int(statistics.mean(lats))
    p50 = int(statistics.median(lats))
    s = sorted(lats)
    p95 = s[int(len(s) * 0.95)] if len(s) > 1 else s[0]
    p99 = s[min(len(s) - 1, int(len(s) * 0.99))]
    print(f"  {label} (n={len(items)}): avg={avg}ms p50={p50}ms p95={p95}ms p99={p99}ms max={max(lats)}ms")


def per_step(records: list[dict]) -> None:
    step_totals: dict[str, list[int]] = defaultdict(list)
    for r in records:
        for ev in r.get("trace", []):
            step = ev.get("step", "?")
            ms = ev.get("duration_ms", 0)
            step_totals[step].append(ms)
    if not step_totals:
        print("  (no trace data)")
        return
    rows = []
    for step, durs in step_totals.items():
        if not durs:
            continue
        avg = int(sum(durs) / len(durs))
        rows.append((step, avg, max(durs), len(durs)))
    rows.sort(key=lambda r: r[1], reverse=True)
    total_of_avgs = sum(r[1] for r in rows) or 1
    for step, avg, mx, n in rows:
        pct = avg / total_of_avgs * 100
        print(f"    {step:<22} avg={avg:>6}ms  max={mx:>6}ms  fired={n:>3}x  ({pct:5.1f}% of avg total)")


def main() -> None:
    rows = [json.loads(l) for l in open(LOG_PATH, encoding="utf-8") if l.strip()]
    cold   = [r for r in rows if r.get("pass") == "cold"]
    cached = [r for r in rows if r.get("pass") == "cached"]

    print("=" * 72)
    print(f"Cerna BGE per-step latency profile (n={len(rows)} from {LOG_PATH})")
    print("=" * 72)

    print("\n-- Cold pass end-to-end -----------------------------------------------")
    stats_block("all", cold)
    refusals_cold = [r for r in cold if r.get("is_refusal")]
    nonref_cold   = [r for r in cold if not r.get("is_refusal")]
    stats_block("non-refusal", nonref_cold)
    stats_block("refusal", refusals_cold)
    print("  Per-step (cold, all):")
    per_step(cold)
    print("  Per-step (cold, non-refusal only):")
    per_step(nonref_cold)

    print("\n-- Cached pass end-to-end ---------------------------------------------")
    stats_block("all", cached)
    refusals_cached = [r for r in cached if r.get("is_refusal")]
    nonref_cached   = [r for r in cached if not r.get("is_refusal")]
    stats_block("non-refusal", nonref_cached)
    stats_block("refusal", refusals_cached)
    print("  Per-step (cached, all):")
    per_step(cached)
    print("  Per-step (cached, non-refusal only):")
    per_step(nonref_cached)

    if cold and cached:
        c_avg = statistics.mean(r["total_ms"] for r in nonref_cold)
        h_avg = statistics.mean(r["total_ms"] for r in nonref_cached)
        if h_avg > 0:
            print(f"\n-- Cache benefit (non-refusal) ----------------------------------------")
            print(f"  cold avg  : {int(c_avg)} ms")
            print(f"  cached avg: {int(h_avg)} ms")
            print(f"  speedup   : {c_avg / h_avg:.2f}x  (saved {int(c_avg - h_avg)} ms per cached query)")


if __name__ == "__main__":
    main()
