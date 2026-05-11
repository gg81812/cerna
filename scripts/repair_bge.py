"""
scripts/repair_bge.py — Rebuild cerner_docs_bge from cerner_docs in a single
add_documents call (not batched). The previous 16-chunk batched ingest left
the HNSW index in a bad state on Windows (segfaults on count/query).

Pulls all chunks + metadata from cerner_docs (MiniLM), generates BGE
embeddings, and writes them to a fresh cerner_docs_bge collection in one
shot.

Usage:
    python scripts/repair_bge.py
"""

from __future__ import annotations

import gc
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from config import (
    CHROMA_DIR,
    CHROMA_COLLECTION,
    CHROMA_COLLECTION_BGE,
    EMBEDDING_MODEL_BGE,
)


def main() -> None:
    print("=" * 60)
    print("Cerna - BGE repair (rebuild HNSW from scratch)")
    print("=" * 60)

    # Step 1: Drop the BGE collection entirely (handles segment folder cleanup).
    print("\n[1/5] Dropping cerner_docs_bge via Chroma client (no read needed)...")
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(CHROMA_COLLECTION_BGE)
        print("  Deleted cerner_docs_bge.")
    except Exception as e:
        print(f"  delete_collection raised: {type(e).__name__}: {e}")
        print("  (Continuing — collection may not exist yet.)")
    del client
    gc.collect()

    # Step 2: Load source chunks from cerner_docs (MiniLM) using a separate client
    print("\n[2/5] Loading source chunks from cerner_docs (MiniLM)...")
    mini_emb = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    src = Chroma(
        collection_name=CHROMA_COLLECTION,
        embedding_function=mini_emb,
        persist_directory=CHROMA_DIR,
    )
    raw = src.get(include=["documents", "metadatas"])
    docs = raw.get("documents", []) or []
    metas = raw.get("metadatas", []) or []
    print(f"  Loaded {len(docs)} chunks.")
    if not docs:
        print("[ERROR] Source empty. Aborting.")
        sys.exit(1)
    del src, mini_emb
    gc.collect()

    # Step 3: Load BGE embedding model
    print(f"\n[3/5] Loading BGE model: {EMBEDDING_MODEL_BGE}")
    bge_emb = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_BGE,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
    )
    print("  BGE ready.")

    # Step 4: Pre-encode all embeddings up front (one big inference pass)
    # This decouples expensive embedding from Chroma's HNSW write so we can
    # add them in a single bulk write below.
    print(f"\n[4/5] Pre-encoding {len(docs)} chunks with BGE (single pass)...")
    t0 = time.time()
    with torch.no_grad():
        vectors = bge_emb.embed_documents(docs)
    enc_min = (time.time() - t0) / 60
    print(f"  Encoded {len(vectors)} vectors in {enc_min:.1f} min "
          f"(dim={len(vectors[0])}).")

    # Step 5: Bulk-add to a fresh Chroma collection in a single call.
    print(f"\n[5/5] Bulk-adding {len(vectors)} embeddings to {CHROMA_COLLECTION_BGE}...")
    # Use raw chromadb client to write embeddings directly (skip langchain wrapper
    # for the write — avoids langchain re-embedding).
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    coll = client.get_or_create_collection(
        name=CHROMA_COLLECTION_BGE,
        metadata={"hnsw:space": "cosine"},
    )
    ids = [f"bge_{i}" for i in range(len(docs))]
    # Chroma can't accept None metadata values, so coerce
    safe_metas = [{k: (v if v is not None else "") for k, v in (m or {}).items()} for m in metas]
    t1 = time.time()
    coll.add(
        ids=ids,
        embeddings=vectors,
        documents=docs,
        metadatas=safe_metas,
    )
    write_min = (time.time() - t1) / 60
    print(f"  Bulk write complete in {write_min:.1f} min.")

    # Verify
    print("\n--- Verifying ---")
    n = coll.count()
    print(f"  cerner_docs_bge: {n} chunks")
    print(f"  Total wall: {(time.time() - t0) / 60:.1f} min (encode + write)")
    print("=" * 60)


if __name__ == "__main__":
    main()
