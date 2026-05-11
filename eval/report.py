"""
eval/report.py — Summarise eval_results.jsonl into a human-readable report.

Usage:
    python eval/report.py
    python eval/report.py --results path/to/custom_results.jsonl
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

RESULTS_FILE = Path(__file__).parent / "eval_results.jsonl"


def load_results(path: Path) -> list[dict]:
    results = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def fmt_pct(v: float | None) -> str:
    return f"{v:.1%}" if v is not None else "n/a"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=str(RESULTS_FILE))
    args = parser.parse_args()

    results = load_results(Path(args.results))
    if not results:
        print("No results found.")
        return

    print("=" * 60)
    print("Cerna — Evaluation Report")
    print("=" * 60)
    print(f"\nTotal queries evaluated: {len(results)}\n")

    # ── Overall metrics ───────────────────────────────────────────────────────
    khr_values   = [r["keyword_hit_rate"] for r in results if r["keyword_hit_rate"] is not None]
    latencies    = [r["latency_ms"]       for r in results]
    chunk_scores = [r["top_chunk_score"]  for r in results if r["top_chunk_score"] > 0]
    refusal_vals = [r["refusal_correct"]  for r in results if r["refusal_correct"] is not None]

    print("OVERALL")
    print(f"  Keyword hit rate (mean)   : {fmt_pct(mean(khr_values) if khr_values else None)}")
    print(f"  Keyword hit rate (median) : {fmt_pct(median(khr_values) if khr_values else None)}")
    print(f"  Refusal accuracy          : {fmt_pct(mean(refusal_vals) if refusal_vals else None)}")
    print(f"  Top chunk score (mean)    : {mean(chunk_scores):.3f}" if chunk_scores else "  Top chunk score: n/a")
    print(f"  Latency mean (ms)         : {mean(latencies):.0f}")
    print(f"  Latency median (ms)       : {median(latencies):.0f}")
    print(f"  Latency p95 (ms)          : {sorted(latencies)[int(len(latencies) * 0.95)]:.0f}")

    # ── Per-module breakdown ──────────────────────────────────────────────────
    by_module: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_module[r["module"]].append(r)

    print("\nPER-MODULE KEYWORD HIT RATE")
    for mod, items in sorted(by_module.items()):
        mod_khr = [r["keyword_hit_rate"] for r in items if r["keyword_hit_rate"] is not None]
        avg = mean(mod_khr) if mod_khr else None
        print(f"  {mod:<16}: {fmt_pct(avg)}  ({len(items)} queries)")

    # ── Per-difficulty breakdown ──────────────────────────────────────────────
    by_diff: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_diff[r["difficulty"]].append(r)

    print("\nPER-DIFFICULTY KEYWORD HIT RATE")
    for diff in ("easy", "medium", "hard", "out_of_scope"):
        items = by_diff.get(diff, [])
        if not items:
            continue
        diff_khr = [r["keyword_hit_rate"] for r in items if r["keyword_hit_rate"] is not None]
        avg = mean(diff_khr) if diff_khr else None
        print(f"  {diff:<12}: {fmt_pct(avg)}  ({len(items)} queries)")

    # ── Confidence distribution ───────────────────────────────────────────────
    conf_counts: dict[str, int] = defaultdict(int)
    for r in results:
        conf_counts[r["confidence"]] += 1
    print("\nCONFIDENCE DISTRIBUTION")
    for conf, count in sorted(conf_counts.items()):
        print(f"  {conf:<10}: {count} ({count/len(results):.1%})")

    # ── Worst performers ─────────────────────────────────────────────────────
    scored = [r for r in results if r["keyword_hit_rate"] is not None]
    if scored:
        worst = sorted(scored, key=lambda r: r["keyword_hit_rate"])[:5]
        print("\nFIVE WORST-PERFORMING QUERIES")
        for r in worst:
            print(f"  [{r['id']}] khr={fmt_pct(r['keyword_hit_rate'])}  "
                  f"{r['question'][:70]}")


if __name__ == "__main__":
    main()
