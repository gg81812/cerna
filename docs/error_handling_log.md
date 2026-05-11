# Error Handling Wrap — Implementation and Test Log
**Date:** 2026-04-22  
**Phase:** 2 · Week 5 (mid-review Day 2 hardening)  
**Files changed:** `llm.py`, `pipeline.py`

---

## What Was Done

### Problem Being Fixed
The primary Groq LLM call had no explicit error handling. When Groq returned a 400 error (bad request — typically triggered by the JSON mode requirement that the prompt contain the word "json"), the error could bleed into the UI as a raw exception or an incorrect message. This occurred in at least one observed session.

### Implementation

**`llm.py` — `safe_invoke_json(llm, messages, query_hint="")`**

New function that wraps any LangChain LLM `.invoke()` call with:

| Error | Category | Retry? | Action |
|-------|----------|--------|--------|
| HTTP 429 | `rate_limit` | Yes — once after 2 s | Retry, then fallback |
| HTTP 5xx | `server_error` | Yes — once after 2 s | Retry, then fallback |
| HTTP 400 | `bad_request` | No | Log + fallback immediately |
| HTTP 401/403 | `auth_error` | No | Log + fallback immediately |
| Timeout | `timeout` | No | Log + fallback immediately |
| Other | `unknown` | No | Log + fallback immediately |

On final failure: returns `_GRACEFUL_FALLBACK_JSON` — a valid CernaResponse JSON with:
```json
{
  "direct_answer": "Cerna is temporarily unable to generate a detailed response. Please try your question again in a moment, or rephrase it.",
  "context_explanation": "",
  "step_by_step": [],
  "best_practices": [],
  "recommendations": "If this persists, try rephrasing your question with specific Cerner terminology, or search uCern (cernercentral.com) directly.",
  "confidence": "low"
}
```

Every error and every fallback is logged to stdout with: category, HTTP status, attempt number, timestamp, and masked query.

**`pipeline.py` — `make_step_generate`**

Replaced the LCEL `.with_fallbacks([llm_fast_json, _graceful])` chain with a direct call to `safe_invoke_json(llm_json, messages, query_hint=query_hint)`. The old chain would try the 8B model as a second fallback, then return a "daily token quota exhausted" message regardless of the actual error. The new wrap returns a more accurate message and has retry logic for transient errors.

---

## Test Scenarios

The following 5 failure injections were designed to validate the wrap. Each was verified by code analysis since live injection of infrastructure failures requires mock infrastructure not available in this environment. The verification notes describe what the code path produces for each scenario.

### Test 1 — Expired API Key (simulates HTTP 401)

**Scenario:** Groq returns 401 Unauthorized (expired or invalid API key).

**Code path:**
- `_classify_error(exc)` → `status_code=401` → category `"auth_error"`
- Attempt 1: logs `[LLM] error category='auth_error' status=401 attempt=1 ts=... query=...`
- No retry (auth errors don't benefit from retry)
- Returns `_GRACEFUL_FALLBACK_JSON`
- `step_parse` receives `raw_llm_response = _GRACEFUL_FALLBACK_JSON`
- `CernaResponse.parse()` succeeds — valid JSON → `confidence="low"`, graceful message rendered

**Expected UI:** Clean low-confidence response card. No raw exception. No stack trace.

**Verification:** ✅ Code path confirmed by inspection.

---

### Test 2 — Corrupt JSON Response from LLM

**Scenario:** Groq returns HTTP 200 but content is malformed JSON (e.g., truncated or missing closing brace).

**Code path:**
- `safe_invoke_json` returns successfully (HTTP 200 — no exception raised by LLM)
- `step_generate` sets `raw_llm_response` to the corrupt string
- `step_parse` calls `CernaResponse.parse(raw)` → raises `json.JSONDecodeError` or Pydantic `ValidationError`
- `step_parse` catches the exception (lines 714–727 in pipeline.py) → falls back to raw text truncated at 800 chars with `confidence="medium"`

**Expected UI:** Response card renders with `direct_answer` showing the raw text, `confidence="medium"`. Not a crash.

**Verification:** ✅ Code path confirmed. `step_parse` already has this fallback (pre-existing, not new code).

---

### Test 3 — Empty Response from LLM

**Scenario:** Groq returns HTTP 200 with empty content string.

**Code path:**
- `safe_invoke_json` calls `result.content.strip()` → returns `""` (non-None)
- `step_generate` sets `raw_llm_response = ""`
- `step_parse`: `raw = state.get("raw_llm_response", "")` → `if not raw.strip(): resp = _LOW_CONFIDENCE_RESPONSE_DICT.copy()`
- Returns `_LOW_CONFIDENCE_RESPONSE_DICT` with `confidence="low"`

**Expected UI:** Clean low-confidence response card ("I don't have sufficient information...").

**Verification:** ✅ Code path confirmed. `step_parse` already handles empty response (pre-existing).

---

### Test 4 — Network Timeout

**Scenario:** Request to Groq times out (e.g., Groq server unresponsive, network drop).

**Code path:**
- `safe_invoke_json` → `llm.invoke(messages)` raises a timeout exception (e.g., `httpx.TimeoutException`, `groq.APITimeoutError`)
- `_classify_error(exc)`: `status_code` attribute not present → checks name/str for "timeout" → category `"timeout"`, status `0`
- Attempt 1: logs `[LLM] error category='timeout' status=0 attempt=1 ts=...`
- No retry (timeouts are not typically transient on the first retry)
- Returns `_GRACEFUL_FALLBACK_JSON`

**Expected UI:** Clean low-confidence response card. Graceful message: "Cerna is temporarily unable to generate a detailed response."

**Verification:** ✅ Code path confirmed by inspection.

---

### Test 5 — Prompt Missing 'json' Keyword in JSON Mode (HTTP 400)

**Scenario:** Groq JSON mode requires the prompt to contain the word "json". If the prompt is modified (e.g., a future template change removes this) and the requirement is not met, Groq returns HTTP 400.

**Code path:**
- `safe_invoke_json` → LLM raises exception with `status_code=400`
- `_classify_error(exc)` → category `"bad_request"`, status `400`
- Attempt 1: logs `[LLM] error category='bad_request' status=400 attempt=1 ts=...`
- No retry (400 is a client error — retrying the same prompt will fail again)
- Returns `_GRACEFUL_FALLBACK_JSON`
- UI renders graceful low-confidence card

**Expected UI:** Clean low-confidence response card. **This is the specific scenario that previously caused the Groq 400 to bleed into the UI. It is now caught and rendered gracefully.**

**Verification:** ✅ Code path confirmed. This is the primary fix target for Day 2.

---

## Key Design Decisions

1. **No 8B fallback model.** The old `.with_fallbacks([llm_fast_json, _graceful])` chain tried the 8B model before giving up. This was removed because: (a) if the 70B fails on a 400, the 8B will also fail on the same 400 (same prompt issue); (b) the graceful response is a cleaner user experience than a degraded 8B answer on a rate-limited session. Post-mid-review: add back if GPT-5.4 mini transition makes 8B moot.

2. **Retry only on transient errors.** 429 and 5xx are transient — a single 2s pause is often sufficient for rate limit windows or brief server hiccups. 400, 401, and timeout are not transient and don't benefit from retry.

3. **Masked query in logs.** Every error log entry calls `mask_pii()` on the query hint before printing. PII does not appear in error logs.

4. **No circuit breaker.** Circuit breaker is a post-mid-review item. The 2s retry window is sufficient protection for a demo context.

---

*Implementation: 2026-04-22 · Phase 2 Week 5 mid-review hardening · files: llm.py, pipeline.py*
