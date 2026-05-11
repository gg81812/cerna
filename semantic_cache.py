"""
semantic_cache.py — Semantic similarity cache for Cerna.

Returns a cached high-confidence response when the incoming query is
semantically similar to a recent query in the same Cerner module.
Only caches responses with response_mode="high" (retrieval score ≥ 0.7,
no citation warning, no archival sources) — avoids propagating uncertainty.

Algorithm:
  check:  embed query → compare cosine similarity against recent module queries
          → hit if best_sim > SEMANTIC_CACHE_THRESHOLD and cached mode == "high"
  store:  on successful high-confidence generation, store embedding + response

Redis key scheme (all with SEMANTIC_CACHE_TTL, default 6 h):
  sem_cache:emb:<q_hash>         → JSON float list (1024-dim embedding)
  sem_cache:resp:<q_hash>        → JSON response string
  sem_cache:module:<module>      → sorted set; score=Unix timestamp, member=q_hash
                                   trimmed to SEMANTIC_RECENT_LIMIT entries

Module isolation: queries from different Cerner modules are never compared.
Redis dependency: if Redis is unavailable, check() returns None (miss),
                  store() is a no-op. Zero crashes on Redis absence.

Environment variables:
  SEMANTIC_CACHE_THRESHOLD   default 0.85 — tune with eval/tune_semantic_threshold.py
  SEMANTIC_RECENT_LIMIT      default 50   — max recent queries per module to compare
  SEMANTIC_CACHE_TTL         default 21600 (6 h)
  CACHE_BACKEND              must be "redis" to activate semantic cache
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from typing import Optional

_THRESHOLD: float = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.85"))
_RECENT_LIMIT: int = int(os.getenv("SEMANTIC_RECENT_LIMIT", "50"))
_TTL: int = int(os.getenv("SEMANTIC_CACHE_TTL", str(6 * 3600)))
_CACHE_BACKEND: str = os.getenv("CACHE_BACKEND", "memory").lower()

_embed_model = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer("BAAI/bge-large-en-v1.5")
    return _embed_model


def _get_redis():
    if _CACHE_BACKEND != "redis":
        return None
    try:
        from redis_client import get_redis_client
        return get_redis_client()
    except Exception:
        return None


def _query_hash(query: str, module: str) -> str:
    try:
        from pii_guard import mask_pii
        safe = mask_pii(query.strip().lower())
    except Exception:
        safe = query.strip().lower()
    raw = json.dumps({"q": safe, "module": module}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _embed(text: str) -> list[float]:
    model = _get_embed_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _emb_key(q_hash: str) -> str:
    return f"sem_cache:emb:{q_hash}"


def _resp_key(q_hash: str) -> str:
    return f"sem_cache:resp:{q_hash}"


def _module_set_key(module: str) -> str:
    return f"sem_cache:module:{module}"


# ── Public API ────────────────────────────────────────────────────────────────

def check(query: str, module: str) -> Optional[tuple[dict, list[float]]]:
    """
    Check the semantic cache for a similar query.
    Returns (response_dict, query_embedding) on hit, or None on miss.
    The embedding is returned so the caller can reuse it for store().
    """
    r = _get_redis()
    if r is None:
        return None

    module = module or "GENERAL"
    set_key = _module_set_key(module)

    # Fetch recent query hashes for this module (ordered by recency)
    try:
        members = r.zrange(set_key, 0, -1)
    except Exception:
        return None

    if not members:
        return None

    # Compute embedding for incoming query
    try:
        query_vec = _embed(query)
    except Exception:
        return None

    # Batch fetch stored embeddings (one pipeline round-trip)
    try:
        pipe = r.pipeline()
        for qhash in members:
            pipe.get(_emb_key(qhash))
        raw_embs = pipe.execute()
    except Exception:
        return None

    # Find the best cosine-similarity match above threshold
    best_sim = 0.0
    best_hash = None
    for qhash, raw_emb in zip(members, raw_embs):
        if raw_emb is None:
            continue
        try:
            stored_vec = json.loads(raw_emb)
            sim = _cosine_sim(query_vec, stored_vec)
            if sim > best_sim:
                best_sim = sim
                best_hash = qhash
        except Exception:
            continue

    if best_sim < _THRESHOLD or best_hash is None:
        return None

    # Retrieve the cached response
    try:
        resp_raw = r.get(_resp_key(best_hash))
    except Exception:
        return None

    if resp_raw is None:
        return None

    try:
        resp = json.loads(resp_raw)
    except Exception:
        return None

    if resp.get("response_mode") != "high":
        return None

    return resp, query_vec


def store(query: str, module: str, response: dict, query_vec: Optional[list[float]] = None) -> None:
    """
    Store a high-confidence response in the semantic cache.
    Only stores if response_mode == "high". No-op if Redis is unavailable.
    query_vec is accepted to avoid recomputing the embedding (pass from check()).
    """
    if response.get("response_mode") != "high":
        return

    r = _get_redis()
    if r is None:
        return

    module = module or "GENERAL"
    q_hash = _query_hash(query, module)
    set_key = _module_set_key(module)

    try:
        if query_vec is None:
            query_vec = _embed(query)

        pipe = r.pipeline()
        pipe.setex(_emb_key(q_hash), _TTL, json.dumps(query_vec))
        pipe.setex(_resp_key(q_hash), _TTL, json.dumps(response))
        pipe.zadd(set_key, {q_hash: time.time()})
        pipe.expire(set_key, _TTL)
        # Trim to most recent N entries
        pipe.zremrangebyrank(set_key, 0, -((_RECENT_LIMIT + 1)))
        pipe.execute()
    except Exception:
        pass


# ── Pipeline step functions ───────────────────────────────────────────────────

def step_semantic_cache_check(state: dict) -> dict:
    """
    Pipeline step: check semantic cache before retrieval.
    On hit: sets state["response"] and state["semantic_cache_hit"] = True.
    On miss or Redis unavailable: returns state unchanged.
    Stores query_embedding in state for reuse by step_semantic_cache_store.
    """
    module = state.get("classification", "GENERAL")
    query = state.get("formal_query") or state.get("original_query", "")

    result = check(query, module)
    if result is None:
        return {**state, "semantic_cache_hit": False}

    resp, query_vec = result
    return {
        **state,
        "semantic_cache_hit": True,
        "response": resp,
        "sources": [],
        "query_embedding": query_vec,
    }


def step_semantic_cache_store(state: dict) -> dict:
    """
    Pipeline step: store a new high-confidence response in the semantic cache.
    Pass-through: returns state unchanged after storing (or skipping).
    """
    if state.get("semantic_cache_hit"):
        return state

    resp = state.get("response")
    if not resp or resp.get("response_mode") != "high":
        return state

    module = state.get("classification", "GENERAL")
    query = state.get("formal_query") or state.get("original_query", "")
    query_vec = state.get("query_embedding")  # may be None if check() was skipped

    store(query, module, resp, query_vec)
    return state
