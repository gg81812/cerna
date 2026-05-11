"""
app.py — Cerna: Cerner AI Specialist  (Phase 2 · Week 5 POV)

Run:
    streamlit run app.py
    streamlit run app.py -- ?health=1   # JSON health check (returns HTTP 200 if store up)
"""

import os
import time
import uuid

_VERSION = "0.5.0"

import streamlit as st

from config import CHROMA_DIR
from logger import log_interaction
from cache import get as cache_get, set as cache_set
from schemas import CernaResponse
from ui.styles import inject_global_css, inject_admin_panel
import ui.components as comp

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cerna",
    page_icon="🟣",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Guard: require ingested vector store ──────────────────────────────────────
if not os.path.isdir(CHROMA_DIR):
    st.error(
        "**Vector store not found.**\n\n"
        "Run ingestion first:\n```\npython ingest.py\nstreamlit run app.py\n```"
    )
    st.stop()

# ── Cached resources ──────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_orchestrator():
    from orchestrator import Orchestrator
    return Orchestrator()


@st.cache_resource(show_spinner=False)
def get_doc_counts() -> dict:
    # Reuse the orchestrator's already-loaded retriever — avoids a second
    # embedding model load and BM25 index build on startup.
    return get_orchestrator()._retriever.get_document_count()


# ── Module classification → session-state key mapping ────────────────────────
_CLASSIFICATION_TO_KEY: dict[str, str | None] = {
    "MILLENNIUM":    "millennium",
    "POWERCHART":    "powerchart",
    "REVENUE_CYCLE": "revenue_cycle",
    "FHIR":          "fhir",
    "CLINICAL":      "clinical",
    "GENERAL":       None,
}

