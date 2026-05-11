"""
scripts/ingest_bge_v2.py — CPU-friendly BGE re-embed with resume support.

Phase 2 cleanup (2026-05-07): the original ingest_bge.py stalled at 704/2,653
chunks on this CPU-only laptop after ~40 min, with degrading per-batch rate.
This v2 addresses the suspected causes:

  1. Smaller batches (16 not 64) — each Chroma write is small enough to
     persist quickly; less memory pressure across BGE encoder + Chroma write.
  2. Explicit gc.collect() between batches — releases intermediate tensors.
  3. torch.no_grad() context — avoids autograd graph accumulation.
  4. Periodic persist() every N batches — flushes Chroma writes to disk so
     SQLite doesn't grow an unbounded WAL.
  5. Newline progress output (not \\r) — visible in piped stdout.
  6. Resume mode (--resume): if cerner_docs_bge already has K chunks, skip
     the first K from the source collection and only embed the remainder.
     Lets a partial run be picked up rather than restarted from scratch.
  7. --batch-size and --persist-every CLI flags for tuning.

Usage:
    python scripts/ingest_bge_v2.py                       # fresh start (deletes existing BGE chunks)
    python scripts/ingest_bge_v2.py --resume              # pick up where prior run left off
    python scripts/ingest_bge_v2.py --batch-size 8        # for tighter memory pressure
"""

from __future__ import annotations

import argparse
import gc
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def _persist(store: Chroma) -> None:
    if hasattr(store, "persist"):
        try:
            store.persist()
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--persist-every", type=int, default=8,
                        help="Call persist() every N batches.")
    parser.add_argument("--resume", action="store_true",
                        help="Skip chunks already in BGE collection (don't delete).")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max chunks to embed (for testing).")
    args = parser.parse_args()

    print("=" * 60)
    print("Cerna - BGE re-embed v2 (Phase 2 cleanup)")
    print("=" * 60)
    print(f"Source collection : {CHROMA_COLLECTION}  (MiniLM)")
    print(f"Target collection : {CHROMA_COLLECTION_BGE}  (BGE-large)")
    print(f"Chroma store      : {CHROMA_DIR}")
    print(f"Batch size        : {args.batch_size}")
    print(f"Persist every     : {args.persist_every} batches")
    print(f"Resume mode       : {args.resume}")

    if not os.path.isdir(CHROMA_DIR):
        print("\n[ERROR] chroma_store not found. Run `python ingest.py` first.")
        sys.exit(1)

    # ---- 1. Load source chunks (MiniLM collection) ----
    print("\n[1/4] Loading source chunks from MiniLM collection...")
    mini_emb = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    source_store = Chroma(
        collection_name=CHROMA_COLLECTION,
        embedding_function=mini_emb,
        persist_directory=CHROMA_DIR,
    )
    src = source_store.get(include=["documents", "metadatas"])
    src_ids = src.get("ids", []) or []
    src_docs = src.get("documents", []) or []
    src_metas = src.get("metadatas", []) or []
    n_src = len(src_docs)
    print(f"  Loaded {n_src} chunks from {CHROMA_COLLECTION}")
    if n_src == 0:
        print("[ERROR] Source collection empty. Aborting.")
        sys.exit(1)

    # Free the MiniLM model — we no longer need it
    del mini_emb, source_store
    gc.collect()

    # ---- 2. Load BGE model ----
    print(f"\n[2/4] Loading BGE model: {EMBEDDING_MODEL_BGE}")
    bge_emb = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_BGE,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True, "batch_size": args.batch_size},
    )
    print("  BGE model ready.")

    # ---- 3. Open / clear / probe BGE collection ----
    print(f"\n[3/4] Preparing BGE collection: {CHROMA_COLLECTION_BGE}")
    bge_store = Chroma(
        collection_name=CHROMA_COLLECTION_BGE,
        embedding_function=bge_emb,
        persist_directory=CHROMA_DIR,
    )
    existing = bge_store.get()
    n_existing = len(existing.get("ids", []) or [])

    if args.resume:
        print(f"  Resume mode: keeping {n_existing} existing chunks; will append the remainder.")
        # Skip the first n_existing source chunks (assumes deterministic order from get())
        skip = n_existing
    else:
        if n_existing:
            print(f"  Clearing {n_existing} existing chunks for fresh start...")
            bge_store.delete(existing["ids"])
            _persist(bge_store)
        skip = 0

    todo_docs = src_docs[skip:]
    todo_metas = src_metas[skip:]
    if args.limit:
        todo_docs = todo_docs[: args.limit]
        todo_metas = todo_metas[: args.limit]

    n_todo = len(todo_docs)
    print(f"  Chunks remaining to embed: {n_todo}")
    if n_todo == 0:
        print("  Nothing to do. Done.")
        return

    # ---- 4. Embed in batches ----
    print(f"\n[4/4] Embedding {n_todo} chunks (batch={args.batch_size}, persist every {args.persist_every})...")
    t_start = time.time()
    batch_count = 0
    n_done = 0

    with torch.no_grad():
        for i in range(0, n_todo, args.batch_size):
            t_b = time.time()
            doc_batch = todo_docs[i : i + args.batch_size]
            meta_batch = todo_metas[i : i + args.batch_size]
            lc_batch = [
                Document(page_content=d, metadata=m or {})
                for d, m in zip(doc_batch, meta_batch)
            ]
            bge_store.add_documents(lc_batch)
            n_done += len(lc_batch)
            batch_count += 1

            elapsed = time.time() - t_start
            batch_dt = time.time() - t_b
            rate = n_done / elapsed if elapsed > 0 else 0
            eta_min = (n_todo - n_done) / rate / 60 if rate > 0 else float("inf")
            print(
                f"  [{n_done:5d}/{n_todo}] batch={batch_count} "
                f"dt={batch_dt:5.1f}s rate={rate:4.1f}/s "
                f"elapsed={elapsed/60:5.1f}m eta={eta_min:5.1f}m",
                flush=True,
            )

            # Periodic persist + gc
            if batch_count % args.persist_every == 0:
                _persist(bge_store)
                gc.collect()

    # Final flush
    _persist(bge_store)
    gc.collect()

    final_count = bge_store._collection.count() if hasattr(bge_store, "_collection") else None
    print("\n" + "=" * 60)
    print("BGE re-embed complete.")
    print(f"  Embedded this run : {n_done}")
    print(f"  Total in BGE coll : {final_count if final_count is not None else 'unknown'}")
    print(f"  Source had        : {n_src}")
    print(f"  Wall time         : {(time.time() - t_start) / 60:.1f} min")
    print("=" * 60)


if __name__ == "__main__":
    main()
