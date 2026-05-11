"""
scripts/ingest_bge.py — Re-embed all chunks into the parallel BGE collection.

Creates `cerner_docs_bge` alongside the existing `cerner_docs` (MiniLM) collection.
Does NOT touch the original collection — safe rollback by switching COLLECTION env var.

Usage:
    python scripts/ingest_bge.py

Switch retriever to BGE collection:
    export COLLECTION=cerner_docs_bge
    streamlit run app.py

Switch back:
    export COLLECTION=cerner_docs          (or unset COLLECTION)
    streamlit run app.py

Download note: BAAI/bge-large-en-v1.5 is ~1.3 GB on first run.
Expected runtime: 15-30 min on CPU for 9,099 chunks.
"""

import os
import sys

# Make project root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from config import (
    CHROMA_DIR,
    CHROMA_COLLECTION,
    CHROMA_COLLECTION_BGE,
    EMBEDDING_MODEL_BGE,
)


def main():
    print("=" * 60)
    print("Cerna — BGE-large-en-v1.5 Re-embedding")
    print("=" * 60)
    print(f"\nSource collection : {CHROMA_COLLECTION}  (MiniLM)")
    print(f"Target collection : {CHROMA_COLLECTION_BGE}  (BGE-large)")
    print(f"Chroma store      : {CHROMA_DIR}")

    if not os.path.isdir(CHROMA_DIR):
        print("\n[ERROR] chroma_store not found. Run `python ingest.py` first.")
        sys.exit(1)

    # 1. Load all chunks from the existing MiniLM collection
    print("\n[1/4] Loading existing chunks from MiniLM collection…")
    from langchain_huggingface import HuggingFaceEmbeddings as HFE
    mini_emb = HFE(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    source_store = Chroma(
        collection_name=CHROMA_COLLECTION,
        embedding_function=mini_emb,
        persist_directory=CHROMA_DIR,
    )
    data = source_store.get(include=["documents", "metadatas"])
    docs   = data.get("documents", []) or []
    metas  = data.get("metadatas", []) or []
    print(f"  Loaded {len(docs)} chunks from {CHROMA_COLLECTION}")

    if not docs:
        print("[ERROR] No chunks found in source collection. Aborting.")
        sys.exit(1)

    # 2. Load BGE embedding model
    print(f"\n[2/4] Loading BGE embedding model: {EMBEDDING_MODEL_BGE}")
    print("  (First run downloads ~1.3 GB — subsequent runs use local cache)")
    bge_emb = HFE(
        model_name=EMBEDDING_MODEL_BGE,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    print("  BGE model ready.")

    # 3. Create the BGE collection (clearing any stale version)
    from langchain_core.documents import Document
    print(f"\n[3/4] Creating BGE collection: {CHROMA_COLLECTION_BGE}")
    bge_store = Chroma(
        collection_name=CHROMA_COLLECTION_BGE,
        embedding_function=bge_emb,
        persist_directory=CHROMA_DIR,
    )
    existing = bge_store.get()
    if existing["ids"]:
        print(f"  Clearing {len(existing['ids'])} existing chunks in BGE collection…")
        bge_store.delete(existing["ids"])

    # 4. Batch-embed and store
    print(f"\n[4/4] Embedding {len(docs)} chunks with BGE-large-en-v1.5…")
    print("  This may take 15-30 min on CPU.")

    batch_size = 64
    lc_docs = [
        Document(page_content=doc, metadata=meta or {})
        for doc, meta in zip(docs, metas)
    ]

    for i in range(0, len(lc_docs), batch_size):
        batch = lc_docs[i : i + batch_size]
        bge_store.add_documents(batch)
        pct = min(100, int((i + len(batch)) / len(lc_docs) * 100))
        print(f"  {i + len(batch)}/{len(lc_docs)} chunks embedded  ({pct}%)", end="\r")

    if hasattr(bge_store, "persist"):
        bge_store.persist()

    print(f"\n\n{'=' * 60}")
    print("BGE re-embedding complete!")
    print(f"  Chunks in BGE collection : {len(lc_docs)}")
    print(f"  Collection name          : {CHROMA_COLLECTION_BGE}")
    print(f"  Store path               : {CHROMA_DIR}")
    print(f"\nTo use BGE collection:")
    print(f"  Windows:  set COLLECTION=cerner_docs_bge && streamlit run app.py")
    print(f"  Linux/Mac: COLLECTION=cerner_docs_bge streamlit run app.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
