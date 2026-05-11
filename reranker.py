"""
reranker.py — Cross-encoder reranker using BAAI/bge-reranker-v2-m3.

Fetches RERANK_TOP_K candidates from retrieval, scores each (query, chunk) pair
with the cross-encoder, and returns the top FINAL_TOP_K highest-scoring chunks.

Download note: BAAI/bge-reranker-v2-m3 is ~570 MB on first run.
Subsequent runs use the local HuggingFace cache.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from config import RERANK_ENABLED, FINAL_TOP_K

if TYPE_CHECKING:
    from retriever import RetrievedChunk

_model = None   # lazy-loaded singleton


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder(
            "BAAI/bge-reranker-v2-m3",
            device="cpu",
            max_length=512,
        )
    return _model


def rerank(query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """
    Score every (query, chunk) pair and return the top FINAL_TOP_K chunks.

    When RERANK_ENABLED is False or the list is already ≤ FINAL_TOP_K,
    returns the input list trimmed to FINAL_TOP_K (no model call).
    Attaches `rerank_score` to each returned chunk's score field.
    """
    if not chunks:
        return chunks

    if not RERANK_ENABLED or len(chunks) <= FINAL_TOP_K:
        return chunks[:FINAL_TOP_K]

    model = _get_model()
    pairs = [(query, chunk.text) for chunk in chunks]
    scores = model.predict(pairs, show_progress_bar=False)

    scored = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
    top = []
    for raw_score, chunk in scored[:FINAL_TOP_K]:
        chunk.score = round(float(raw_score), 4)
        top.append(chunk)

    return top
