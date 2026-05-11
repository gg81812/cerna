"""
pipeline.py — Pure step functions + LCEL composition for the Cerna request pipeline.

Architecture
------------
Every public step function has the signature:
    fn(state: CernaState) -> CernaState

Steps that need external resources (LLMs, retriever) are created by factory
functions that capture those dependencies via closure. This keeps the step
functions themselves pure and independently testable:

    step = make_step_retrieve(retriever)
    result_state = step(initial_state)

The LCEL chain is assembled by build_pipeline() and composed using:
    - RunnableLambda       — wraps each step function as a Runnable
    - RunnableParallel     — fans out retrieval across all query variants simultaneously
    - RunnableBranch       — routes on intent (casual / oos / clinical vs. full pipeline)
    - .with_fallbacks()    — LLM fallback chain (big model → small model → graceful error)

LangGraph migration note
------------------------
To migrate to LangGraph, replace build_pipeline() with a StateGraph that wires
the same step functions as nodes. Zero changes to the step functions themselves.
See docs/langgraph_migration.md for the full port plan.
"""

from __future__ import annotations

import functools
import json
import re
import time
from typing import Optional

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnableParallel

from config import (
    CERNER_CLINICAL,
    CERNER_FHIR,
    CERNER_GENERAL,
    CERNER_MILLENNIUM,
    CERNER_POWERCHART,
    CERNER_REVENUE_CYCLE,
    CONFIDENCE_THRESHOLD,
    CONFIDENCE_THRESHOLD_GENERAL,
    CITATION_SCORE_THRESHOLD,
    DID_YOU_MEAN_THRESHOLD,
    FINAL_TOP_K,
    HYDE_ENABLED,
    RERANK_ENABLED,
    RERANK_TOP_K,
    TOP_K,
    VALID_CLASSIFICATIONS,
)

# Iterative retrieval threshold — avg semantic score of top-3 chunks below this triggers
# a second (HyDE) and third (variant) retrieval pass before giving up.
ITERATIVE_RETRIEVAL_THRESHOLD: float = 0.55
from prompts import (
    CLASSIFICATION_PROMPT,
    COMPARISON_PROMPT_TEMPLATE,
    FOLLOWUP_PROMPT_TEMPLATE,
    MODULE_PROMPT_MAP,
    SYSTEM_PROMPT_TEMPLATE,
    format_context,
    format_history,
)
from query_rewriter import generate_hyde, understand_query
from reranker import rerank
from safety import REFUSAL_MESSAGES, requires_citation
from schemas import CernaResponse
from state import CernaState, TraceEvent, chunk_to_dict, dict_to_chunk

# ── Module-level helpers (moved from orchestrator.py) ─────────────────────────

_MODULE_KEYWORDS: dict[str, list[str]] = {
    "MILLENNIUM":    ["millennium", "ccl", "mpages", "discern", "domain"],
    "POWERCHART":    ["powerchart", "cpoe", "powernote", "patient list", "order entry"],
    "REVENUE_CYCLE": ["revenue cycle", "rcm", "charge capture", "claims", "billing",
                      "revelate", "cdi", "him coding", "denial"],
    "FHIR":          ["fhir", "smart on fhir", "oauth", "hl7", "careaware", "api"],
    "CLINICAL":      ["emar", "bcma", "nursing", "pharmnet", "medication admin",
                      "firstnet", "surginet", "scheduling"],
}

_ENTITY_MODULE_PRIORITY: dict[str, str] = {
    "smart":      "FHIR",
    "fhir":       "FHIR",
    "hl7":        "FHIR",
    "oauth":      "FHIR",
    "careaware":  "FHIR",
    "emar":       "CLINICAL",
    "bcma":       "CLINICAL",
    "pharmnet":   "CLINICAL",
    "firstnet":   "CLINICAL",
    "surginet":   "CLINICAL",
    "cpoe":       "POWERCHART",
    "powernote":  "POWERCHART",
    "powerchart": "POWERCHART",
    "ccl":        "MILLENNIUM",
    "mpages":     "MILLENNIUM",
    "mpage":      "MILLENNIUM",
    "discern":    "MILLENNIUM",
    "millennium": "MILLENNIUM",
    "revelate":   "REVENUE_CYCLE",
    "cdi":        "REVENUE_CYCLE",
}

_VERTICAL_MAP: dict[str, Optional[str]] = {
    "MILLENNIUM":    CERNER_MILLENNIUM,
    "POWERCHART":    CERNER_POWERCHART,
    "REVENUE_CYCLE": CERNER_REVENUE_CYCLE,
    "FHIR":          CERNER_FHIR,
    "CLINICAL":      CERNER_CLINICAL,
    "GENERAL":       None,
}

_CASUAL_RESPONSE = (
    "I'm Cerna, an AI specialist for Oracle Health (Cerner) implementation and configuration. "
    "I can help with:\n\n"
    "- **Millennium** — platform architecture, CCL, code sets, MPages\n"
    "- **PowerChart** — CPOE, order sets, clinical documentation, alerts\n"
    "- **Revenue Cycle** — charge capture, claims, RevElate, CDI\n"
    "- **FHIR & APIs** — SMART on FHIR, R4 resources, OAuth, Ignite APIs\n"
    "- **Clinical Workflows** — eMAR, BCMA, PharmNet, FirstNet\n\n"
    "What would you like to explore?"
)