# ── Session state init ────────────────────────────────────────────────────────
def _init_state() -> None:
    defaults: dict = {
        "messages":        [],
        "pending_prompt":  None,
        "last_module":     None,
        "active_module":   None,
        "avatar_speaking": False,
        "session_id":      str(uuid.uuid4()),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()

# ── Inject CSS (once) ─────────────────────────────────────────────────────────
inject_global_css()

# ── KB counts — loaded lazily so the page renders before models initialise ────
kb_counts = st.session_state.get("_kb_counts", {})

_TYPING_HTML = (
    '<div class="typing-card">'
    '<span></span><span></span><span></span>'
    '</div>'
)

# ── Two-column layout ─────────────────────────────────────────────────────────
col_l, col_c = st.columns([0.34, 0.66], gap="small")

with col_l:
    comp.render_left_panel(
        is_speaking=st.session_state.avatar_speaking,
        active_module=st.session_state.active_module,
        kb_counts=kb_counts,
    )

    # Collapsible starter-prompts dropdown lives in the left panel, styled
    # to match the dark purple background. Hidden once the user sends a message.
    comp.render_starter_grid()

    # Knowledge-articles footer rendered after the dropdown so it stays
    # at the bottom of the left panel visual hierarchy.
    comp.render_left_footer(kb_counts)

with col_c:
    # Header + module filter
    comp.render_top_bar()

    # Chat input — pinned to the top of the conversation area
    with st.form("chat_input_form", clear_on_submit=True, border=False):
        ti_col, btn_col = st.columns([0.88, 0.12])
        with ti_col:
            user_input = st.text_input(
                "Ask Cerna",
                placeholder="Ask about Cerner workflows, configurations, integrations…",
                label_visibility="collapsed",
                key="chat_text_input",
            )
        with btn_col:
            submitted = st.form_submit_button("Send", use_container_width=True)
    if not submitted:
        user_input = None

    # Chat transcript (all stored messages)
    comp.render_chat(st.session_state.messages)

    # ── Structured generation with streaming ─────────────────────────────────
    if st.session_state.avatar_speaking and st.session_state.messages:
        last = st.session_state.messages[-1]
        if last["role"] == "user":
            query = last["content"]
            _model_status = st.empty()
            _model_status.markdown(
                '<div class="stream-status">⚙️ Initialising Cerna AI models…</div>',
                unsafe_allow_html=True,
            )
            orch = get_orchestrator()
            _model_status.empty()

            # Populate KB counts the first time the orchestrator is ready
            if "_kb_counts" not in st.session_state:
                try:
                    st.session_state["_kb_counts"] = orch._retriever.get_document_count()
                except Exception:
                    st.session_state["_kb_counts"] = {}

            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
                if m["role"] in ("user", "assistant")
            ]

            t0 = time.time()
            active_module = st.session_state.active_module

            # Cache check — skip retrieval + LLM on hit
            cached_json = cache_get(query, active_module)
            prepared = None
            if cached_json:
                try:
                    cerna_resp = CernaResponse.parse(cached_json)
                except Exception:
                    cached_json = None

            if not cached_json:
                # Phase 1 — retrieval status
                _status = st.empty()
                _status.markdown(
                    '<div class="stream-status">🔍 Searching Cerner knowledge base…</div>',
                    unsafe_allow_html=True,
                )
                prepared = orch.prepare(query, history, module_hint=active_module)

                # Phase 2 — streaming LLM generation
                _status.markdown(
                    '<div class="stream-status">⚡ Generating response…</div>',
                    unsafe_allow_html=True,
                )
                _typing = st.empty()
                _typing.markdown(_TYPING_HTML, unsafe_allow_html=True)

                # Refusal path — casual greeting, OOS, or clinical decision
                if prepared.refusal:
                    from schemas import CernaResponse as _CR
                    cerna_resp = _CR(
                        direct_answer=prepared.refusal,
                        context_explanation="",
                        step_by_step=[],
                        best_practices=[],
                        recommendations="",
                        confidence="high" if prepared.intent == "casual" else "low",
                    )
                    follow_ups = []

                # "Did you mean" path — retrieval was too weak; surface suggestions
                # as chips without calling the LLM at all.
                elif prepared.did_you_mean:
                    from schemas import CernaResponse as _CR
                    cerna_resp = _CR(
                        direct_answer=(
                            "I'm not sure which Cerner topic you're asking about. "
                            "Here are some related searches — click one to get a full answer:"
                        ),
                        context_explanation="",
                        step_by_step=[],
                        best_practices=[],
                        recommendations=(
                            "You can also try rephrasing your question with specific "
                            "Cerner module names, or search uCern (cernercentral.com)."
                        ),
                        confidence="low",
                    )
                    follow_ups = prepared.did_you_mean
                else:
                    raw_json = ""
                    try:
                        for token in orch.stream_json_tokens(prepared):
                            raw_json += token
                        cerna_resp = orch.parse_structured(raw_json, prepared)
                    except Exception:
                        cerna_resp = orch.generate_structured(prepared)

                    follow_ups = orch.generate_followups(
                        prepared.rewritten_query, cerna_resp.direct_answer, history
                    )
                    cache_set(query, active_module, cerna_resp.model_dump_json())

                _status.empty()
                _typing.empty()
            else:
                follow_ups = orch.generate_followups(query, cerna_resp.direct_answer, history)

            latency_ms = int((time.time() - t0) * 1000)

            sources         = prepared.sources if prepared else []
            chunks          = prepared.chunks  if prepared else []
            classification  = prepared.classification  if prepared else "GENERAL"
            rewritten_query = prepared.rewritten_query if prepared else query
            refusal         = prepared.refusal         if prepared else ""

            # Render the response card immediately (before rerun, in chat flow)
            comp.render_cerna_response(cerna_resp, sources, classification=classification)

            comp.render_followups(follow_ups, len(st.session_state.messages))

            entry_id = log_interaction(
                query=query,
                classified_vertical=classification,
                retrieved_chunks=chunks,
                response=cerna_resp.to_markdown(),
                latency_ms=latency_ms,
                session_id=st.session_state.session_id,
                rewritten_query=rewritten_query,
                confidence=cerna_resp.confidence,
                refusal_flag=bool(refusal),
                refusal_reason=refusal,
                cache_hit=bool(cached_json),
                intent=getattr(prepared, "intent", "question") if prepared else "question",
                formal_query=getattr(prepared, "formal_query", "") if prepared else "",
                query_variants=getattr(prepared, "did_you_mean", []) if prepared else [],
            )

            st.session_state.messages.append({
                "role":           "assistant",
                "content":        cerna_resp.to_markdown(),
                "cerna_response": cerna_resp,
                "sources":        sources,
                "vertical":       classification,
                "entry_id":       entry_id,
                "follow_ups":     follow_ups,
            })
            st.session_state.last_module     = _CLASSIFICATION_TO_KEY.get(classification)
            st.session_state.avatar_speaking = False
            st.rerun()

    # Clinical disclaimer footer for the conversation area
    st.markdown(
        '<div style="text-align:center;font-size:0.58rem;color:#9CA3AF;margin-top:0.5rem;padding:0 1rem;">'
        'Cerna is an AI assistant for Cerner implementation guidance only. '
        'Not a clinical decision tool — always consult a licensed clinician.</div>',
        unsafe_allow_html=True,
    )

# ── Input routing ─────────────────────────────────────────────────────────────
final_input: str | None = None
if st.session_state.pending_prompt:
    final_input = st.session_state.pending_prompt
    st.session_state.pending_prompt = None
