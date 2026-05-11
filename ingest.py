"""
ingest.py — Load, chunk, embed, and store Cerner documents into ChromaDB.

Run once (or whenever the document corpus changes):
    python ingest.py

What it does:
1. Loads scripts/doc_manifest.json (produced by scripts/tag_documents.py)
2. Loads all .txt and .md files from each data/[module]/ folder
3. Skips placeholder files (containing "PLACEHOLDER — MANUAL DOWNLOAD REQUIRED")
4. Splits documents using type-aware structural chunking:
   - Reference docs (FHIR spec, doc_type="spec"):
       RecursiveChar at heading boundaries (600 chars / 50 overlap)
   - Workflow docs (eMAR, CPOE, build guides — step-heavy):
       RecursiveChar with heading+paragraph separators (1500 chars / 100 overlap)
   - Prose docs (overviews, architecture, blog):
       RecursiveChar paragraph-first (1000 chars / 150 overlap)
5. Prepends "# [title] | Module: [module]" to every chunk for context
6. Tags every chunk with: source, vertical, doc_source, doc_type,
   priority_tier, source_weight, last_updated, title
7. Embeds with all-MiniLM-L6-v2 (local, no API calls)
8. Persists to ./chroma_store/ under the "cerner_docs" collection
"""

import json
import os
import re
import sys
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False

from config import (
    CERNER_DIRS,
    CHROMA_COLLECTION,
    CHROMA_DIR,
    EMBEDDING_MODEL,
    CHUNK_SIZE_PROSE,
    CHUNK_SIZE_WORKFLOW,
    CHUNK_SIZE_REFERENCE,
    CHUNK_OVERLAP_PROSE,
    CHUNK_OVERLAP_WORKFLOW,
    CHUNK_OVERLAP_REFERENCE,
    SCRIPTS_DIR,
    INGEST_EXCLUDE,
)

PLACEHOLDER_MARKER = "PLACEHOLDER — MANUAL DOWNLOAD REQUIRED"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(SCRIPTS_DIR, "doc_manifest.json")

# Separators ordered from most structural to least, per chunk strategy
_SEP_REFERENCE = ["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " ", ""]
_SEP_WORKFLOW  = ["\n## ", "\n### ", "\n\n", "\n", " ", ""]
_SEP_PROSE     = ["\n\n", "\n", ". ", " ", ""]

# Filename patterns that indicate workflow/step-heavy docs
_WORKFLOW_PAT = re.compile(
    r"(reconciliation|workflow|charge-capture|emar|bcma|cpoe|"
    r"powerchart-ai|clinical-ai|build|implementation|config|admin|setup)",
    re.IGNORECASE,
)


# ── Manifest ──────────────────────────────────────────────────────────────────

def _load_manifest() -> dict:
    """Load doc_manifest.json; return empty dict if not found."""
    if not os.path.isfile(MANIFEST_PATH):
        print(f"  [WARN] Manifest not found at {MANIFEST_PATH}.")
        print("         Run `python scripts/tag_documents.py` for enriched metadata.")
        return {}
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def _manifest_key(filepath: str) -> str:
    """Convert absolute path to the key format used in the manifest (relative to project root)."""
    return os.path.relpath(filepath, BASE_DIR).replace("\\", "/")


# ── Chunk strategy selection ──────────────────────────────────────────────────

def _select_strategy(doc_type: str, fname: str, content: str) -> str:
    """Return 'reference', 'workflow', or 'prose'."""
    if doc_type == "spec":
        return "reference"
    if _WORKFLOW_PAT.search(fname):
        return "workflow"
    # Content heuristic: ≥5 numbered steps → treat as workflow
    if len(re.findall(r"^\d+\.\s", content, re.MULTILINE)) >= 5:
        return "workflow"
    return "prose"


def _make_splitter(strategy: str) -> RecursiveCharacterTextSplitter:
    if strategy == "reference":
        return RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE_REFERENCE,
            chunk_overlap=CHUNK_OVERLAP_REFERENCE,
            separators=_SEP_REFERENCE,
            length_function=len,
        )
    if strategy == "workflow":
        return RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE_WORKFLOW,
            chunk_overlap=CHUNK_OVERLAP_WORKFLOW,
            separators=_SEP_WORKFLOW,
            length_function=len,
        )
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE_PROSE,
        chunk_overlap=CHUNK_OVERLAP_PROSE,
        separators=_SEP_PROSE,
        length_function=len,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

