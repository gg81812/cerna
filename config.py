"""
config.py — Central configuration for Cerna, the Cerner AI specialist assistant.
Loads environment variables and defines all shared constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY is not set. Add it to your .env file."
    )

# ── LLM ───────────────────────────────────────────────────────────────────────
GROQ_MODEL: str          = "llama-3.3-70b-versatile"   # main model (128k ctx)
GROQ_MODEL_FAST: str     = "llama-3.1-8b-instant"      # cheap model for classify/rewrite/safety
LLM_TEMPERATURE: float   = 0.15                         # low temperature for factual consistency across runs

# ── Prompt versioning ─────────────────────────────────────────────────────────
PROMPT_VERSION: str = "2.1.0"

# ── Embeddings ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL: str     = "all-MiniLM-L6-v2"          # legacy (384-dim) — use for cerner_docs
EMBEDDING_MODEL_BGE: str = "BAAI/bge-large-en-v1.5"    # upgraded (1024-dim) — use for cerner_docs_bge

# ── ChromaDB collections ──────────────────────────────────────────────────────
CHROMA_COLLECTION: str     = "cerner_docs"              # MiniLM collection (baseline)
CHROMA_COLLECTION_BGE: str = "cerner_docs_bge"          # BGE collection (upgraded)
# Flip between collections without code changes: export COLLECTION=cerner_docs_bge
ACTIVE_COLLECTION: str = os.getenv("COLLECTION", CHROMA_COLLECTION)

# ── Retrieval ─────────────────────────────────────────────────────────────────
TOP_K: int              = 5     # final chunks passed to LLM
RERANK_ENABLED: bool    = os.getenv("RERANK_ENABLED", "false").lower() == "true"
RERANK_TOP_K: int       = 10    # candidates fetched before reranking
FINAL_TOP_K: int        = 4     # top N kept after reranking
MMR_LAMBDA: float       = float(os.getenv("MMR_LAMBDA", "0.7"))  # 0=diversity, 1=relevance

# ── Query expansion ───────────────────────────────────────────────────────────
HYDE_ENABLED: bool = os.getenv("HYDE_ENABLED", "false").lower() == "true"

# ── Chunking (structural, per doc type) ───────────────────────────────────────
# Sizes in characters (≈4 chars/token)
CHUNK_SIZE_PROSE: int      = 1000   # FHIR overviews, platform architecture
CHUNK_SIZE_WORKFLOW: int   = 1500   # eMAR, CPOE — keep full step blocks intact
CHUNK_SIZE_REFERENCE: int  = 600    # FHIR resource pages — one section per chunk
CHUNK_OVERLAP_PROSE: int   = 150
CHUNK_OVERLAP_WORKFLOW: int= 100
CHUNK_OVERLAP_REFERENCE: int = 50

# ── Safety ────────────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD: float = 0.27  # minimum semantic cosine score for a confident answer
                                    # (all-MiniLM-L6-v2 typical in-domain matches score 0.27-0.65)
                                    # Lowered from 0.35: brand-name product queries (RevElate, etc.)
                                    # score 0.27-0.30; safety classifier blocks true OOS queries
CONFIDENCE_THRESHOLD_GENERAL: float = 0.18  # lower threshold for GENERAL queries (e.g. "what is cerner")
                                             # broad overview questions score lower vs. specific technical docs
CITATION_SCORE_THRESHOLD: float = 0.50  # clinical/FHIR/RCM queries require this semantic score
DID_YOU_MEAN_THRESHOLD: float = 0.40    # below this after multi-query retrieval → surface "did you mean"
                                         # suggestions instead of a low-confidence guess

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR: str  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR: str  = os.path.join(BASE_DIR, "data")
CHROMA_DIR: str = os.path.join(BASE_DIR, "chroma_store")
LOG_DIR: str   = os.path.join(BASE_DIR, "logs")
LOG_FILE: str  = os.path.join(LOG_DIR, "query_log.jsonl")
SCRIPTS_DIR: str = os.path.join(BASE_DIR, "scripts")

# ── Cerner Modules ────────────────────────────────────────────────────────────
CERNER_MILLENNIUM: str    = "millennium"
CERNER_POWERCHART: str    = "powerchart"
CERNER_REVENUE_CYCLE: str = "revenue_cycle"
CERNER_FHIR: str          = "fhir"
CERNER_CLINICAL: str      = "clinical"
CERNER_GENERAL: str       = "GENERAL"

CERNER_DIRS: dict = {
    "millennium":    os.path.join(DATA_DIR, "millennium"),
    "powerchart":    os.path.join(DATA_DIR, "powerchart"),
    "revenue_cycle": os.path.join(DATA_DIR, "revenue_cycle"),
    "fhir":          os.path.join(DATA_DIR, "fhir"),
    "clinical":      os.path.join(DATA_DIR, "clinical"),
}

VALID_CLASSIFICATIONS: tuple = (
    "MILLENNIUM", "POWERCHART", "REVENUE_CYCLE", "FHIR", "CLINICAL", "GENERAL"
)

# ── Conversation History ───────────────────────────────────────────────────────
MAX_HISTORY_EXCHANGES: int = 6   # last N user/assistant pairs (query rewriter uses all 6)

# ── Ingest exclusion list ─────────────────────────────────────────────────────
# Files excluded from ingest — kept on disk for audit, never embedded.
# Reason: explicitly AI-generated synthetic content (SYNTHETIC KNOWLEDGE BASE marker).
# To re-include a file, remove its basename from this set and re-run ingest.
INGEST_EXCLUDE: frozenset = frozenset({
    # FHIR
    "fhir-developer-program-guide.txt",
    # Millennium
    "millennium-code-sets-guide.txt",
    "millennium-ccl-performance-tuning.txt",
    "millennium-discern-rules-engine.txt",
    # PowerChart
    "powerchart-ai-integration-context.txt",
    "powerchart-ai-predictive-ordering.txt",
    "powerchart-cpoe-alert-configuration.txt",
    "powerchart-hl7-lab-integration.txt",
    "powerchart-order-sets-cpoe-config.txt",
    # Clinical
    "clinical-firstnet-ed-tracking.txt",
    "clinical-surginet-perioperative.txt",
    # Wiki spot-check: B3-suspect (HIGH_ALERT_MED/TOPICAL flag values unverifiable)
    "clinical-bcma-barcode-admin-guide.txt",
})
