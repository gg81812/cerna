"""Test BGE collection via a direct retrieval, not count()."""
import os
import sys
print("[1] starting")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from config import CHROMA_DIR
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

print("[2] loading BGE embeddings...")
emb = HuggingFaceEmbeddings(
    model_name="BAAI/bge-large-en-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)
print("[3] BGE loaded")

print("[4] opening cerner_docs_bge via langchain Chroma wrapper...")
store = Chroma(
    collection_name="cerner_docs_bge",
    embedding_function=emb,
    persist_directory=CHROMA_DIR,
)
print("[5] store opened")

print("[6] running similarity_search 'What is FHIR?'")
docs = store.similarity_search("What is FHIR?", k=3)
print(f"[7] got {len(docs)} hits")
for i, d in enumerate(docs):
    src = (d.metadata or {}).get("source", "?")
    print(f"  [{i}] source={src}")
    print(f"      content[:200]={d.page_content[:200].replace(chr(10),' ')!r}")

print("[done]")
