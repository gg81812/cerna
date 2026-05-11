"""
eval/run_eval.py — Run the 75-query golden set evaluation against Cerna.

Outputs: eval/eval_results.jsonl

Usage:
    python eval/run_eval.py
    python eval/run_eval.py --limit 10          # quick smoke test
    python eval/run_eval.py --module fhir       # single module

Metrics computed per query:
  - keyword_hit_rate:  fraction of expected_keywords found in the response
  - refusal_correct:   True if expected_refusal matches actual refusal
  - latency_ms:        end-to-end wall-clock ms
  - confidence:        "high" | "medium" | "low" from CernaResponse
  - top_chunk_score:   highest retrieval score across all chunks
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator import Orchestrator

GOLDEN_SET = Path(__file__).parent / "golden_set.jsonl"
RESULTS_FILE = Path(__file__).parent / "eval_results.jsonl"
# When --module is specified, results are written to eval_results_{module}.jsonl
# to avoid overwriting the full results file


def load_golden_set(module_filter: str | None = None) -> list[dict]:
    queries = []
    with open(GOLDEN_SET, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                q = json.loads(line)
                if module_filter and q["module"] != module_filter:
                    continue
                queries.append(q)
    return queries


def evaluate_single(orch: Orchestrator, item: dict) -> dict:
    question = item["question"]
    module   = item["module"] if item["module"] != "out_of_scope" else None
    expected_keywords = item.get("expected_keywords", [])
    expected_refusal  = item.get("expected_refusal", False)

    t0 = time.time()
    try:
        prepared     = orch.prepare(question, [], module_hint=module)
        cerna_resp   = orch.generate_structured(prepared)
        latency_ms   = int((time.time() - t0) * 1000)
        response_text = cerna_resp.to_markdown()
        actual_refusal = bool(prepared.refusal or cerna_resp.confidence == "low")
        confidence     = cerna_resp.confidence
        top_chunk_score = max((c.semantic_score for c in prepared.chunks), default=0.0)
    except Exception as exc:
        latency_ms      = int((time.time() - t0) * 1000)
        response_text   = f"ERROR: {exc}"
        actual_refusal  = False
        confidence      = "error"
        top_chunk_score = 0.0

    # Keyword hit rate
    if expected_keywords:
        resp_lower = response_text.lower()
        hits = sum(1 for kw in expected_keywords if kw.lower() in resp_lower)
        keyword_hit_rate = round(hits / len(expected_keywords), 3)
    else:
        keyword_hit_rate = None

    refusal_correct = (actual_refusal == expected_refusal) if expected_refusal else None

    return {
        "id":               item["id"],
        "module":           item["module"],
        "difficulty":       item["difficulty"],
        "question":         question,
        "keyword_hit_rate": keyword_hit_rate,
        "refusal_correct":  refusal_correct,
        "confidence":       confidence,
        "top_chunk_score":  round(top_chunk_score, 4),
        "latency_ms":       latency_ms,
        "response_excerpt": response_text[:300],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",  type=int,  default=None, help="Max queries to run")
    parser.add_argument("--module", type=str,  default=None, help="Filter to one module")
    parser.add_argument("--delay",  type=float, default=3.0,
                        help="Seconds to sleep between queries (default: 3.0). "
                             "Increase to avoid Groq TPD rate limits on long runs.")
    args = parser.parse_args()

    print("=" * 60)
    print("Cerna — Golden Set Evaluation")
    print("=" * 60)

    queries = load_golden_set(args.module)
    if args.limit:
        queries = queries[: args.limit]

    # Use module-specific output file when filtering by module to avoid
    # overwriting the combined results file
    results_file = RESULTS_FILE
    if args.module:
        results_file = Path(__file__).parent / f"eval_results_{args.module}.jsonl"

    print(f"\nLoaded {len(queries)} queries"
          + (f" (module={args.module})" if args.module else ""))
    print("Initialising orchestrator…")
    orch = Orchestrator()
    print()

    results = []
    for i, item in enumerate(queries, 1):
        print(f"[{i:02d}/{len(queries)}] {item['id']:<12} {item['question'][:60]}…", end=" ", flush=True)
        result = evaluate_single(orch, item)
        results.append(result)
        khr = f"{result['keyword_hit_rate']:.0%}" if result["keyword_hit_rate"] is not None else "n/a"
        print(f"khr={khr}  conf={result['confidence']}  {result['latency_ms']}ms")
        if args.delay > 0 and i < len(queries):
            time.sleep(args.delay)

    with open(results_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"\nResults written to: {results_file}")
    print("Run `python eval/report.py` to see summary statistics.")


if __name__ == "__main__":
    main()
