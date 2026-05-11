"""
state.py — Explicit, fully-serialisable state container for the Cerna pipeline.

CernaState is a TypedDict that accumulates every piece of data produced or consumed
during a single request. It is the exact shape a LangGraph StateGraph expects —
migrating means replacing build_pipeline() with StateGraph(CernaState) and wiring
the same step functions as nodes (zero changes to step code).

Serialisation contract
----------------------
Every field must round-trip through json.dumps / json.loads with no loss.
  - No LangChain objects (ChatGroq, BaseChatModel, VectorStore, …)
  - No numpy arrays
  - No dataclass instances — convert to plain dicts at step boundaries
  - RetrievedChunk  ↔  dict  via chunk_to_dict() / dict_to_chunk()
  - CernaResponse   ↔  dict  via .model_dump() / CernaResponse(**d)
"""

from __future__ import annotations

import uuid
from typing import Optional

from typing_extensions import TypedDict


# ── Trace ─────────────────────────────────────────────────────────────────────

class TraceEvent(TypedDict):
    """One instrumentation record written by the @traced decorator per step."""
    step: str            # step function name
    duration_ms: int     # wall-clock milliseconds
    success: bool        # False if an unhandled exception was caught
    input_summary: str   # <= 120 chars describing what went in
    output_summary: str  # <= 120 chars describing what came out
    error: Optional[str] # exception message if success=False, else None


# ── Pipeline State ─────────────────────────────────────────────────────────────

class CernaState(TypedDict):
    """
    Immutable-by-convention dict that flows through every pipeline step.
    Each step receives a CernaState and returns a *new* CernaState via {**state, ...}.

    Field groups correspond 1-to-1 with the nodes in docs/orchestrator_flow.md.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    trace_id: str                    # uuid4 set at pipeline entry

    # ── Input (set by make_initial_state) ─────────────────────────────────────
    original_query: str
    conversation_history: list[dict] # [{"role": "user"|"assistant", "content": str}]
    module_hint: Optional[str]       # UI module filter selected by user; may be None

    # ── Query Understanding  (step_understand) ────────────────────────────────
    intent: str                      # question|troubleshooting|follow_up|
                                     # casual|out_of_scope|clinical_decision
    formal_query: str                # query rewritten and optimised for retrieval
    query_variants: list[str]        # 2 alternative phrasings from the rewriter
    detected_modules: list[str]      # ["FHIR", "CLINICAL", …]
    detected_entities: list[str]     # specific Cerner product names found
    is_ambiguous: bool               # True → trigger HyDE + broader retrieval

    # ── Multi-branch clarification (Phase 1 Item 2) ──────────────────────────
    needs_clarification: bool        # True → short-circuit to step_clarify
    clarification_question: str      # the single clarifying question to render

    # ── Module Routing  (step_classify_module) ────────────────────────────────
    classification: str              # "FHIR"|"CLINICAL"|"GENERAL"|…
    retrieval_vertical: Optional[str]# "fhir"|"clinical"|… or None (cross-module)
    fetch_k: int                     # chunks fetched per retrieval query
    should_hyde: bool                # whether to run HyDE generation

    # ── Pre-retrieval setup  (step_prepare_retrieval) ────────────────────────
    variant1: str                    # query_variants[0] or ""
    variant2: str                    # query_variants[1] or ""
    hyde_doc: str                    # hypothetical document (set after generation)

    # ── Raw Retrieval Results  (step_retrieve) ────────────────────────────────
    raw_result_lists: list[list[dict]]  # serialised RetrievedChunks, one list per query

    # ── Fused & Reranked Chunks  (step_fuse / step_rerank) ───────────────────
    fused_chunks: list[dict]         # after RRF across all retrieval lists
    final_chunks: list[dict]         # after rerank / trim — fed to prompt builder

    # ── Quality Gates  (step_gate) ────────────────────────────────────────────
    low_confidence: bool
    citation_warning: bool
    did_you_mean: list[str]          # non-empty when top_score < DID_YOU_MEAN_THRESHOLD

    # ── Prompt  (step_build_prompt) ───────────────────────────────────────────
    prompt: str

    # ── LLM Generation  (step_generate / step_parse) ─────────────────────────
    raw_llm_response: str            # raw JSON string returned by LLM
    response: Optional[dict]         # CernaResponse.model_dump() — always JSON-safe

    # ── Short-circuit paths ───────────────────────────────────────────────────
    refusal: str                     # non-empty → skip retrieval + generation
    semantic_cache_hit: bool         # True → semantic cache returned a response; skip retrieval
    query_embedding: Optional[list]  # float list (1024-dim); set by semantic cache check for reuse

    # ── Output ───────────────────────────────────────────────────────────────
    sources: list[dict]              # [{"source":…, "vertical":…, "score":…}]

    # ── Pipeline Metadata ─────────────────────────────────────────────────────
    trace: list[TraceEvent]          # one TraceEvent appended per step
    error: Optional[str]             # set if a step raises an unhandled exception


# ── Constructors ──────────────────────────────────────────────────────────────

def make_initial_state(
    query: str,
    conversation_history: list[dict] | None = None,
    module_hint: str | None = None,
) -> CernaState:
    """Return a fully-initialised CernaState with every field at a safe default."""
    return CernaState(
        trace_id=str(uuid.uuid4()),
        original_query=query,
        conversation_history=conversation_history or [],
        module_hint=module_hint,
        # Understanding
        intent="question",
        formal_query="",
        query_variants=[],
        detected_modules=[],
        detected_entities=[],
        is_ambiguous=False,
        # Clarification
        needs_clarification=False,
        clarification_question="",
        # Routing
        classification="GENERAL",
        retrieval_vertical=None,
        fetch_k=5,
        should_hyde=False,
        # Retrieval setup
        variant1="",
        variant2="",
        hyde_doc="",
        # Results
        raw_result_lists=[],
        fused_chunks=[],
        final_chunks=[],
        # Gates
        low_confidence=False,
        citation_warning=False,
        did_you_mean=[],
        # Prompt + generation
        prompt="",
        raw_llm_response="",
        response=None,
        # Short-circuit
        refusal="",
        semantic_cache_hit=False,
        query_embedding=None,
        # Output
        sources=[],
        # Meta
        trace=[],
        error=None,
    )


# ── Serialisation helpers ─────────────────────────────────────────────────────

def chunk_to_dict(chunk) -> dict:
    """
    Convert a RetrievedChunk dataclass to a plain JSON-serialisable dict.
    Called at every step boundary where chunks enter the state.
    """
    return {
        "text":           chunk.text,
        "source":         chunk.source,
        "vertical":       chunk.vertical,
        "score":          float(chunk.score),
        "semantic_score": float(chunk.semantic_score),
        "source_weight":  float(chunk.source_weight),
        "doc_type":       chunk.doc_type,
        "priority_tier":  chunk.priority_tier,
        "source_quality": getattr(chunk, "source_quality", "secondary"),
    }


def dict_to_chunk(d: dict):
    """
    Convert a state chunk dict back to a RetrievedChunk dataclass.
    Called inside step functions that need to pass chunks to retriever/reranker APIs.
    """
    from retriever import RetrievedChunk
    return RetrievedChunk(
        text=d["text"],
        source=d["source"],
        vertical=d["vertical"],
        score=float(d["score"]),
        source_weight=float(d.get("source_weight", 0.5)),
        doc_type=d.get("doc_type", "community"),
        priority_tier=d.get("priority_tier", "nice"),
        semantic_score=float(d.get("semantic_score", 0.0)),
        source_quality=d.get("source_quality", "secondary"),
    )
