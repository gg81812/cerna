"""
eval/vague_query_eval.py — Retrieval-quality benchmark for vague natural-language queries.

Evaluates RETRIEVAL only (no LLM generation) — safe to run without hitting Groq TPD limits.

Pass criteria per query:
  - top semantic_score after multi-query retrieval >= 0.40
  - at least one retrieved chunk.vertical matches expected_module

Usage:
    python eval/vague_query_eval.py              # full 40-query vague set
    python eval/vague_query_eval.py --formal     # formal regression set (5 queries)
    python eval/vague_query_eval.py --all        # both sets
    python eval/vague_query_eval.py --retrieval-only   # skip understand_query (raw query only)

Outputs:
    eval/vague_eval_results.jsonl   — per-query detail
    Prints a Markdown table to stdout
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from retriever import HealthcareRetriever
from query_rewriter import understand_query
from config import TOP_K, RERANK_ENABLED, RERANK_TOP_K, DID_YOU_MEAN_THRESHOLD

RESULTS_FILE = Path(__file__).parent / "vague_eval_results.jsonl"
PASS_SCORE = 0.40


def _classification_to_vertical(cls: str) -> str | None:
    mapping = {
        "MILLENNIUM":    "millennium",
        "POWERCHART":    "powerchart",
        "REVENUE_CYCLE": "revenue_cycle",
        "FHIR":          "fhir",
        "CLINICAL":      "clinical",
        "GENERAL":       None,
    }
    return mapping.get(cls.upper())


def run_one(
    retriever: HealthcareRetriever,
    item: dict,
    retrieval_only: bool = False,
) -> dict:
    """Run retrieval for one query and score it."""
    query = item["query"]
    expected_module = item["expected_module"].lower()
    fetch_k = RERANK_TOP_K if RERANK_ENABLED else TOP_K

    t0 = time.time()
    understood_intent = "question"
    formal_query = query
    variants: list[str] = []
    is_ambiguous = False

    if not retrieval_only:
        try:
            understood = understand_query(query, "")
            understood_intent = understood.intent
            formal_query = understood.formal_query or query
            variants = understood.variants
            is_ambiguous = understood.is_ambiguous
            retrieval_queries = understood.all_retrieval_queries
        except Exception as exc:
            print(f"  [WARN] understand_query failed: {exc}")
            retrieval_queries = [query]
    else:
        retrieval_queries = [query]

    # Multi-query retrieval
    all_result_lists = []
    for q in retrieval_queries:
        try:
            chunks = retriever.query(q, vertical=None, top_k=fetch_k)
            all_result_lists.append(chunks)
        except Exception as exc:
            print(f"  [WARN] retrieval failed for {q!r}: {exc}")

    # RRF fusion of multi-query results
    if not all_result_lists:
        top_score = 0.0
        all_chunks = []
    elif len(all_result_lists) == 1:
        all_chunks = all_result_lists[0]
    else:
        rrf_scores: dict[str, float] = {}
        chunk_map:  dict[str, object] = {}
        sem_scores: dict[str, float] = {}
        k = 60
        for result_list in all_result_lists:
            for rank, chunk in enumerate(result_list):
                key = f"{chunk.source}|||{chunk.text[:200]}"
                rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
                sem_scores[key] = max(sem_scores.get(key, 0.0), chunk.semantic_score)
                if key not in chunk_map:
                    chunk_map[key] = chunk
        sorted_keys = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)
        from retriever import RetrievedChunk
        all_chunks = [
            RetrievedChunk(
                text=chunk_map[k2].text,
                source=chunk_map[k2].source,
                vertical=chunk_map[k2].vertical,
                score=round(rrf_scores[k2], 6),
                source_weight=chunk_map[k2].source_weight,
                doc_type=chunk_map[k2].doc_type,
                priority_tier=chunk_map[k2].priority_tier,
                semantic_score=round(sem_scores.get(k2, 0.0), 4),
                source_quality=chunk_map[k2].source_quality,
            )
            for k2 in sorted_keys
        ]

    top_chunks = all_chunks[:TOP_K]
    top_score = max((c.semantic_score for c in top_chunks), default=0.0)
    modules_found = list({c.vertical for c in top_chunks if c.vertical})
    latency_ms = int((time.time() - t0) * 1000)

    score_pass   = top_score >= PASS_SCORE
    module_pass  = expected_module in modules_found
    overall_pass = score_pass and module_pass

    return {
        "id":              item["id"],
        "query":           query,
        "expected_module": expected_module,
        "intent":          understood_intent,
        "formal_query":    formal_query,
        "variants":        variants,
        "is_ambiguous":    is_ambiguous,
        "top_score":       round(top_score, 4),
        "modules_found":   modules_found,
        "score_pass":      score_pass,
        "module_pass":     module_pass,
        "pass":            overall_pass,
        "latency_ms":      latency_ms,
        "num_result_lists": len(all_result_lists),
    }


def print_table(results: list[dict], title: str) -> None:
    print(f"\n## {title}")
    print(f"\n{'ID':<12} {'Query':<45} {'Intent':<16} {'Score':>6} {'Module':>6} {'Pass':>5}")
    print("-" * 95)
    for r in results:
        status = "PASS" if r["pass"] else ("SCORE" if r["score_pass"] else "FAIL")
        q_short = r["query"][:43] + ".." if len(r["query"]) > 45 else r["query"]
        mod_mark = "Y" if r["module_pass"] else "N"
        print(
            f"{r['id']:<12} {q_short:<45} {r['intent']:<16} "
            f"{r['top_score']:>6.3f} {mod_mark:>6} {status:>5}"
        )

    passed = sum(1 for r in results if r["pass"])
    total  = len(results)
    score_only = sum(1 for r in results if r["score_pass"])
    print(f"\nPass: {passed}/{total} ({passed/total:.0%})  |  Score>=0.4: {score_only}/{total}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal",         action="store_true", help="Run formal regression set only")
    parser.add_argument("--all",            action="store_true", help="Run both sets")
    parser.add_argument("--retrieval-only", action="store_true",
                        help="Skip understand_query — use raw query for retrieval")
    args = parser.parse_args()

    from tests.vague_queries import VAGUE_QUERIES, FORMAL_QUERIES

    if args.formal:
        queries = FORMAL_QUERIES
        title = "Formal Regression Queries"
    elif args.all:
        queries = VAGUE_QUERIES + FORMAL_QUERIES
        title = "All Queries (Vague + Formal)"
    else:
        queries = VAGUE_QUERIES
        title = "Vague Natural-Language Queries"

    print("=" * 70)
    print(f"Cerna — Vague Query Retrieval Benchmark")
    print(f"Pass threshold: top semantic_score >= {PASS_SCORE}  AND  module matches")
    print(f"Mode: {'retrieval-only (no rewriter)' if args.retrieval_only else 'full pipeline (with understand_query)'}")
    print("=" * 70)
    print("\nInitialising retriever…")
    retriever = HealthcareRetriever()

    results = []
    for i, item in enumerate(queries, 1):
        print(f"[{i:02d}/{len(queries)}] {item['id']:<10} {item['query'][:55]}…", end=" ", flush=True)
        r = run_one(retriever, item, retrieval_only=args.retrieval_only)
        results.append(r)
        status = "PASS" if r["pass"] else "FAIL"
        print(f"{status}  score={r['top_score']:.3f}  {r['latency_ms']}ms")

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"\nDetailed results -> {RESULTS_FILE}")

    print_table(results, title)


if __name__ == "__main__":
    main()
