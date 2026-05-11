"""
eval/rerun_rate_limited_bge.py — Re-run only the rate-limited queries from
the Phase 2 BGE eval, on fresh Groq quota.

Identifies queries whose response_excerpt in eval/hospital_eval_v2_results_bge.jsonl
contains the rate-limit fallback marker, re-runs each via the same
evaluate_single() helper, and APPENDS the new rows (with cleanup_rerun=True)
to the same file. Original rows are preserved so the audit trail is intact;
downstream analysis should prefer cleanup_rerun rows over the originals when
both share an id.

Usage:
    python eval/rerun_rate_limited_bge.py
    python eval/rerun_rate_limited_bge.py --delay 4.0
    python eval/rerun_rate_limited_bge.py --dry-run            # list IDs only
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

_EVAL_DIR = Path(__file__).parent
RESULTS_FILE = _EVAL_DIR / "hospital_eval_v2_results_bge.jsonl"
RL_MARKER = "temporarily unable to generate a detailed response"


def find_rate_limited_ids(results_path: Path) -> list[str]:
    rl_ids: list[str] = []
    with open(results_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("cleanup_rerun"):
                continue
            if RL_MARKER in row.get("response_excerpt", "").lower():
                rl_ids.append(row["id"])
    return rl_ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=float, default=4.0,
                        help="Seconds between queries (default 4.0; bump if quota is tight)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List which IDs would be re-run, then exit")
    args = parser.parse_args()

    if not RESULTS_FILE.exists():
        print(f"ERROR: {RESULTS_FILE} not found")
        sys.exit(1)

    rl_ids = find_rate_limited_ids(RESULTS_FILE)
    print(f"Rate-limited IDs in {RESULTS_FILE.name}: {len(rl_ids)}")
    for i in rl_ids:
        print(f"  {i}")

    if args.dry_run:
        print("\n[dry-run] exiting without re-running.")
        return

    queries = load_hospital_set(persona_filter=None, version="v2")
    by_id = {q["id"]: q for q in queries}
    missing = [i for i in rl_ids if i not in by_id]
    if missing:
        print(f"ERROR: {len(missing)} ids not found in v2 query set: {missing}")
        sys.exit(1)

    rerun_items = [by_id[i] for i in rl_ids]
    print(f"\nInitialising orchestrator (BGE collection)…")
    orch = Orchestrator()

    out_rows = []
    rl_marker_hits = 0
    fail_modes = {"pass": 0, "honest": 0, "bad": 0}
    t_start = time.time()

    for i, item in enumerate(rerun_items, 1):
        print(
            f"[{i:02d}/{len(rerun_items)}] {item['id']:<22} {item['question'][:55]}…",
            end=" ",
            flush=True,
        )
        result = evaluate_single(orch, item)
        result["cleanup_rerun"] = True
        out_rows.append(result)
        status = "PASS" if result["passed"] else f"FAIL({result['fail_mode']})"
        still_rl = RL_MARKER in result["response_excerpt"].lower()
        if still_rl:
            rl_marker_hits += 1
        fail_modes[result["fail_mode"]] = fail_modes.get(result["fail_mode"], 0) + 1
        print(
            f"{status:<12} khr={result['keyword_hit_rate']:.0%}  "
            f"conf={result['confidence']}  {result['latency_ms']}ms"
            + ("  [STILL-RL]" if still_rl else "")
        )
        if args.delay > 0 and i < len(rerun_items):
            time.sleep(args.delay)

    # Append to the same file so the audit trail is preserved
    with open(RESULTS_FILE, "a", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r) + "\n")

    elapsed = time.time() - t_start
    print()
    print("=" * 70)
    print(f"RE-RUN COMPLETE  —  {len(out_rows)} queries in {elapsed/60:.1f} min")
    print("=" * 70)
    passed = sum(1 for r in out_rows if r["passed"])
    print(f"Pass:        {passed}/{len(out_rows)}")
    print(f"Bad fails:   {fail_modes.get('bad', 0)}")
    print(f"Still RL:    {rl_marker_hits}")
    print(f"Appended to: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
