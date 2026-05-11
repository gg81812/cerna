"""
orchestrator.py — Thin orchestration layer for Cerna.

This module is now a compatibility wrapper over pipeline.py. The business logic
lives entirely in pipeline.py (pure step functions) and state.py (CernaState).
This file's only job is to:

  1. Own the long-lived resources (retriever, LLM instances) that are expensive
     to initialise and must be reused across requests.
  2. Build the LCEL pipeline chain once at startup.
  3. Expose the same public API that app.py already uses (prepare / generate_structured /
     stream_json_tokens / parse_structured / generate_followups / run) so that
     no UI code changes are required.

LangGraph migration
-------------------
When Phase 3 begins, replace the build_pipeline() call with a LangGraph
StateGraph. The Orchestrator class itself stays unchanged — it will still own
resources and expose the same public API. See docs/langgraph_migration.md.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Generator, Optional

from langchain_core.messages import HumanMessage

from config import CERNER_GENERAL
from llm import get_llm, get_llm_fast, get_llm_fast_json, get_llm_json
from pipeline import (
    _LOW_CONFIDENCE_RESPONSE_DICT,
    build_pipeline,
    log_pipeline_trace,
    make_generate_followups,
)
from retriever import HealthcareRetriever, RetrievedChunk
from safety import REFUSAL_MESSAGES
from schemas import CernaResponse
from state import CernaState, make_initial_state


# ── Public return types (kept for backward compatibility with app.py) ─────────

@dataclass
class PreparedQuery:
    """
    Adapter between CernaState and the app.py API.
    Populated by Orchestrator.prepare() from the final CernaState.
    """
    prompt: str
    classification: str
    chunks: list[RetrievedChunk]
    sources: list[dict]
    rewritten_query: str
    low_confidence: bool = False
    refusal: str = ""
    citation_warning: bool = False
    intent: str = "question"
    formal_query: str = ""
    did_you_mean: list[str] = field(default_factory=list)
    # Keep a reference to the full state so generate_structured can use it
    _state: Optional[CernaState] = field(default=None, repr=False)


@dataclass
class OrchestratorResponse:
    response: str
    cerna_response: Optional[CernaResponse]
    classified_vertical: str
    sources: list[dict] = field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)


# ── Orchestrator ──────────────────────────────────────────────────────────────

class Orchestrator:
    """
    Stateless-per-request orchestrator for Cerna.
    Initialise once per app session; call .prepare() + .generate_structured() per request.

    All business logic lives in pipeline.py. This class:
      - Initialises and holds long-lived resources (retriever, LLMs).
      - Calls build_pipeline() to assemble the LCEL chain.
      - Converts CernaState ↔ PreparedQuery / CernaResponse for backward compat.
    """

    def __init__(self):
        self._retriever  = HealthcareRetriever()
        self._llm        = get_llm()
        self._llm_json   = get_llm_json()
        self._llm_fast   = get_llm_fast()
        self._llm_fast_json = get_llm_fast_json()

        self._pipeline = build_pipeline(
            self._retriever,
            self._llm_json,
            self._llm_fast,
            self._llm_fast_json,
        )
        self._generate_followups = make_generate_followups(self._llm_fast)
        print("[Orchestrator] Ready.")

    # ── Primary API ────────────────────────────────────────────────────────────

    def prepare(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
        module_hint: Optional[str] = None,
    ) -> PreparedQuery:
        """
        Run the full prepare pipeline (understand → route → retrieve → gate → prompt).
        Returns a PreparedQuery ready for generate_structured() or stream_json_tokens().
        """
        initial = make_initial_state(query, conversation_history, module_hint)
        state   = self._pipeline.invoke(initial)
        log_pipeline_trace(state)
        return self._state_to_prepared(state)

    def generate_structured(self, prepared: PreparedQuery) -> CernaResponse:
        """
        Generate a structured CernaResponse.
        If the state already has a response (did-you-mean or low-confidence path),
        returns it directly without calling the LLM again.
        """
        # Refusal paths
        if prepared.refusal:
            return CernaResponse(
                direct_answer=prepared.refusal,
                context_explanation="",
                step_by_step=[],
                best_practices=[],
                recommendations="",
                confidence="low",
            )

        # If the pipeline already produced a response (DYM / low-confidence)
        state = prepared._state
        if state and state.get("response"):
            return CernaResponse(**state["response"])

        # Low-confidence without a cached response
        if prepared.low_confidence:
            return CernaResponse(**_LOW_CONFIDENCE_RESPONSE_DICT)

        # Normal path: call the LLM with retry + fallback
        raw = self._generate_json_with_retry(prepared.prompt)
        return self._parse_and_apply_gates(raw, prepared)

    def stream_json_tokens(self, prepared: PreparedQuery) -> Generator[str, None, None]:
        """
        Stream raw JSON tokens from the LLM.
        Caller accumulates tokens then calls parse_structured().
        Yields nothing for refusal / low-confidence queries.
        """
        if prepared.refusal or prepared.low_confidence:
            return
        try:
            for chunk in self._llm_json.stream([HumanMessage(content=prepared.prompt)]):
                if chunk.content:
                    yield chunk.content
        except Exception as exc:
            exc_str = str(exc)
            if "429" in exc_str:
                is_tpd = "tokens per day" in exc_str.lower() or "tpd" in exc_str.lower()
                print(f"[Orchestrator] Stream rate-limited ({'TPD' if is_tpd else 'TPM'}).")
            else:
                print(f"[Orchestrator] Stream error: {exc}")
            raise

    def parse_structured(self, raw: str, prepared: PreparedQuery) -> CernaResponse:
        """
        Parse accumulated JSON tokens into a CernaResponse, applying safety checks.
        Use after consuming stream_json_tokens().
        """
        if prepared.refusal:
            return CernaResponse(
                direct_answer=prepared.refusal,
                context_explanation="",
                step_by_step=[],
                best_practices=[],
                recommendations="",
                confidence="low",
            )
        if prepared.low_confidence:
            return CernaResponse(**_LOW_CONFIDENCE_RESPONSE_DICT)
        if not raw.strip():
            return CernaResponse(**_LOW_CONFIDENCE_RESPONSE_DICT)
        return self._parse_and_apply_gates(raw, prepared)

    def generate_followups(
        self, query: str, response: str, history: list[dict]
    ) -> list[str]:
        """Generate 3 contextual follow-up questions."""
        return self._generate_followups(query, response, history)

    def run(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
        module_hint: Optional[str] = None,
    ) -> OrchestratorResponse:
        """Full blocking pipeline. Returns OrchestratorResponse with CernaResponse."""
        history = conversation_history or []
        prepared = self.prepare(query, history, module_hint)
        cerna_resp = self.generate_structured(prepared)
        response_text = cerna_resp.to_markdown()
        follow_ups = self.generate_followups(prepared.rewritten_query, response_text, history)

        return OrchestratorResponse(
            response=response_text,
            cerna_response=cerna_resp,
            classified_vertical=prepared.classification,
            sources=prepared.sources,
            retrieved_chunks=prepared.chunks,
            follow_ups=follow_ups,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _state_to_prepared(state: CernaState) -> PreparedQuery:
        """Convert the final CernaState to the PreparedQuery adapter type."""
        from state import dict_to_chunk

        raw_chunks = state.get("final_chunks") or []
        chunks = [dict_to_chunk(d) for d in raw_chunks]

        return PreparedQuery(
            prompt=state.get("prompt", ""),
            classification=state.get("classification", CERNER_GENERAL),
            chunks=chunks,
            sources=state.get("sources", []),
            rewritten_query=state.get("formal_query") or state.get("original_query", ""),
            low_confidence=state.get("low_confidence", False),
            refusal=state.get("refusal", ""),
            citation_warning=state.get("citation_warning", False),
            intent=state.get("intent", "question"),
            formal_query=state.get("formal_query", ""),
            did_you_mean=state.get("did_you_mean", []),
            _state=state,
        )

    def _parse_and_apply_gates(self, raw: str, prepared: PreparedQuery) -> CernaResponse:
        """Parse JSON and apply the citation-warning confidence downgrade."""
        try:
            resp = CernaResponse.parse(raw)
        except Exception as exc:
            print(f"[Orchestrator] JSON parse error: {exc}. Using raw text.")
            resp = CernaResponse(
                direct_answer=raw[:800],
                context_explanation="",
                step_by_step=[],
                best_practices=[],
                recommendations="",
                confidence="medium",
            )

        if prepared.citation_warning and resp.confidence == "high":
            resp = resp.model_copy(update={
                "confidence": "medium",
                "recommendations": (
                    resp.recommendations
                    + " Note: No retrieved source scored above the citation threshold "
                    "for this clinical/FHIR/Revenue Cycle query. "
                    "Verify against official uCern documentation before acting on it."
                ),
            })
        return resp

    def _generate_json_with_retry(self, prompt_text: str, max_retries: int = 3) -> str:
        """
        Invoke JSON-mode LLM with exponential backoff on TPM 429 errors.
        TPD (daily limit) errors are handled immediately with a friendly message.

        Note: for the streaming path this is bypassed — stream_json_tokens uses
        the raw LLM directly. For the blocking path (generate_structured) this
        adds resilience on top of the with_fallbacks() chain in step_generate.
        """
        last_exc = None
        for attempt in range(max_retries):
            try:
                result = self._llm_json.invoke([HumanMessage(content=prompt_text)])
                return result.content.strip()
            except Exception as exc:
                last_exc = exc
                exc_str = str(exc)
                if "429" in exc_str:
                    is_tpd = "tokens per day" in exc_str.lower() or "tpd" in exc_str.lower()
                    if is_tpd:
                        print("[Orchestrator] Daily token limit (TPD) exhausted.")
                        return json.dumps({
                            "direct_answer": (
                                "The Groq API's daily token quota has been exhausted. "
                                "Please wait until midnight UTC for the limit to reset."
                            ),
                            "context_explanation": "",
                            "step_by_step": [],
                            "best_practices": [],
                            "recommendations": "The free Groq tier resets at midnight UTC.",
                            "confidence": "low",
                        })
                    if attempt < max_retries - 1:
                        wait = 2 ** attempt
                        print(f"[Orchestrator] Rate-limited (TPM). Retrying in {wait}s...")
                        time.sleep(wait)
                        continue
                break
        return json.dumps({
            "direct_answer": f"Error generating response: {last_exc}",
            "context_explanation": "",
            "step_by_step": [],
            "best_practices": [],
            "recommendations": "Please try again later.",
            "confidence": "low",
        })


# ── Standalone test ───────────────────────────────────────────────────────────

def _test():
    orch = Orchestrator()

    test_queries = [
        ("How do I configure PowerChart patient lists?", [], None),
        ("What is the Cerner FHIR R4 authorization flow?",
         [{"role": "user", "content": "What is SMART on FHIR?"},
          {"role": "assistant", "content": "SMART on FHIR is..."}], "fhir"),
        ("How does charge capture work in Revenue Cycle?", [], None),
    ]

    for query, history, hint in test_queries:
        print("\n" + "=" * 70)
        print(f"QUERY     : {query}")
        result = orch.run(query, history, module_hint=hint)
        print(f"MODULE    : {result.classified_vertical}")
        if result.cerna_response:
            cr = result.cerna_response
            print(f"CONFIDENCE: {cr.confidence}")
            print(f"ANSWER    : {cr.direct_answer[:300]}")
        print(f"SOURCES   : {[s['source'] for s in result.sources[:3]]}")


if __name__ == "__main__":
    _test()
