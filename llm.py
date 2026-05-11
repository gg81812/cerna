"""
llm.py — Single LLM factory for Cerna. All LLM calls go through this file.

To migrate from Groq → GPT-5.4 mini (planned production, Week 5):
  1. pip install langchain-openai
  2. Set OPENAI_API_KEY in .env
  3. Replace ChatGroq with ChatOpenAI below; model = "gpt-5.4-mini"
  4. JSON mode: use model_kwargs={"response_format": {"type": "json_object"}}
     OR switch to native function calling (preferred for GPT-5.4 mini).
  Note: GROQ_MODEL_FAST → gpt-5.4-nano or o4-mini for classification/safety calls.
"""

import json
import threading
import time
from datetime import datetime, timezone

from langchain_groq import ChatGroq

from config import GROQ_API_KEY, GROQ_MODEL, GROQ_MODEL_FAST, LLM_TEMPERATURE

# ── Pool key helpers (imported lazily to avoid circular imports) ──────────────

def _pool_acquire() -> tuple:
    """Return (key_id, api_key) from the pool, or (None, GROQ_API_KEY) on error."""
    try:
        from groq_pool import get_pool
        kid, key = get_pool().acquire()
        if key:
            return kid, key
    except Exception:
        pass
    return None, GROQ_API_KEY


def _pool_record(key_id) -> None:
    if key_id is None:
        return
    try:
        from groq_pool import get_pool
        get_pool().record_usage(key_id)
    except Exception:
        pass


def _pool_block(key_id) -> None:
    if key_id is None:
        return
    try:
        from groq_pool import get_pool
        get_pool().mark_blocked(key_id)
    except Exception:
        pass


def _llm_with_key(llm, api_key: str):
    """Clone an existing ChatGroq instance with a different API key."""
    return ChatGroq(
        model=getattr(llm, "model", GROQ_MODEL),
        groq_api_key=api_key,
        temperature=getattr(llm, "temperature", LLM_TEMPERATURE),
        max_tokens=getattr(llm, "max_tokens", None),
        model_kwargs=getattr(llm, "model_kwargs", None) or {},
    )

# Graceful fallback response returned when all LLM attempts fail.
# Matches the CernaResponse schema so the UI renders a clean low-confidence card.
_GRACEFUL_FALLBACK_JSON: str = json.dumps({
    "direct_answer": (
        "Cerna is temporarily unable to generate a detailed response. "
        "Please try your question again in a moment, or rephrase it."
    ),
    "context_explanation": "",
    "step_by_step": [],
    "best_practices": [],
    "recommendations": (
        "If this persists, try rephrasing your question with specific Cerner "
        "terminology, or search uCern (cernercentral.com) directly."
    ),
    "confidence": "low",
})


def get_llm() -> ChatGroq:
    """Return a standard ChatGroq instance for streaming / blocking generation."""
    return ChatGroq(
        model=GROQ_MODEL,
        groq_api_key=GROQ_API_KEY,
        temperature=LLM_TEMPERATURE,
    )