elif user_input and user_input.strip():
    final_input = user_input.strip()

if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    st.session_state.avatar_speaking = True
    st.rerun()

# ── Admin view (gated by ?admin=1 in URL) ────────────────────────────────────
params = st.query_params
if params.get("admin") == "1":
    from cache import stats as cache_stats
    from logger import get_recent_logs
    inject_admin_panel(cache_stats(), get_recent_logs(20))

# ── Health check (gated by ?health=1 in URL) ─────────────────────────────────
if params.get("health") == "1":
    chroma_ok = os.path.isdir(CHROMA_DIR)
    try:
        doc_counts = get_doc_counts()
        chunk_total = sum(doc_counts.values()) if doc_counts else 0
        store_ok = chunk_total > 0
    except Exception:
        store_ok = False
        chunk_total = 0

    try:
        from redis_client import health_check as _redis_health
        _redis_info = _redis_health()
    except Exception:
        _redis_info = {"redis": "unavailable"}

    try:
        from cache import stats as _cache_stats
        _cache_info = _cache_stats()
    except Exception:
        _cache_info = {}

    try:
        from llm import get_circuit_breaker_state as _cb_state
        _cb_info = _cb_state()
    except Exception:
        _cb_info = {}

    try:
        from groq_pool import get_pool as _get_pool
        _quota_info = _get_pool().quota_info()
    except Exception:
        _quota_info = []

    health = {
        "status":           "ok" if (chroma_ok and store_ok) else "degraded",
        "version":          _VERSION,
        "chroma_dir_exists": chroma_ok,
        "chunk_total":      chunk_total,
        "redis":            _redis_info,
        "cache":            _cache_info,
        "circuit_breaker":  _cb_info,
        "groq_keys":        _quota_info,
    }
    st.json(health)
    st.stop()

# ── Quota admin view (gated by ?admin=1&view=quota) ───────────────────────────
if params.get("admin") == "1" and params.get("view") == "quota":
    import pandas as pd
    from llm import get_circuit_breaker_state as _cb_state
    from cache import stats as _cache_stats
    from redis_client import health_check as _redis_health

    st.title("Cerna — Operational Dashboard")
    st.caption("Refresh page to update. Data sourced from Redis.")

    col1, col2, col3 = st.columns(3)

    # Redis status
    _ri = _redis_health()
    _redis_status = _ri.get("redis", "unknown")
    col1.metric("Redis", _redis_status.upper(), delta=None)

    # Cache stats
    _cs = _cache_stats()
    col2.metric("Cache Hit Rate", f"{_cs.get('hit_rate_pct', 0.0):.1f}%")
    col3.metric("Cache Backend", _cs.get("backend", "—").upper())

    st.divider()

    # Circuit breaker
    st.subheader("Circuit Breaker")
    _cb = _cb_state()
    _cb_state_str = _cb.get("state", "unknown").upper()
    _cb_cols = st.columns(3)
    _cb_cols[0].metric("State", _cb_state_str)
    _cb_cols[1].metric("Recent Failures", _cb.get("failures_recent", 0))
    _cb_cols[2].metric("Closes In (s)", _cb.get("seconds_until_close", 0))

    st.divider()

    # Groq key quota
    st.subheader("Groq Key Quota — Today")
    try:
        from groq_pool import get_pool as _get_pool
        _qi = _get_pool().quota_info()
    except Exception:
        _qi = []

    if _qi:
        _df = pd.DataFrame(_qi)
        _df = _df.rename(columns={
            "key_id": "Key ID",
            "requests_today": "Requests Today",
            "daily_limit": "Daily Limit",
            "pct_used": "% Used",
            "blocked": "Blocked",
            "blocked_ttl_s": "Blocked TTL (s)",
        })
        st.dataframe(_df, use_container_width=True)

        # Usage bar chart
        _chart_data = pd.DataFrame({
            "Key": [r["key_id"] for r in _qi],
            "Requests": [r["requests_today"] for r in _qi],
            "Limit (95%)": [int(r["daily_limit"] * 0.95) for r in _qi],
        }).set_index("Key")
        st.bar_chart(_chart_data[["Requests"]])
    else:
        st.info("No quota data available (Redis unreachable or no keys configured).")

    st.divider()
    st.caption(f"Cerna v{_VERSION} · Admin view · Refresh to update")
    st.stop()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="text-align:center;font-size:0.55rem;color:#6B7280;margin-top:1rem;">'
    f'Cerna v{_VERSION} · Accenture Oracle Health POV · Not a clinical decision tool'
    f'</div>',
    unsafe_allow_html=True,
)