_LOW_CONFIDENCE_RESPONSE_DICT: dict = {
    "direct_answer": (
        "I don't have sufficient information in my Cerner knowledge base to "
        "answer this question confidently."
    ),
    "context_explanation": (
        "The retrieved documents do not contain enough relevant information on this topic."
    ),
    "step_by_step": [],
    "best_practices": [],
    "recommendations": (
        "Try rephrasing with more specific Cerner terminology, or search "
        "uCern (cernercentral.com) for official documentation on this topic."
    ),
    "confidence": "low",
    "response_mode": "low",
}

_MEDIUM_CONFIDENCE_SOURCE_FRAMING = (
    " This is based on available documentation and may not reflect your "
    "facility's specific configuration. For implementation details, verify "
    "with your local Cerner reference or uCern (cernercentral.com)."
)

_TPD_RESPONSE_JSON = json.dumps({
    "direct_answer": (
        "The Groq API's daily token quota has been exhausted. "
        "Please wait until midnight UTC for the limit to reset."
    ),
    "context_explanation": "",
    "step_by_step": [],
    "best_practices": [],
    "recommendations": (
        "The free Groq tier resets at midnight UTC. "
        "Consider upgrading to a paid plan for higher daily limits."
    ),
    "confidence": "low",
})

# Session-level understand_query cache (keyed on query + history tail).
# In LangGraph this would be replaced by the checkpointer.
_understand_cache: dict[str, object] = {}


# ── Utility functions ─────────────────────────────────────────────────────────

def _classification_to_vertical(classification: str) -> Optional[str]:
    return _VERTICAL_MAP.get(classification, None)


def _detect_modules(query: str) -> list[str]:
    q = query.lower()
    return [
        label for label, kws in _MODULE_KEYWORDS.items()
        if any(kw in q for kw in kws)
    ]


def _is_cross_module(query: str, classification: str) -> bool:
    if classification == "GENERAL":
        return True
    return len(_detect_modules(query)) >= 2


def _resolve_with_entity_priority(module_hints: list[str], entities: list[str]) -> str:
    """Break a multi-module tie using entity names. Falls back to first hint or GENERAL."""
    for entity in entities:
        e = entity.lower()
        for keyword, module in _ENTITY_MODULE_PRIORITY.items():
            if keyword in e and module in module_hints:
                return module
    return module_hints[0] if len(module_hints) == 2 else CERNER_GENERAL


def _deduplicate_sources(chunk_dicts: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for d in chunk_dicts:
        key = d["source"]
        if key not in seen or d["score"] > seen[key]["score"]:
            seen[key] = {
                "source":         d["source"],
                "vertical":       d["vertical"],
                "score":          d["score"],
                "source_quality": d.get("source_quality", "secondary"),
            }
    return sorted(seen.values(), key=lambda s: s["score"], reverse=True)


def _rrf_fuse_multiple(result_lists: list[list], k: int = 60) -> list:
    """Reciprocal Rank Fusion over N retrieval result lists (RetrievedChunk objects)."""
    from retriever import RetrievedChunk
    rrf_scores: dict[str, float] = {}
    chunk_map:  dict[str, RetrievedChunk] = {}
    sem_scores: dict[str, float] = {}

    for result_list in result_lists:
        for rank, chunk in enumerate(result_list):
            key = f"{chunk.source}|||{chunk.text[:200]}"
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            sem_scores[key] = max(sem_scores.get(key, 0.0), chunk.semantic_score)
            if key not in chunk_map:
                chunk_map[key] = chunk

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
        )
        for key in sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)
    ]


# ── Tracing decorator ─────────────────────────────────────────────────────────

def _input_summary(state: CernaState, step: str) -> str:
    q = (state.get("original_query") or "")[:40]
    if step == "understand":
        return f"query={q!r}"
    if step in ("classify_module", "prepare_retrieval"):
        return f"intent={state.get('intent')!r} modules={state.get('detected_modules', [])}"
    if step == "retrieve":
        n = 1 + bool(state.get("variant1")) + bool(state.get("variant2")) + bool(state.get("should_hyde"))
        return f"n_queries={n} vertical={state.get('retrieval_vertical')}"
    if step == "fuse":
        return f"n_lists={len(state.get('raw_result_lists', []))}"
    if step in ("rerank", "gate"):
        return f"n_chunks={len(state.get('fused_chunks', []))}"
    if step == "build_prompt":
        return f"classification={state.get('classification')!r}"
    if step == "generate":
        return f"prompt_len={len(state.get('prompt', ''))}"
    if step == "parse":
        return f"raw_len={len(state.get('raw_llm_response', ''))}"
    return f"query={q!r}"


def _output_summary(state: CernaState, step: str) -> str:
    if step == "understand":
        return f"intent={state.get('intent')!r} modules={state.get('detected_modules', [])}"
    if step == "classify_module":
        return f"cls={state.get('classification')!r} vertical={state.get('retrieval_vertical')}"
    if step == "retrieve":
        total = sum(len(lst) for lst in state.get("raw_result_lists", []))
        return f"total_chunks={total}"
    if step == "fuse":
        return f"fused={len(state.get('fused_chunks', []))}"
    if step in ("rerank", "gate"):
        fc = state.get("final_chunks", [])
        top = fc[0].get("semantic_score", 0.0) if fc else 0.0
        return f"final={len(fc)} top_score={top:.3f}"
    if step == "generate":
        return f"raw_len={len(state.get('raw_llm_response', ''))}"
    if step == "parse":
        resp = state.get("response") or {}
        return f"confidence={resp.get('confidence', '?')!r}"
    if "refusal" in step or "casual" in step or "oos" in step or "clinical" in step:
        return "refusal set"
    return ""