def get_llm_json() -> ChatGroq:
    """
    Return a ChatGroq instance with JSON mode enabled.
    Used by orchestrator for structured CernaResponse generation.
    The prompt MUST instruct the model to produce JSON (Groq requirement).
    """
    return ChatGroq(
        model=GROQ_MODEL,
        groq_api_key=GROQ_API_KEY,
        temperature=LLM_TEMPERATURE,
        max_tokens=2000,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


def get_llm_fast() -> ChatGroq:
    """Return a fast, low-cost model for classification, rewriting, and safety checks."""
    return ChatGroq(
        model=GROQ_MODEL_FAST,
        groq_api_key=GROQ_API_KEY,
        temperature=0.0,
        max_tokens=512,
    )


def get_llm_fast_json() -> ChatGroq:
    """
    Fast model with JSON mode — used by understand_query() for structured output.
    Prompt MUST contain the word 'json' (Groq requirement for JSON mode).
    """
    return ChatGroq(
        model=GROQ_MODEL_FAST,
        groq_api_key=GROQ_API_KEY,
        temperature=0.0,
        max_tokens=600,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


# ── Circuit breaker state (module-level, shared across calls) ────────────────

def get_circuit_breaker_state() -> dict:
    """Return a JSON-safe snapshot of circuit breaker state for health/admin endpoints."""
    import time as _time
    with _CB_LOCK:
        now = _time.time()
        is_open = bool(_cb_open_until and now < _cb_open_until)
        return {
            "state":           "open" if is_open else "closed",
            "failures_recent": len(_cb_failures),
            "failure_threshold": _CB_FAILURE_THRESHOLD,
            "open_until_epoch": _cb_open_until if is_open else None,
            "seconds_until_close": max(0, int(_cb_open_until - now)) if is_open else 0,
        }



_CB_LOCK = threading.Lock()
_cb_failures: list[float] = []   # timestamps of recent failures
_cb_open_until: float = 0.0       # epoch seconds; 0 = closed (normal operation)
_CB_FAILURE_WINDOW = 60           # seconds to count failures over
_CB_FAILURE_THRESHOLD = 5         # failures in window → open circuit
_CB_OPEN_DURATION = 120           # seconds to stay open before re-closing


def _cb_record_failure() -> None:
    global _cb_open_until
    now = time.time()
    with _CB_LOCK:
        _cb_failures.append(now)
        cutoff = now - _CB_FAILURE_WINDOW
        while _cb_failures and _cb_failures[0] < cutoff:
            _cb_failures.pop(0)
        if len(_cb_failures) >= _CB_FAILURE_THRESHOLD:
            _cb_open_until = now + _CB_OPEN_DURATION
            print(
                f"[LLM] circuit_breaker OPEN — {len(_cb_failures)} failures in "
                f"{_CB_FAILURE_WINDOW}s; skipping Groq for {_CB_OPEN_DURATION}s"
            )


def _cb_is_open() -> bool:
    global _cb_open_until
    with _CB_LOCK:
        if _cb_open_until and time.time() < _cb_open_until:
            return True
        if _cb_open_until and time.time() >= _cb_open_until:
            _cb_open_until = 0.0
            _cb_failures.clear()
            print("[LLM] circuit_breaker CLOSED — resuming normal operation")
        return False


# ── Safe invocation with exponential backoff, 8B fallback, circuit breaker ───

# Retry delays for transient failures (429, 5xx)
_RETRY_DELAYS = (1, 3, 9)  # seconds; up to 3 attempts total


def _classify_error(exc: Exception) -> tuple[str, int]:
    """Return (category, http_status) from a Groq/LangChain exception."""
    status: int = getattr(exc, "status_code", 0)
    if status == 429:
        return "rate_limit", status
    elif 500 <= status < 600:
        return "server_error", status
    elif status == 400:
        return "bad_request", status
    elif status in (401, 403):
        return "auth_error", status
    elif "timeout" in type(exc).__name__.lower() or "timeout" in str(exc).lower():
        return "timeout", 0
    return "unknown", status


def _log_llm_error(
    category: str, status: int, query_hint: str, timestamp: str, attempt: int
) -> None:
    try:
        from pii_guard import mask_pii
        safe_q = mask_pii(query_hint[:100])
    except Exception:
        safe_q = query_hint[:100]
    print(
        f"[LLM] error category={category!r} status={status} "
        f"attempt={attempt} ts={timestamp} query={safe_q!r}"
    )


def _invoke_with_backoff(
    llm, messages: list, query_hint: str = "", key_id=None
) -> str | None:
    """
    Try up to 3 attempts with exponential backoff (1s/3s/9s) on 429/5xx.
    Returns content string on success, None on final failure.
    Records failures in the circuit breaker on each error.
    On 429, also marks the pool key blocked for 60 s (key_id param).
    """
    for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
        ts = datetime.now(timezone.utc).isoformat()
        try:
            result = llm.invoke(messages)
            return result.content.strip()
        except Exception as exc:
            category, status = _classify_error(exc)
            _log_llm_error(category, status, query_hint, ts, attempt)
            _cb_record_failure()
            if category == "rate_limit":
                _pool_block(key_id)
            if category not in ("rate_limit", "server_error") or attempt == len(_RETRY_DELAYS):
                return None
            time.sleep(delay)
    return None


def safe_invoke_json(llm, messages: list, query_hint: str = "") -> str:
    """
    Invoke an LLM with exponential backoff (3 retries: 1s/3s/9s), a circuit
    breaker (5 failures in 60s → skip Groq for 2 min), an 8B fast-model fallback,
    and a final static graceful fallback.

    Fallback chain:
      1. Primary LLM — up to 3 attempts with backoff (pool key selected)
      2. 8B fast-model (llama-3.1-8b-instant) — 1 attempt; skipped if circuit open
      3. _GRACEFUL_FALLBACK_JSON — always available, no network

    Non-retryable errors (400, 401, 403, timeout) skip directly to fallback chain.
    Pool key selection: lowest-quota key is preferred; 429 blocks that key for 60 s.
    """
    # Select a pool key and rebuild the LLM if a different key was chosen.
    key_id, pool_key = _pool_acquire()
    active_llm = _llm_with_key(llm, pool_key) if pool_key else llm

    # Check circuit breaker before primary call
    if _cb_is_open():
        print(f"[LLM] circuit_breaker open — skipping primary model; query={query_hint[:40]!r}")
    else:
        raw = _invoke_with_backoff(active_llm, messages, query_hint, key_id=key_id)
        if raw is not None:
            _pool_record(key_id)
            return raw

    # 8B fallback: only if circuit is not open (circuit tracks overall Groq health)
    if not _cb_is_open():
        fb_key_id, fb_pool_key = _pool_acquire()
        fb_api_key = fb_pool_key or GROQ_API_KEY
        try:
            llm_8b = ChatGroq(
                model=GROQ_MODEL_FAST,
                groq_api_key=fb_api_key,
                temperature=LLM_TEMPERATURE,
                max_tokens=2000,
                model_kwargs={"response_format": {"type": "json_object"}},
            )
            ts = datetime.now(timezone.utc).isoformat()
            result = llm_8b.invoke(messages)
            _pool_record(fb_key_id)
            print(f"[LLM] 8b_fallback succeeded ts={ts}")
            return result.content.strip()
        except Exception as exc:
            category, status = _classify_error(exc)
            ts = datetime.now(timezone.utc).isoformat()
            _log_llm_error(category, status, query_hint, ts, 0)
            _cb_record_failure()
            if category == "rate_limit":
                _pool_block(fb_key_id)

    ts = datetime.now(timezone.utc).isoformat()
    try:
        from pii_guard import mask_pii
        safe_q = mask_pii(query_hint[:80])
    except Exception:
        safe_q = query_hint[:80]
    print(f"[LLM] final_fallback ts={ts} query={safe_q!r}")
    return _GRACEFUL_FALLBACK_JSON


# ── Fast (8B) JSON-mode invocation with pool key rotation ────────────────────

def safe_invoke_fast_json(
    messages: list, query_hint: str = "", max_tokens: int = 600
) -> str | None:
    """
    Invoke the 8B fast LLM in JSON mode with pool key rotation, exponential
    backoff (1s/3s/9s on 429/5xx), and circuit-breaker integration.

    Returns the raw content string on success, or None on total failure —
    callers choose their own fallback (e.g. understand_query() returns a
    minimal QueryUnderstanding via `_fallback()` rather than the
    CernaResponse-shaped graceful fallback).

    Mirrors safe_invoke_json() but for the 8B model: same pool, same
    backoff, same circuit breaker, no 70B fallback (8B IS the fallback
    target in safe_invoke_json's chain).
    """
    if _cb_is_open():
        print(
            f"[LLM] circuit_breaker open — skipping fast 8B; query={query_hint[:40]!r}"
        )
        return None

    key_id, pool_key = _pool_acquire()
    api_key = pool_key or GROQ_API_KEY
    llm = ChatGroq(
        model=GROQ_MODEL_FAST,
        groq_api_key=api_key,
        temperature=0.0,
        max_tokens=max_tokens,
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    raw = _invoke_with_backoff(llm, messages, query_hint, key_id=key_id)
    if raw is not None:
        _pool_record(key_id)
        return raw
    return None
