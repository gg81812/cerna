"""
eval/reranker_e2e_test.py — End-to-end reranker decision test.

Runs 10 selected queries twice: once with RERANK_ENABLED=False (baseline)
and once with RERANK_ENABLED=True. Compares KHR side-by-side.

Query selection:
  - 5 complex/technical (likely to benefit from cross-encoder re-scoring)
  - 3 formal/structured (well-defined retrieval needs)
  - 2 cross-domain / keyword-fail risk (BM25 alone may pull wrong chunks)

Usage:
    python eval/reranker_e2e_test.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

RESULTS_FILE = Path(__file__).parent / "reranker_e2e_results.json"

# 10 representative queries: id, question, expected_keywords, category
TEST_QUERIES = [
    # ── 5 complex/technical ──────────────────────────────────────────────
    {
        "id": "mil-013",
        "category": "complex",
        "module": "millennium",
        "question": "How do you implement a custom Discern rule to fire clinical alerts in Millennium?",
        "expected_keywords": ["Discern", "rule", "alert", "CCL", "criteria"],
    },
    {
        "id": "mil-015",
        "category": "complex",
        "module": "millennium",
        "question": "How does Cerner Millennium manage multi-facility data partitioning?",
        "expected_keywords": ["facility", "partition", "data", "Millennium", "domain"],
    },
    {
        "id": "fhir-013",
        "category": "complex",
        "module": "fhir",
        "question": "How do you implement a SMART on FHIR standalone launch for a patient-facing app?",
        "expected_keywords": ["SMART", "standalone", "launch", "OAuth", "patient"],
    },
    {
        "id": "rc-013",
        "category": "complex",
        "module": "revenue_cycle",
        "question": "How do you configure custom charge routing rules in Cerner Revenue Cycle?",
        "expected_keywords": ["charge", "routing", "rule", "Revenue Cycle", "configuration"],
    },
    {
        "id": "pc-013",
        "category": "complex",
        "module": "powerchart",
        "question": "How do you build a complex PowerNote template with dynamic content and auto-population?",
        "expected_keywords": ["PowerNote", "template", "dynamic", "auto", "documentation"],
    },
    # ── 3 formal/structured ──────────────────────────────────────────────
    {
        "id": "mil-014",
        "category": "formal",
        "module": "millennium",
        "question": "What are the performance tuning best practices for CCL queries on large patient populations?",
        "expected_keywords": ["CCL", "performance", "tuning", "query", "index"],
    },
    {
        "id": "pc-012",
        "category": "formal",
        "module": "powerchart",
        "question": "How are FYI alerts and hard stops configured in CPOE?",
        "expected_keywords": ["CPOE", "alert", "hard stop", "FYI", "order"],
    },
    {
        "id": "fhir-015",
        "category": "formal",
        "module": "fhir",
        "question": "How do you map Cerner proprietary data to FHIR R4 Observation resources?",
        "expected_keywords": ["Observation", "FHIR", "mapping", "R4", "resource"],
    },
    # ── 2 cross-domain / keyword-fail risk ───────────────────────────────
    {
        "id": "rc-015",
        "category": "keyword_fail_risk",
        "module": "revenue_cycle",
        "question": "How does Cerner's CDI workflow integrate with physician query management?",
        "expected_keywords": ["CDI", "physician", "query", "documentation", "Revenue Cycle"],
    },
    {
        "id": "pc-015",
        "category": "keyword_fail_risk",
        "module": "powerchart",
        "question": "How does PowerChart integrate with external lab systems via HL7 interfaces?",
        "expected_keywords": ["HL7", "interface", "lab", "PowerChart", "integration"],
    },
]


def compute_khr(response_text: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    text_lower = response_text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in text_lower)
    return round(hits / len(keywords), 3)


def run_query(orch, item: dict) -> dict:
    t0 = time.time()
    try:
        prepared   = orch.prepare(item["question"], [], module_hint=item["module"])
        cerna_resp = orch.generate_structured(prepared)
        latency_ms = int((time.time() - t0) * 1000)
        response_text = cerna_resp.to_markdown()
        khr = compute_khr(response_text, item["expected_keywords"])
        return {
            "id":        item["id"],
            "khr":       khr,
            "confidence": cerna_resp.confidence,
            "latency_ms": latency_ms,
            "error":     None,
            "response_excerpt": response_text[:250],
        }
    except Exception as exc:
        latency_ms = int((time.time() - t0) * 1000)
        return {
            "id":        item["id"],
            "khr":       0.0,
            "confidence": "error",
            "latency_ms": latency_ms,
            "error":     str(exc)[:300],
            "response_excerpt": f"ERROR: {exc}",
        }


def run_batch(label: str, rerank: bool, delay: float = 5.0) -> list[dict]:
    import importlib
    import config as cfg_module

    os.environ["RERANK_ENABLED"] = "true" if rerank else "false"
    importlib.reload(cfg_module)

    # Re-import orchestrator with fresh config
    import orchestrator as orch_module
    importlib.reload(orch_module)
    orch = orch_module.Orchestrator()

    results = []
    print(f"\n{'='*60}")
    print(f"  {label}  (RERANK_ENABLED={rerank})")
    print(f"{'='*60}")

    for item in TEST_QUERIES:
        print(f"  [{item['id']}] {item['question'][:65]}...", end="", flush=True)
        r = run_query(orch, item)
        r["category"] = item["category"]
        results.append(r)
        status = f"KHR={r['khr']:.2f}  conf={r['confidence']}"
        if r["error"]:
            status += f"  ERROR={r['error'][:50]}"
        print(f"  {status}")
        time.sleep(delay)

    return results


def main():
    import config as cfg
    print("Cerna — Reranker E2E Decision Test")
    print(f"Queries: {len(TEST_QUERIES)}")
    print(f"Current RERANK_ENABLED={cfg.RERANK_ENABLED}")

    baseline = run_batch("BASELINE  (retrieval-only)", rerank=False)
    time.sleep(10)
    reranked = run_batch("RERANKER  (cross-encoder)", rerank=True)

    # Reset to False
    os.environ["RERANK_ENABLED"] = "false"

    # Build comparison table
    baseline_map = {r["id"]: r for r in baseline}
    reranked_map = {r["id"]: r for r in reranked}

    print(f"\n{'='*80}")
    print("COMPARISON TABLE")
    print(f"{'='*80}")
    print(f"{'ID':<10} {'Cat':<18} {'Base KHR':>8} {'Rank KHR':>8} {'Delta':>7} {'Base conf':<10} {'Rank conf':<10}")
    print("-" * 80)

    gains = []
    losses = []
    ties = []
    for item in TEST_QUERIES:
        b = baseline_map[item["id"]]
        r = reranked_map[item["id"]]
        delta = round(r["khr"] - b["khr"], 3)
        if delta > 0.05:
            gains.append(delta)
        elif delta < -0.05:
            losses.append(delta)
        else:
            ties.append(item["id"])
        print(f"{item['id']:<10} {item['category']:<18} {b['khr']:>8.2f} {r['khr']:>8.2f} {delta:>+7.2f}  {b['confidence']:<10} {r['confidence']:<10}")

    avg_base = round(sum(b["khr"] for b in baseline) / len(baseline), 3)
    avg_rank = round(sum(r["khr"] for r in reranked) / len(reranked), 3)
    print("-" * 80)
    print(f"{'AVERAGE':<10} {'':<18} {avg_base:>8.2f} {avg_rank:>8.2f} {avg_rank-avg_base:>+7.2f}")

    print(f"\nGains (>+0.05): {len(gains)}  Losses (>-0.05): {len(losses)}  Ties: {len(ties)}")

    verdict = "ENABLE" if avg_rank > avg_base + 0.02 else ("DISABLE" if avg_rank < avg_base - 0.02 else "NEUTRAL")
    print(f"\nVERDICT: {verdict} reranker  (avg delta={avg_rank-avg_base:+.3f})")

    # Save results
    output = {
        "run_date": "2026-04-20",
        "n_queries": len(TEST_QUERIES),
        "avg_khr_baseline": avg_base,
        "avg_khr_reranked": avg_rank,
        "avg_delta": round(avg_rank - avg_base, 3),
        "verdict": verdict,
        "baseline": baseline,
        "reranked": reranked,
        "comparison": [
            {
                "id": item["id"],
                "category": item["category"],
                "question": item["question"],
                "base_khr": baseline_map[item["id"]]["khr"],
                "rank_khr": reranked_map[item["id"]]["khr"],
                "delta": round(reranked_map[item["id"]]["khr"] - baseline_map[item["id"]]["khr"], 3),
            }
            for item in TEST_QUERIES
        ],
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