_HTML_RE = re.compile(r"<[a-zA-Z][^>]{0,200}>")

def _strip_html(text: str) -> str:
    """Strip HTML tags if BeautifulSoup is available and text looks like HTML."""
    if not _BS4_AVAILABLE:
        return re.sub(r"<[^>]+>", " ", text)
    if not _HTML_RE.search(text):
        return text
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    clean = soup.get_text(separator="\n")
    # Collapse excessive blank lines
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()


def is_placeholder(file_path: str) -> bool:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            head = fh.read(512)
        return PLACEHOLDER_MARKER in head
    except OSError:
        return False


def load_module(module_name: str, directory: str, manifest: dict):
    """
    Load all .txt and .md files from `directory`, skipping placeholders and READMEs.
    Tags every document with vertical=module_name plus manifest metadata.
    Returns (docs list, skipped_count).
    """
    if not os.path.isdir(directory):
        print(f"  [WARN] Directory not found, skipping: {directory}")
        return [], 0

    docs = []
    skipped = 0

    for glob_pattern in ("**/*.txt", "**/*.md"):
        loader = DirectoryLoader(
            directory,
            glob=glob_pattern,
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
            show_progress=False,
            use_multithreading=False,
        )
        try:
            loaded = loader.load()
        except Exception as exc:
            print(f"  [WARN] Could not load {glob_pattern} from {directory}: {exc}")
            loaded = []

        for doc in loaded:
            raw_source = doc.metadata.get("source", "")
            fname = Path(raw_source).name
            if fname.lower() == "readme.md":
                continue
            if fname in INGEST_EXCLUDE:
                rel = os.path.relpath(raw_source, BASE_DIR).replace("\\", "/")
                print(f"  [EXCL] {rel} — excluded (synthetic/audit-only)")
                skipped += 1
                continue
            if is_placeholder(raw_source) or PLACEHOLDER_MARKER in doc.page_content[:512]:
                rel = os.path.relpath(raw_source, BASE_DIR).replace("\\", "/")
                print(f"  [SKIP] {rel} — placeholder, manual download required")
                skipped += 1
                continue

            doc.page_content = _strip_html(doc.page_content)
            doc.metadata["source"] = fname
            doc.metadata["vertical"] = module_name

            # Enrich from manifest
            mkey = _manifest_key(raw_source)
            meta = manifest.get(mkey, {})
            doc.metadata["doc_source"]    = meta.get("doc_source",    "third_party")
            doc.metadata["doc_type"]      = meta.get("doc_type",      "community")
            doc.metadata["priority_tier"] = meta.get("priority_tier", "nice")
            doc.metadata["source_weight"] = meta.get("source_weight", 0.5)
            doc.metadata["last_updated"]  = meta.get("last_updated",  "unknown")
            doc.metadata["title"]         = meta.get("title",         fname)
            # source_quality: "archival_secondary" for wiki files, else derived from doc_source
            ds = meta.get("doc_source", "third_party")
            doc.metadata["source_quality"] = (
                "archival_secondary" if ds == "archival_secondary"
                else "primary" if ds in ("official", "oracle_docs", "open_cerner", "ucern")
                else "secondary"
            )

            docs.append(doc)

    return docs, skipped


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_documents(documents: list) -> list:
    """
    Split documents using type-aware structural chunking.
    Prepends "# [title] | Module: [module]" to every chunk for retrieval context.
    """
    all_chunks = []
    strategy_counts = {"reference": 0, "workflow": 0, "prose": 0}

    for doc in documents:
        fname    = doc.metadata.get("source", "")
        module   = doc.metadata.get("vertical", "")
        doc_type = doc.metadata.get("doc_type", "community")
        title    = doc.metadata.get("title", fname)
        content  = doc.page_content

        strategy = _select_strategy(doc_type, fname, content)
        splitter = _make_splitter(strategy)

        raw_chunks = splitter.split_documents([doc])
        prefix = f"# {title} | Module: {module}\n\n"

        for chunk in raw_chunks:
            chunk.page_content = prefix + chunk.page_content
            all_chunks.append(chunk)

        strategy_counts[strategy] += len(raw_chunks)

    return all_chunks, strategy_counts


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Cerna — Document Ingestion")
    print("=" * 60)

    # 0. Load manifest ---------------------------------------------------------
    print(f"\n[0/4] Loading document manifest from {MANIFEST_PATH}…")
    manifest = _load_manifest()
    print(f"  Manifest entries: {len(manifest)}")

    # 1. Load documents --------------------------------------------------------
    print("\n[1/4] Loading documents…")

    all_docs = []
    total_skipped = 0
    module_stats = {}

    for module_name, directory in CERNER_DIRS.items():
        docs, skipped = load_module(module_name, directory, manifest)
        all_docs.extend(docs)
        total_skipped += skipped
        module_stats[module_name] = (len(docs), skipped)

    print(f"\n  Per-module breakdown:")
    for module, (cnt, skp) in module_stats.items():
        status = f"{cnt} real docs"
        if skp:
            status += f", {skp} placeholders skipped"
        print(f"    {module:<16}: {status}")

    print(f"\n  Total real docs   : {len(all_docs)}")
    print(f"  Total skipped     : {total_skipped} (placeholders)")

    if not all_docs:
        print(
            "\n[WARN] No real documents found across all modules.\n"
            "       Add documents to data/[module]/ folders and re-run ingest.py."
        )
    else:
        for module, (cnt, skp) in module_stats.items():
            if cnt == 0 and skp > 0:
                print(
                    f"\n  [ERROR] Module {module}: no real documents — "
                    f"Cerna cannot answer {module} questions until documents are added"
                )

    # 2. Chunk -----------------------------------------------------------------
    print(f"\n[2/4] Chunking documents (structural, type-aware)…")
    print("       reference -> 600/50  |  workflow -> 1500/100  |  prose -> 1000/150")
    chunks, strategy_counts = chunk_documents(all_docs)
    print(f"  Total chunks      : {len(chunks)}")
    print(f"  By strategy       : reference={strategy_counts['reference']}, "
          f"workflow={strategy_counts['workflow']}, prose={strategy_counts['prose']}")

    # 3. Embed -----------------------------------------------------------------
    print(f"\n[3/4] Loading embedding model ({EMBEDDING_MODEL})…")
    print("  (First run downloads ~90 MB — subsequent runs use local cache)")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    print("  Embedding model ready.")

    # 4. Store in ChromaDB -----------------------------------------------------
    print(f"\n[4/4] Storing chunks in ChromaDB at: {CHROMA_DIR}")
    print(f"      Collection: {CHROMA_COLLECTION}")

    # Delete only the target collection — leave other collections (e.g. cerner_docs_bge) intact.
    import chromadb
    if os.path.exists(CHROMA_DIR):
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
        existing_names = [c.name for c in _client.list_collections()]
        if CHROMA_COLLECTION in existing_names:
            _client.delete_collection(CHROMA_COLLECTION)
            print(f"  Cleared collection '{CHROMA_COLLECTION}' (other collections preserved).")
        del _client

    if chunks:
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=CHROMA_DIR,
            collection_name=CHROMA_COLLECTION,
        )
        if hasattr(vectorstore, "persist"):
            vectorstore.persist()
    else:
        Chroma(
            collection_name=CHROMA_COLLECTION,
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR,
        )
        print("  Empty store created (no documents to embed).")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Ingestion complete!")
    print(f"  Documents ingested : {len(all_docs)}")
    print(f"  Chunks stored      : {len(chunks)}")
    print(f"  Vector store path  : {CHROMA_DIR}")
    print(f"  Collection         : {CHROMA_COLLECTION}")
    print("=" * 60)
    print("\nRun `python scripts/tag_documents.py` first to refresh metadata.")
    print("Then run `streamlit run app.py` to start the app.")


if __name__ == "__main__":
    main()