def traced(step_name: str):
    """
    Decorator that wraps a (state: CernaState) -> CernaState function with:
      - Wall-clock timing
      - TraceEvent appended to state["trace"]
      - Error capture: on exception, sets state["error"] and returns the state
        so the pipeline can continue to the parse/format step gracefully.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(state: CernaState) -> CernaState:
            t0 = time.monotonic()
            in_summary = _input_summary(state, step_name)
            try:
                out = fn(state)
                duration_ms = int((time.monotonic() - t0) * 1000)
                event = TraceEvent(
                    step=step_name,
                    duration_ms=duration_ms,
                    success=True,
                    input_summary=in_summary,
                    output_summary=_output_summary(out, step_name),
                    error=None,
                )
                return {**out, "trace": out.get("trace", []) + [event]}
            except Exception as exc:
                duration_ms = int((time.monotonic() - t0) * 1000)
                print(f"[Pipeline:{step_name}] ERROR: {exc}")
                event = TraceEvent(
                    step=step_name,
                    duration_ms=duration_ms,
                    success=False,
                    input_summary=in_summary,
                    output_summary="",
                    error=str(exc)[:300],
                )
                return {**state, "error": str(exc), "trace": state.get("trace", []) + [event]}
        return wrapper
    return decorator


# ── Step 1: Understand ────────────────────────────────────────────────────────

def make_step_understand() -> callable:
    """
    Factory for step_understand.
    One JSON-mode LLM call that replaces the old safety+rewrite+classify+enrich quad.
    Results are cached in-process on (query, history_tail) to avoid duplicate calls
    on retries within the same session.
    """
    @traced("understand")
    def step_understand(state: CernaState) -> CernaState:
        query = state["original_query"]
        history_str = format_history(state["conversation_history"])

        cache_key = f"{query.strip()}|||{history_str[-200:]}"
        if cache_key in _understand_cache:
            u = _understand_cache[cache_key]
        else:
            u = understand_query(query, history_str)
            _understand_cache[cache_key] = u

        return {
            **state,
            "intent":                  u.intent,
            "formal_query":            u.formal_query or query,
            "query_variants":          u.variants,
            "detected_modules":        u.module_hints,
            "detected_entities":       u.entities,
            "is_ambiguous":            u.is_ambiguous,
            "refusal_key":             getattr(u, "refusal_key", ""),
            "needs_clarification":     getattr(u, "needs_clarification", False),
            "clarification_question":  getattr(u, "clarification_question", ""),
        }
    return step_understand


# ── Step 2: Intent routing (refusal short-circuits) ───────────────────────────

@traced("route_casual")
def step_casual(state: CernaState) -> CernaState:
    return {**state, "refusal": _CASUAL_RESPONSE}


@traced("route_oos")
def step_out_of_scope(state: CernaState) -> CernaState:
    key = state.get("refusal_key") or "out_of_domain"
    msg = REFUSAL_MESSAGES.get(key, REFUSAL_MESSAGES["out_of_domain"])
    return {**state, "refusal": msg}


@traced("route_clarify")
def step_clarify(state: CernaState) -> CernaState:
    """
    Multi-branch clarification short-circuit (Phase 1 Item 2).

    When the 8B classifier sets needs_clarification=True for a question or
    troubleshooting query, route here instead of running retrieval+generation.
    The classifier's single short clarification_question becomes the response;
    retrieval and the 70B call are skipped entirely.

    The eval detector reads the question text via the `refusal` channel and
    classifies it as `clarify` because the classifier prompt nudges its
    questions to start with "Could you tell me whether ...", "Are you asking
    about ...", or "Which of these applies — ..." — those phrases are in the
    detector's clarify keyword list.
    """
    question = state.get("clarification_question", "").strip()
    # Defensive fallback: if the classifier said needs_clarification=True but
    # produced an empty string, fall through to normal content flow rather
    # than render a blank response. The understand_query() safety net should
    # already catch this, but belt-and-suspenders.
    if not question:
        return {**state, "needs_clarification": False}
    return {**state, "refusal": question}


@traced("route_clinical")
def step_clinical_decision(state: CernaState) -> CernaState:
    """
    Refuse the clinical decision part, but offer the Cerner workflow side.

    If the query contains a workflow component (detected by the query rewriter's
    module hints pointing to a clinical module), pull that out and present it
    alongside the refusal — so the user gets something useful rather than a dead end.
    """
    query = state.get("original_query", "")
    formal = state.get("formal_query", "") or query
    modules = state.get("detected_modules", [])
    refusal_key = state.get("refusal_key") or ""

    # INT-04 path: the query already names a specific clinical conflict
    # (allergy / dose / interaction). The dedicated message in
    # REFUSAL_MESSAGES["clinical_decision_int04"] already routes to the right
    # clinical resource per conflict type, so do not append the generic
    # workflow-hint suffix below.
    if refusal_key == "clinical_decision_int04":
        return {
            **state,
            "refusal": REFUSAL_MESSAGES["clinical_decision_int04"],
        }

    # For queries that have a clear workflow component, offer workflow help
    has_workflow_component = bool(modules) and any(
        m in ("CLINICAL", "POWERCHART") for m in modules
    )

    if has_workflow_component:
        # Identify which workflow area is relevant and add it to the refusal
        workflow_areas = []
        if "CLINICAL" in modules:
            workflow_areas.append("eMAR/BCMA medication administration workflows")
        if "POWERCHART" in modules:
            workflow_areas.append("PowerChart CPOE order management and clinical alerts")
        workflow_hint = " and ".join(workflow_areas) if workflow_areas else "Cerner clinical workflows"

        msg = (
            REFUSAL_MESSAGES["clinical_decision"]
            + f"\n\nFor the Cerner **workflow** side of this question, I can help with "
            f"{workflow_hint}. Try asking: \"How does [the workflow process] work in Cerner?\""
        )
    else:
        msg = REFUSAL_MESSAGES["clinical_decision"]

    return {**state, "refusal": msg}


# ── Step 3: Module classification ─────────────────────────────────────────────

def make_step_classify_module(llm_fast) -> callable:
    """Factory for step_classify_module. Captures fast LLM for the fallback path."""

    def _classify_with_llm(query: str) -> str:
        try:
            result = llm_fast.invoke([HumanMessage(content=CLASSIFICATION_PROMPT.format(question=query))])
            raw = result.content.strip().upper()
            word = re.split(r"[\s\.,;:]+", raw)[0]
            if word in VALID_CLASSIFICATIONS:
                return word
            for label in VALID_CLASSIFICATIONS:
                if label in raw:
                    return label
        except Exception as exc:
            print(f"[Pipeline:classify_module] LLM fallback error: {exc}")
        return CERNER_GENERAL

    @traced("classify_module")
    def step_classify_module(state: CernaState) -> CernaState:
        hint    = state.get("module_hint")
        modules = state["detected_modules"]
        entities = state["detected_entities"]

        if hint and hint.upper() in VALID_CLASSIFICATIONS:
            classification = hint.upper()
        elif len(modules) == 1:
            classification = modules[0]
        elif len(modules) > 1:
            classification = _resolve_with_entity_priority(modules, entities)
        else:
            classification = _classify_with_llm(state["formal_query"] or state["original_query"])

        is_cross = _is_cross_module(state["formal_query"] or state["original_query"], classification)
        vertical = None if is_cross else _classification_to_vertical(classification)
        fetch_k  = RERANK_TOP_K if RERANK_ENABLED else TOP_K
        should_hyde = HYDE_ENABLED or state["is_ambiguous"]

        return {
            **state,
            "classification":      classification,
            "retrieval_vertical":  vertical,
            "fetch_k":             fetch_k,
            "should_hyde":         should_hyde,
        }
    return step_classify_module


# ── Step 4: Prepare retrieval ─────────────────────────────────────────────────

@traced("prepare_retrieval")
def step_prepare_retrieval(state: CernaState) -> CernaState:
    """Split query_variants into named fields consumed by the parallel retrieval step."""
    variants = state["query_variants"]
    return {
        **state,
        "variant1": variants[0] if len(variants) > 0 else "",
        "variant2": variants[1] if len(variants) > 1 else "",
    }


# ── Step 5: Iterative retrieval ───────────────────────────────────────────────

def _avg_top3_semantic(chunk_dicts: list[dict]) -> float:
    """Average semantic_score of the top-3 chunks (or all if fewer than 3)."""
    scores = sorted(
        (d.get("semantic_score", 0.0) for d in chunk_dicts),
        reverse=True,
    )[:3]
    return sum(scores) / len(scores) if scores else 0.0


def make_step_retrieve(retriever) -> callable:
    """
    Factory for step_retrieve — iterative multi-pass retrieval.

    Pass 1 (always): parallel fan-out across formal + variant1 + variant2.
    Pass 2 (if avg top-3 semantic score < ITERATIVE_RETRIEVAL_THRESHOLD): HyDE retrieval.
    Pass 3 (if still below threshold): variant2 with broader context (no vertical filter).

    All passes' chunks are unioned, deduplicated by chunk ID, and re-ranked by RRF.
    Explicit logging at each pass gives the data needed to tune thresholds later.

    Latency budget: each pass adds ~200–400 ms. Worst case (~1.2 s retrieval) is
    within the 5-second response cap, so all three passes are kept.

    LangGraph note: this becomes a conditional Map node over retrieval_queries.
    """

    def _do_retrieve(query: str, state: CernaState, vertical_override=None) -> list[dict]:
        if not query:
            return []
        vertical = vertical_override if vertical_override is not None else state.get("retrieval_vertical")
        chunks = retriever.query(query, vertical, state.get("fetch_k", TOP_K))
        return [chunk_to_dict(c) for c in chunks]

    # Pass 1 parallel fan-out (same as before — no HyDE blocking the fan-out).
    _parallel_pass1 = RunnableParallel(
        formal   = RunnableLambda(lambda s: _do_retrieve(s.get("formal_query", ""), s)),
        variant1 = RunnableLambda(lambda s: _do_retrieve(s.get("variant1", ""), s)),
        variant2 = RunnableLambda(lambda s: _do_retrieve(s.get("variant2", ""), s)),
    )

    @traced("retrieve")
    def step_retrieve(state: CernaState) -> CernaState:
        fetch_k   = state.get("fetch_k", TOP_K)
        threshold = ITERATIVE_RETRIEVAL_THRESHOLD

        # ── Pass 1: parallel formal + variants ─────────────────────────────
        p1_results = _parallel_pass1.invoke(state)
        pass1_lists = [lst for lst in p1_results.values() if lst]
        all_lists: list[list[dict]] = list(pass1_lists)

        # Quick fuse pass1 to assess quality before deciding on pass 2
        from retriever import RetrievedChunk  # local import to avoid circular at module init
        p1_fused: list[dict] = [
            chunk_to_dict(c)
            for c in _rrf_fuse_multiple(
                [[dict_to_chunk(d) for d in lst] for lst in pass1_lists]
            )
        ] if pass1_lists else []

        p1_avg = _avg_top3_semantic(p1_fused)
        print(
            f"[Retrieve:pass1] strategy=parallel formal+variants  "
            f"avg_top3={p1_avg:.3f}  threshold={threshold}"
        )

        # ── Pass 2: HyDE (if pass-1 quality is insufficient) ──────────────
        hyde_text = ""
        p2_avg = p1_avg
        if p1_avg < threshold:
            hyde_text = generate_hyde(state["formal_query"])
            if hyde_text:
                p2_chunks = _do_retrieve(hyde_text, state)
                if p2_chunks:
                    all_lists.append(p2_chunks)
                    # Re-fuse to measure improvement
                    p2_fused = [
                        chunk_to_dict(c)
                        for c in _rrf_fuse_multiple(
                            [[dict_to_chunk(d) for d in lst] for lst in all_lists]
                        )
                    ]
                    p2_avg = _avg_top3_semantic(p2_fused)
                    print(
                        f"[Retrieve:pass2] strategy=HyDE  "
                        f"avg_top3={p2_avg:.3f}  "
                        f"trigger=pass1_avg({p1_avg:.3f})<{threshold}"
                    )
                else:
                    print(f"[Retrieve:pass2] strategy=HyDE  no chunks returned")
            else:
                print(f"[Retrieve:pass2] strategy=HyDE  generation returned empty")
        else:
            print(
                f"[Retrieve:pass2] skipped — pass1 quality sufficient "
                f"(avg_top3={p1_avg:.3f}>={threshold})"
            )

        # ── Pass 3: broad variant retrieval with no vertical filter ────────
        if p2_avg < threshold and state.get("variant1"):
            broad_query = state.get("variant1") or state.get("formal_query", "")
            p3_chunks = _do_retrieve(broad_query, state, vertical_override=None)
            if p3_chunks:
                all_lists.append(p3_chunks)
                p3_fused = [
                    chunk_to_dict(c)
                    for c in _rrf_fuse_multiple(
                        [[dict_to_chunk(d) for d in lst] for lst in all_lists]
                    )
                ]
                p3_avg = _avg_top3_semantic(p3_fused)
                print(
                    f"[Retrieve:pass3] strategy=broad_variant (no vertical filter)  "
                    f"avg_top3={p3_avg:.3f}  "
                    f"trigger=pass2_avg({p2_avg:.3f})<{threshold}"
                )
            else:
                print(f"[Retrieve:pass3] strategy=broad_variant  no chunks returned")
        elif p2_avg >= threshold:
            print(
                f"[Retrieve:pass3] skipped — pass2 quality sufficient "
                f"(avg_top3={p2_avg:.3f}>={threshold})"
            )
        else:
            print(f"[Retrieve:pass3] skipped — no variant available for broad search")

        return {
            **state,
            "raw_result_lists": all_lists,
            "hyde_doc":         hyde_text,
        }

    return step_retrieve


# ── Step 6: RRF fusion ────────────────────────────────────────────────────────

@traced("fuse")
def step_fuse(state: CernaState) -> CernaState:
    """Fuse all retrieval result lists with Reciprocal Rank Fusion."""
    raw = state["raw_result_lists"]
    if not raw:
        return {**state, "fused_chunks": []}

    # Deserialise dicts → RetrievedChunk for the RRF algorithm
    result_lists = [[dict_to_chunk(d) for d in lst] for lst in raw]
    fused = _rrf_fuse_multiple(result_lists)
    return {**state, "fused_chunks": [chunk_to_dict(c) for c in fused]}


# ── Step 7: Reranking ─────────────────────────────────────────────────────────

@traced("rerank")
def step_rerank(state: CernaState) -> CernaState:
    """Cross-encoder rerank if RERANK_ENABLED, else trim fused list to TOP_K."""
    chunks = [dict_to_chunk(d) for d in state["fused_chunks"]]
    if not chunks:
        return {**state, "final_chunks": []}

    if RERANK_ENABLED:
        rerank_query = state["formal_query"] or state["original_query"]
        chunks = rerank(rerank_query, chunks)
    else:
        chunks = chunks[:TOP_K]

    return {**state, "final_chunks": [chunk_to_dict(c) for c in chunks]}


# ── Step 8: Quality gates ─────────────────────────────────────────────────────

@traced("gate")
def step_gate(state: CernaState) -> CernaState:
    """Apply did-you-mean, low-confidence, and citation-warning gates."""
    chunks = [dict_to_chunk(d) for d in state["final_chunks"]]
    top_score = max((c.semantic_score for c in chunks), default=0.0)

    # Did-you-mean: retrieval too weak, surface variant suggestions
    did_you_mean: list[str] = []
    if top_score < DID_YOU_MEAN_THRESHOLD and state["query_variants"]:
        did_you_mean = [v for v in state["query_variants"] if v][:3]

    # Confidence gate
    threshold = (
        CONFIDENCE_THRESHOLD_GENERAL
        if state["classification"] == "GENERAL"
        else CONFIDENCE_THRESHOLD
    )
    low_confidence = not chunks or all(c.semantic_score < threshold for c in chunks)

    # Citation warning (clinical/FHIR/RCM with no high-score chunk)
    citation_warning = requires_citation(state["classification"], chunks)

    return {
        **state,
        "did_you_mean":    did_you_mean,
        "low_confidence":  low_confidence,
        "citation_warning": citation_warning,
    }


# ── Step 8a: Did-you-mean short-circuit ───────────────────────────────────────

@traced("did_you_mean")
def step_did_you_mean(state: CernaState) -> CernaState:
    """
    Skip LLM generation; return a genuine clarifying question with concrete options.
    Rather than guessing, the system presents what the query could mean and asks
    the user to disambiguate — more useful than a low-confidence wrong answer.
    """
    variants = [v for v in state.get("query_variants", []) if v][:3]
    original = state.get("original_query", "")

    if variants:
        options = "\n".join(f"  ({chr(97+i)}) {v}" for i, v in enumerate(variants))
        direct_answer = (
            f"That could mean a few different things in Cerner — could you clarify?\n\n"
            f"{options}\n\n"
            f"Letting me know which applies will help me give you a specific, accurate answer."
        )
    else:
        direct_answer = (
            "I'm not confident which Cerner topic this refers to. "
            "Could you add more detail — for example, which module you're working in "
            "(PowerChart, BCMA, Revenue Cycle, Millennium) or what you're trying to accomplish?"
        )

    resp = {
        "direct_answer":       direct_answer,
        "context_explanation": "",
        "step_by_step":        [],
        "best_practices":      [],
        "recommendations": (
            "You can also try rephrasing with specific Cerner feature names, "
            "or search uCern (cernercentral.com) for the official documentation."
        ),
        "confidence":    "low",
        "response_mode": "low",
    }
    return {
        **state,
        "response": resp,
        "sources":  _deduplicate_sources(state.get("final_chunks", [])),
    }


# ── Step 9: Build prompt ──────────────────────────────────────────────────────

@traced("build_prompt")
def step_build_prompt(state: CernaState) -> CernaState:
    """Format the LLM prompt from retrieved chunks, intent context, and history."""
    from pii_guard import mask_pii
    chunks = [dict_to_chunk(d) for d in state["final_chunks"]]
    history_str = format_history(state["conversation_history"])
    original = mask_pii(state["original_query"])
    formal   = mask_pii(state["formal_query"])
    intent   = state["intent"]
    is_ambig = state["is_ambiguous"]

    # Intent-aware question field enrichment
    if intent == "troubleshooting":
        question_for_prompt = (
            f"[Troubleshooting] The user is experiencing a problem.\n"
            f"User message: {original}\n"
            f"Cerner interpretation: {formal}"
        )
    elif is_ambig and formal and formal.lower() != original.lower():
        question_for_prompt = (
            f"[Vague query — interpret broadly]\n"
            f"User message: {original}\n"
            f"Best Cerner interpretation: {formal}"
        )
    elif formal and formal.lower() != original.lower():
        question_for_prompt = f"{original}\n[Cerna interpretation: {formal}]"
    else:
        question_for_prompt = original

    # Cross-module vs. single-module prompt selection
    modules = state["detected_modules"]
    classification = state["classification"]
    is_cross = (classification == CERNER_GENERAL and len(modules) >= 2)

    if is_cross and len(modules) >= 2:
        va = _classification_to_vertical(modules[0])
        vb = _classification_to_vertical(modules[1])
        chunks_a = [c for c in chunks if c.vertical == va][:TOP_K]
        chunks_b = [c for c in chunks if c.vertical == vb][:TOP_K]
        if chunks_a or chunks_b:
            prompt = COMPARISON_PROMPT_TEMPLATE.format(
                module_a_context=format_context(chunks_a or chunks[:TOP_K]),
                module_b_context=format_context(chunks_b or []),
                conversation_history=history_str,
                question=question_for_prompt,
            )
        else:
            # Fall through to single-module specialist if no split possible
            template = MODULE_PROMPT_MAP.get(classification, SYSTEM_PROMPT_TEMPLATE)
            prompt = template.format(
                context=format_context(chunks),
                conversation_history=history_str,
                question=question_for_prompt,
            )
    else:
        # Select module-specialist template if one exists; fall back to generic
        template = MODULE_PROMPT_MAP.get(classification, SYSTEM_PROMPT_TEMPLATE)
        prompt = template.format(
            context=format_context(chunks),
            conversation_history=history_str,
            question=question_for_prompt,
        )

    return {**state, "prompt": prompt}


# ── Step 10: LLM generation ───────────────────────────────────────────────────

def make_step_generate(llm_json, llm_fast_json) -> callable:
    """
    Factory for step_generate.

    Calls the primary LLM via safe_invoke_json which handles:
      - 429 / 5xx: one retry after 2 s
      - 400 / timeout / auth errors: no retry, graceful fallback
    On any final failure, returns a structured low-confidence CernaResponse
    that the UI renders as a clean error card (never shows a raw exception).

    llm_fast_json is retained in the signature for backward compatibility
    but is not used in the primary path (fallback chain removed per Day-2
    hardening — the graceful response in safe_invoke_json covers all cases).
    """
    from llm import safe_invoke_json

    @traced("generate")
    def step_generate(state: CernaState) -> CernaState:
        if state.get("low_confidence") and not state.get("prompt"):
            return {**state, "raw_llm_response": json.dumps(_LOW_CONFIDENCE_RESPONSE_DICT)}

        messages = [HumanMessage(content=state["prompt"])]
        query_hint = state.get("formal_query") or state.get("original_query", "")
        raw = safe_invoke_json(llm_json, messages, query_hint=query_hint)
        return {**state, "raw_llm_response": raw}

    return step_generate


# ── Step 11: Parse response ───────────────────────────────────────────────────

def _compute_response_mode(
    final_chunks: list[dict],
    low_confidence: bool,
    citation_warning: bool,
) -> str:
    """
    Determine response_mode from retrieval quality signals.

    high   — top chunk score > 0.7, no citation warning, chunks present
    medium — top chunk score 0.5–0.7, OR citation warning present
    low    — top chunk score < 0.5, OR low_confidence flag set, OR no chunks
    """
    if low_confidence or not final_chunks:
        return "low"
    top_score = max((d.get("semantic_score", 0.0) for d in final_chunks), default=0.0)
    has_archival = any(
        d.get("source_quality") in ("archival", "third_party") for d in final_chunks
    )
    if top_score >= 0.7 and not citation_warning and not has_archival:
        return "high"
    if top_score >= 0.5 or (citation_warning and top_score >= 0.4):
        return "medium"
    return "low"


@traced("parse")
def step_parse(state: CernaState) -> CernaState:
    """Parse raw JSON from LLM into a CernaResponse dict and apply safety + confidence overrides."""
    final_chunks    = state.get("final_chunks", [])
    low_confidence  = state.get("low_confidence", False)
    citation_warning = state.get("citation_warning", False)
    response_mode   = _compute_response_mode(final_chunks, low_confidence, citation_warning)

    if low_confidence:
        # Build a genuinely useful low-confidence response from whatever chunks we have
        related_chunks = final_chunks[:3]
        if related_chunks:
            chunk_summaries = "; ".join(
                f"[{d.get('source', 'unknown')}] {d.get('text', '')[:120].strip()}"
                for d in related_chunks
            )
            direct_answer = (
                "Limited authoritative information on this specific question. "
                f"Here's what I found that may be related: {chunk_summaries}. "
                "For an authoritative answer, check uCern (cernercentral.com), "
                "your facility's training materials, or your IT help desk."
            )
        else:
            direct_answer = (
                "I don't have sufficient information in my Cerner knowledge base to "
                "answer this question confidently. Try rephrasing with specific Cerner "
                "module names, or search uCern (cernercentral.com)."
            )
        resp = {
            **_LOW_CONFIDENCE_RESPONSE_DICT,
            "direct_answer":  direct_answer,
            "response_mode":  "low",
        }
        sources = _deduplicate_sources(final_chunks)
        return {**state, "response": resp, "sources": sources}

    raw = state.get("raw_llm_response", "")
    if not raw.strip():
        resp = {**_LOW_CONFIDENCE_RESPONSE_DICT, "response_mode": "low"}
    else:
        try:
            cerna_resp = CernaResponse.parse(raw)
            resp = cerna_resp.model_dump()
        except Exception as exc:
            print(f"[Pipeline:parse] JSON parse error: {exc}. Using raw text.")
            resp = {
                "direct_answer":       raw[:800],
                "context_explanation": "",
                "step_by_step":        [],
                "best_practices":      [],
                "recommendations":     "",
                "confidence":          "medium",
                "response_mode":       "medium",
            }

    # Stamp response_mode onto the parsed response
    resp["response_mode"] = response_mode

    # Medium-confidence: append source framing to recommendations
    if response_mode == "medium" and resp.get("recommendations"):
        if _MEDIUM_CONFIDENCE_SOURCE_FRAMING not in (resp.get("recommendations") or ""):
            resp["recommendations"] = (
                (resp.get("recommendations") or "") + _MEDIUM_CONFIDENCE_SOURCE_FRAMING
            )

    # Citation warning: downgrade confidence and append disclaimer
    if citation_warning and resp.get("confidence") == "high":
        resp["confidence"] = "medium"
        resp["response_mode"] = "medium"
        resp["recommendations"] = (
            (resp.get("recommendations") or "")
            + " Note: No retrieved source scored above the citation threshold "
            "for this clinical/FHIR/Revenue Cycle query. "
            "Verify against official uCern documentation before acting on it."
        )

    sources = _deduplicate_sources(final_chunks)
    return {**state, "response": resp, "sources": sources}


# ── Trace log helper ──────────────────────────────────────────────────────────

def log_pipeline_trace(state: CernaState) -> None:
    """
    Append the full pipeline trace as a single JSONL record to logs/trace_log.jsonl.
    Called at the end of each request by the orchestrator.
    This mirrors exactly the data LangGraph's checkpointer would persist.
    """
    import os
    from pathlib import Path
    from config import LOG_DIR

    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    trace_file = os.path.join(LOG_DIR, "trace_log.jsonl")

    from pii_guard import mask_pii
    record = {
        "trace_id":       state.get("trace_id"),
        "query":          mask_pii(state.get("original_query", ""))[:200],
        "intent":         state.get("intent"),
        "classification": state.get("classification"),
        "steps":          state.get("trace", []),
        "total_ms":       sum(e.get("duration_ms", 0) for e in state.get("trace", [])),
        "error":          state.get("error"),
    }
    try:
        with open(trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"[Pipeline] WARNING: could not write trace log: {exc}")


# ── Pipeline assembly ─────────────────────────────────────────────────────────

def build_pipeline(retriever, llm_json, llm_fast, llm_fast_json):
    """
    Assemble and return the full LCEL pipeline chain.

    The returned chain has the signature:
        chain.invoke(CernaState) -> CernaState

    Composition:
        step_understand
        └── RunnableBranch on intent
            ├── casual          → step_casual
            ├── out_of_scope    → step_out_of_scope
            ├── clinical        → step_clinical_decision
            └── (default)       → classify → prepare → retrieve → fuse
                                  → rerank → gate
                                  └── RunnableBranch on did_you_mean
                                      ├── non-empty → step_did_you_mean
                                      └── (default) → build_prompt → generate → parse

    LangGraph migration: replace this function's body with StateGraph(CernaState)
    and add_node() / add_conditional_edges() calls. The step functions are unchanged.
    """
    from semantic_cache import step_semantic_cache_check, step_semantic_cache_store

    # Create step runnables
    _understand  = RunnableLambda(make_step_understand())
    _classify    = RunnableLambda(make_step_classify_module(llm_fast))
    _sem_check   = RunnableLambda(step_semantic_cache_check)
    _sem_store   = RunnableLambda(step_semantic_cache_store)
    _prep        = RunnableLambda(step_prepare_retrieval)
    _retrieve    = RunnableLambda(make_step_retrieve(retriever))
    _fuse        = RunnableLambda(step_fuse)
    _rerank      = RunnableLambda(step_rerank)
    _gate        = RunnableLambda(step_gate)
    _build       = RunnableLambda(step_build_prompt)
    _generate    = RunnableLambda(make_step_generate(llm_json, llm_fast_json))
    _parse       = RunnableLambda(step_parse)
    _dym         = RunnableLambda(step_did_you_mean)
    _casual      = RunnableLambda(step_casual)
    _oos         = RunnableLambda(step_out_of_scope)
    _clinical    = RunnableLambda(step_clinical_decision)
    _clarify     = RunnableLambda(step_clarify)

    # Inner branch: did-you-mean vs. full generation
    _generation_branch = RunnableBranch(
        (lambda s: bool(s.get("did_you_mean")), _dym),
        _build | _generate | _parse,
    )

    # Retrieval branch: semantic cache hit short-circuits retrieval+generation
    _retrieval_branch = RunnableBranch(
        (lambda s: bool(s.get("semantic_cache_hit")), RunnableLambda(lambda s: s)),
        _prep | _retrieve | _fuse | _rerank | _gate | _generation_branch,
    )

    # Full content pipeline (used when intent requires retrieval)
    _content = (
        _classify
        | _sem_check          # semantic cache check (miss → full retrieval; hit → short-circuit)
        | _retrieval_branch   # skip retrieval if semantic cache hit
        | _sem_store          # store response in semantic cache if high-confidence
    )

    # Top-level intent router. Clarification check fires AFTER the safety
    # routes (casual / out_of_scope / clinical_decision) so we never short-
    # circuit a refusal-required query into a clarifying question.
    return (
        _understand
        | RunnableBranch(
            (lambda s: s["intent"] == "casual",            _casual),
            (lambda s: s["intent"] == "out_of_scope",      _oos),
            (lambda s: s["intent"] == "clinical_decision", _clinical),
            (lambda s: bool(s.get("needs_clarification")), _clarify),
            _content,
        )
    )


# ── Follow-up generation (standalone, not part of main pipeline) ──────────────

def make_generate_followups(llm_fast):
    """
    Returns a function that generates 3 follow-up questions.
    Kept separate from the main pipeline because it runs AFTER the response
    is rendered to the user (doesn't block the primary response).
    """
    def generate_followups(query: str, response_summary: str, history: list[dict]) -> list[str]:
        already_asked = "\n".join(
            f"- {m['content']}" for m in history if m["role"] == "user"
        ) or "None"
        prompt_text = FOLLOWUP_PROMPT_TEMPLATE.format(
            question=query,
            response_summary=response_summary[:400].strip(),
            already_asked=already_asked,
        )
        try:
            result = llm_fast.invoke([HumanMessage(content=prompt_text)]).content.strip()
            follow_ups = []
            for m in re.finditer(r"^\s*\d+[.)]\s*(.+)", result, re.MULTILINE):
                q = m.group(1).strip()
                if q:
                    follow_ups.append(q)
            return follow_ups[:3]
        except Exception as exc:
            print(f"[Pipeline:followups] Error: {exc}")
            return []
    return generate_followups
