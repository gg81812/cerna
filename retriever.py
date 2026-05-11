"""
retriever.py — Hybrid BM25 + semantic retrieval with RRF fusion, MMR diversity,
and source-weight tiebreaking.

Pipeline:
  1. Semantic search (ChromaDB cosine)  → fetch_k candidates
  2. BM25 keyword search               → fetch_k candidates
  3. Reciprocal Rank Fusion (k=60)     → ranked merged list
  4. MMR diversity filter              → controlled by MMR_LAMBDA env var
  5. Source-weight tiebreaking         → prefer authoritative sources within 0.05 score bands
  6. Return top_k chunks

Standalone test:
    python retriever.py
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from rank_bm25 import BM25Okapi

from config import (
    CHROMA_DIR,
    ACTIVE_COLLECTION,
    EMBEDDING_MODEL,
    EMBEDDING_MODEL_BGE,
    CHROMA_COLLECTION_BGE,
    TOP_K,
    RERANK_TOP_K,
    RERANK_ENABLED,
    MMR_LAMBDA,
    CERNER_DIRS,
)


# ── Return type ───────────────────────────────────────────────────────────────

@dataclass
class RetrievedChunk:
    text: str
    source: str
    vertical: str           # Cerner module (millennium, fhir, …)
    score: float            # RRF score (higher = more relevant)
    source_weight: float = 0.5   # from doc manifest (ucern=1.0, third_party=0.5, …)
    doc_type: str = "community"  # spec / official / blog / community
    priority_tier: str = "nice"  # must / should / nice
    semantic_score: float = 0.0  # raw cosine similarity score (used for confidence gating)
    source_quality: str = "secondary"  # primary / secondary / archival_secondary


# ── Retriever class ───────────────────────────────────────────────────────────

class HealthcareRetriever:
    """
    Loads ChromaDB once, builds a BM25 index over the same corpus, and
    exposes a single `query()` that fuses both rankings via RRF, applies
    MMR diversity, and breaks ties using source_weight.
    Re-use one instance per app session.
    """

    def __init__(self):
        if not os.path.isdir(CHROMA_DIR):
            raise FileNotFoundError(
                f"ChromaDB store not found at '{CHROMA_DIR}'. "
                "Run `python ingest.py` first."
            )

        print("[Retriever] Loading embedding model…")
        _model_name = EMBEDDING_MODEL_BGE if ACTIVE_COLLECTION == CHROMA_COLLECTION_BGE else EMBEDDING_MODEL
        self._embeddings = HuggingFaceEmbeddings(
            model_name=_model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        self._vectorstore = Chroma(
            collection_name=ACTIVE_COLLECTION,
            embedding_function=self._embeddings,
            persist_directory=CHROMA_DIR,
        )

        print("[Retriever] Building BM25 index…")
        self._bm25: dict[Optional[str], tuple[BM25Okapi, list[RetrievedChunk]]] = {}
        self._build_bm25_index()

        print("[Retriever] Ready.")

    # ── Public API ────────────────────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        vertical: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> list[RetrievedChunk]:
        """
        Hybrid retrieval: semantic + BM25 → RRF → MMR → source-weight tiebreak.

        Returns RERANK_TOP_K candidates when reranking is enabled so the
        cross-encoder has enough to choose from; otherwise returns TOP_K.
        """
        if top_k is None:
            top_k = RERANK_TOP_K if RERANK_ENABLED else TOP_K

        fetch_k = max(top_k * 3, 30)   # over-fetch for both rankers before fusion
        semantic = self._semantic_query(query_text, vertical, fetch_k)
        bm25     = self._bm25_query(query_text, vertical, fetch_k)
        fused    = self._rrf_merge(semantic, bm25)

        # MMR diversity then source-weight tiebreaking
        diverse  = self._mmr_filter(fused, MMR_LAMBDA, top_k)
        return self._source_weight_sort(diverse)

    def get_document_count(self) -> dict:
        """Return total and per-module chunk counts (used by left panel in app.py)."""
        all_docs = self._vectorstore.get()
        total = len(all_docs.get("ids", []))
        metadatas = all_docs.get("metadatas", [])

        counts = {"total": total}
        for module in CERNER_DIRS:
            counts[module] = sum(
                1 for m in metadatas if m and m.get("vertical") == module
            )
        return counts

    # ── Private: index building ───────────────────────────────────────────────

    def _build_bm25_index(self) -> None:
        all_data = self._vectorstore.get(include=["documents", "metadatas"])
        docs  = all_data.get("documents", []) or []
        metas = all_data.get("metadatas", []) or []

        groups: dict[Optional[str], list[tuple[str, dict]]] = {None: []}
        for doc, meta in zip(docs, metas):
            m = meta or {}
            v = m.get("vertical")
            groups.setdefault(v, []).append((doc, m))
            groups[None].append((doc, m))

        for key, items in groups.items():
            if not items:
                continue
            tokenized = [d.lower().split() for d, _ in items]
            chunks = [
                RetrievedChunk(
                    text=d,
                    source=m.get("source", "unknown"),
                    vertical=m.get("vertical", "unknown"),
                    score=0.0,
                    source_weight=float(m.get("source_weight", 0.5)),
                    doc_type=m.get("doc_type", "community"),
                    priority_tier=m.get("priority_tier", "nice"),
                    source_quality=m.get("source_quality", "secondary"),
                )
                for d, m in items
            ]
            self._bm25[key] = (BM25Okapi(tokenized), chunks)

    # ── Private: retrieval ────────────────────────────────────────────────────

    def _semantic_query(
        self, query_text: str, vertical: Optional[str], top_k: int
    ) -> list[RetrievedChunk]:
        where_filter = self._build_filter(vertical)
        results = self._vectorstore.similarity_search_with_relevance_scores(
            query=query_text,
            k=top_k,
            filter=where_filter,
        )
        chunks = [
            RetrievedChunk(
                text=doc.page_content,
                source=doc.metadata.get("source", "unknown"),
                vertical=doc.metadata.get("vertical", "unknown"),
                score=round(score, 4),
                source_weight=float(doc.metadata.get("source_weight", 0.5)),
                doc_type=doc.metadata.get("doc_type", "community"),
                priority_tier=doc.metadata.get("priority_tier", "nice"),
                semantic_score=round(score, 4),
                source_quality=doc.metadata.get("source_quality", "secondary"),
            )
            for doc, score in results
        ]
        chunks.sort(key=lambda c: c.score, reverse=True)
        return chunks

    def _bm25_query(
        self, query_text: str, vertical: Optional[str], top_k: int
    ) -> list[RetrievedChunk]:
        key = vertical if vertical in self._bm25 else None
        if key not in self._bm25:
            return []

        bm25, chunks = self._bm25[key]
        scores = bm25.get_scores(query_text.lower().split())

        top_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:top_k]

        return [
            RetrievedChunk(
                text=chunks[i].text,
                source=chunks[i].source,
                vertical=chunks[i].vertical,
                score=round(float(scores[i]), 4),
                source_weight=chunks[i].source_weight,
                doc_type=chunks[i].doc_type,
                priority_tier=chunks[i].priority_tier,
                source_quality=chunks[i].source_quality,
            )
            for i in top_indices
            if scores[i] > 0.0
        ]

    # ── Private: fusion ───────────────────────────────────────────────────────

    @staticmethod
    def _rrf_merge(
        semantic: list[RetrievedChunk],
        bm25: list[RetrievedChunk],
        k: int = 60,
    ) -> list[RetrievedChunk]:
        """Reciprocal Rank Fusion: score = Σ 1/(k + rank + 1)."""
        rrf_scores: dict[str, float] = {}
        chunk_map:  dict[str, RetrievedChunk] = {}
        sem_scores: dict[str, float] = {}  # track best semantic score per chunk

        for rank, chunk in enumerate(semantic):
            # Use text[:200] to reduce hash collisions between chunks sharing a common prefix
            key = f"{chunk.source}|||{chunk.text[:200]}"
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            sem_scores[key] = max(sem_scores.get(key, 0.0), chunk.semantic_score)
            chunk_map[key] = chunk

        for rank, chunk in enumerate(bm25):
            key = f"{chunk.source}|||{chunk.text[:200]}"
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            if key not in chunk_map:
                chunk_map[key] = chunk

        sorted_keys = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)
        return [
            RetrievedChunk(
                text=chunk_map[key].text,
                source=chunk_map[key].source,
                vertical=chunk_map[key].vertical,
                score=round(rrf_scores[key], 6),
                source_weight=chunk_map[key].source_weight,
                doc_type=chunk_map[key].doc_type,
                priority_tier=chunk_map[key].priority_tier,
                semantic_score=round(sem_scores.get(key, 0.0), 4),
                source_quality=chunk_map[key].source_quality,
            )
            for key in sorted_keys
        ]

    # ── Private: MMR diversity ────────────────────────────────────────────────

    @staticmethod
    def _jaccard(a: str, b: str) -> float:
        """Token-level Jaccard similarity between two text strings."""
        sa = set(a.lower().split())
        sb = set(b.lower().split())
        if not sa and not sb:
            return 1.0
        return len(sa & sb) / len(sa | sb)

    @classmethod
    def _mmr_filter(
        cls,
        candidates: list[RetrievedChunk],
        lambda_param: float,
        top_k: int,
    ) -> list[RetrievedChunk]:
        """
        Maximal Marginal Relevance: greedily pick chunks that balance
        relevance and diversity.
        λ=1.0 → pure relevance order; λ=0.0 → maximum diversity.
        """
        if lambda_param >= 1.0 or len(candidates) <= top_k:
            return candidates[:top_k]

        selected: list[RetrievedChunk] = [candidates[0]]
        remaining = list(candidates[1:])

        while len(selected) < top_k and remaining:
            best_idx = 0
            best_mmr = float("-inf")

            for i, cand in enumerate(remaining):
                rel = cand.score
                max_sim = max(cls._jaccard(cand.text, s.text) for s in selected)
                mmr = lambda_param * rel - (1.0 - lambda_param) * max_sim
                if mmr > best_mmr:
                    best_mmr = mmr
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    # ── Private: source-weight tiebreaking ────────────────────────────────────

    @staticmethod
    def _source_weight_sort(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """
        Secondary sort by source_weight within 0.05-wide score bands.
        Chunks in the same 0.05 floor bucket are ordered by source_weight desc.
        """
        return sorted(
            chunks,
            key=lambda c: (int(c.score / 0.05), c.source_weight),
            reverse=True,
        )

    # ── Private: helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _build_filter(vertical: Optional[str]) -> Optional[dict]:
        if vertical is None:
            return None
        v = vertical.lower()
        if v in CERNER_DIRS:
            return {"vertical": {"$eq": v}}
        return None


# ── Standalone test ───────────────────────────────────────────────────────────

def _test():
    retriever = HealthcareRetriever()

    counts = retriever.get_document_count()
    print(f"\nStore contains {counts['total']} total chunks")
    for module in CERNER_DIRS:
        print(f"  {module:<16}: {counts.get(module, 0)} chunks")
    print()

    test_cases = [
        ("How do I configure PowerChart patient lists?",    "powerchart"),
        ("What is the Cerner FHIR R4 authorization flow?",  "fhir"),
        ("How does charge capture work in Revenue Cycle?",  "revenue_cycle"),
        ("Explain the Millennium domain architecture",       None),
    ]

    for query_text, vertical in test_cases:
        label = vertical if vertical else "all modules"
        print("-" * 60)
        print(f"Query  : {query_text}")
        print(f"Module : {label}")
        results = retriever.query(query_text, vertical=vertical, top_k=3)
        for i, chunk in enumerate(results, 1):
            print(f"  [{i}] rrf={chunk.score:.6f}  sw={chunk.source_weight}  "
                  f"source={chunk.source}  module={chunk.vertical}")
            print(f"      {chunk.text[:120].strip()}…")
        print()


if __name__ == "__main__":
    _test()
