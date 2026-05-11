"""
scripts/diagnose_new25_gap.py — Compare BGE vs MiniLM retrieval on the 5
new-25 queries that failed on BGE (passed on MiniLM in 4 of 5 cases).

For each failing query, this:
  1. Reads the question + expected_keywords from the v2 set.
  2. Runs the same understand_query rewrite (so retrieval inputs are identical).
  3. Pulls top-10 chunks from BOTH `cerner_docs` (MiniLM) and `cerner_docs_bge`
     using the formal_query.
  4. Reports per-collection:
     - top chunk source filenames
     - top scores
     - which (if any) of the expected_keywords appear in the top-10 chunks

Output: a per-query side-by-side table and a summary by failure type.
No LLM calls beyond the single understand_query rewrite per question.

Usage:
    python scripts/diagnose_new25_gap.py
    python scripts/diagnose_new25_gap.py --top-k 5
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from config import CHROMA_DIR
from query_rewriter import understand_query

FAILED_IDS = [
    "hs-clerk-013",
    "hs-it-014",
    "hs-nurse-019",
    "hs-nurse-020",
    "hs-physician-012",
]
V2_PATH = Path("eval/hospital_staff_queries_v2.jsonl")


def load_query(qid: str) -> dict | None:
    with open(V2_PATH, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                q = json.loads(line)
                if q["id"] == qid:
                    return q
    return None


def open_collection(name: str, model: str) -> Chroma:
    emb = HuggingFaceEmbeddings(
        model_name=model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    return Chroma(
        collection_name=name,
        embedding_function=emb,
        persist_directory=CHROMA_DIR,
    )


def retrieve(store: Chroma, query: str, k: int) -> list[tuple[float, str, str]]:
    docs_with_scores = store.similarity_search_with_score(query, k=k)
    out = []
    for doc, score in docs_with_scores:
        src = (doc.metadata or {}).get("source", "?")
        out.append((float(score), os.path.basename(src), doc.page_content))
    return out


def keyword_hit_count(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    text_l = text.lower()
    hits = [k for k in keywords if k.lower() in text_l]
    return len(hits), hits


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--top-k", type=int, default=10)
    args = p.parse_args()

    print(f"Loading collections (CHROMA_DIR={CHROMA_DIR})...")
    bge = open_collection("cerner_docs_bge", "BAAI/bge-large-en-v1.5")
    mini = open_collection("cerner_docs", "sentence-transformers/all-MiniLM-L6-v2")
    print("Collections ready.\n")

    summary = []

    for qid in FAILED_IDS:
        q = load_query(qid)
        if q is None:
            print(f"[skip] {qid} not found")
            continue
        question = q["question"]
        expected_kw = q.get("expected_keywords", [])
        expected_behavior = q.get("expected_behavior", "answer")
        module = q.get("module", "?")

        # Use the same understand_query rewrite the pipeline would use.
        understood = understand_query(question, "")
        formal = understood.formal_query or question

        print("=" * 88)
        print(f"[{qid}]  module={module}  expected_behavior={expected_behavior}")
        print(f"  Q       : {question}")
        print(f"  formal  : {formal}")
        print(f"  expected: {expected_kw}")
        print()

        bge_hits = retrieve(bge, formal, args.top_k)
        mini_hits = retrieve(mini, formal, args.top_k)

        bge_top_text = "\n".join(h[2] for h in bge_hits)
        mini_top_text = "\n".join(h[2] for h in mini_hits)
        bge_kw_hits, bge_hit_kw = keyword_hit_count(bge_top_text, expected_kw)
        mini_kw_hits, mini_hit_kw = keyword_hit_count(mini_top_text, expected_kw)

        print(f"  BGE top-{args.top_k}:")
        for i, (s, src, _) in enumerate(bge_hits, 1):
            print(f"    [{i:>2}] {s:>5.3f}  {src}")
        print(f"  BGE keyword hits in top-{args.top_k}: {bge_kw_hits}/{len(expected_kw)}  hit={bge_hit_kw}")

        print(f"  MiniLM top-{args.top_k}:")
        for i, (s, src, _) in enumerate(mini_hits, 1):
            print(f"    [{i:>2}] {s:>5.3f}  {src}")
        print(f"  MiniLM keyword hits in top-{args.top_k}: {mini_kw_hits}/{len(expected_kw)}  hit={mini_hit_kw}")

        # Source overlap
        bge_srcs = {h[1] for h in bge_hits}
        mini_srcs = {h[1] for h in mini_hits}
        overlap = bge_srcs & mini_srcs
        print(f"  Source-set overlap: {len(overlap)}/{args.top_k}  shared={sorted(overlap)}")
        print(f"  BGE-only sources : {sorted(bge_srcs - mini_srcs)}")
        print(f"  MiniLM-only      : {sorted(mini_srcs - bge_srcs)}")
        print()

        summary.append({
            "id": qid,
            "module": module,
            "expected_behavior": expected_behavior,
            "bge_kw_hits": bge_kw_hits,
            "mini_kw_hits": mini_kw_hits,
            "src_overlap": len(overlap),
            "src_total": args.top_k,
        })

    print("=" * 88)
    print("Summary (rounded to top-k=10):")
    print(f"  {'id':<22} {'module':<14} {'exp_beh':<10} {'BGE kw/exp':<10} {'Mini kw/exp':<10} {'src overlap':<12}")
    for s in summary:
        print(
            f"  {s['id']:<22} {s['module']:<14} {s['expected_behavior']:<10} "
            f"{s['bge_kw_hits']}/{s['src_total']:<8} "
            f"{s['mini_kw_hits']}/{s['src_total']:<8} "
            f"{s['src_overlap']}/{s['src_total']}"
        )


if __name__ == "__main__":
    main()
