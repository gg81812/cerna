# Cerna — Error Handling Matrix
**Day 2 Resilience · 2026-04-22**

---

## Primary LLM Path (safe_invoke_json)

| Error | HTTP | Retry | Backoff | Fallback | CB Record |
|-------|------|-------|---------|----------|-----------|
| Rate limit | 429 | Up to 3 | 1s / 3s / 9s | 8B model → static | Yes |
| Server error | 5xx | Up to 3 | 1s / 3s / 9s | 8B model → static | Yes |
| Bad request | 400 | None | — | 8B model → static | Yes |
| Auth error | 401/403 | None | — | 8B model → static | Yes |
| Timeout | — | None | — | 8B model → static | Yes |
| Other | — | None | — | 8B model → static | Yes |

**Circuit breaker:** 5 failures in 60s → Groq skipped for 120s (both primary and 8B paths). On re-close, failure counter resets.

---

## Fallback Chain

```
Primary LLM (70B, up to 3 attempts)
  ├─ Success → return content
  └─ All attempts fail
       ├─ Circuit NOT open → 8B fallback (1 attempt)
       │    ├─ Success → return content
       │    └─ Fail → record in CB
       └─ Circuit open OR 8B fails → _GRACEFUL_FALLBACK_JSON
```

`_GRACEFUL_FALLBACK_JSON` is a valid `CernaResponse`-shaped JSON with `confidence="low"` and a "try again" message. The UI renders it as a low-confidence card — not a crash.

---

## JSON Repair Chain (schemas.py:CernaResponse.parse)

| Repair step | What it fixes | Example |
|-------------|---------------|---------|
| Fence removal | `\`\`\`json...\`\`\`` wrapper | LLM adds markdown output despite JSON mode |
| Trailing comma removal | `,]` or `,}` | LLM adds trailing comma on last array element |
| Truncation repair | Missing `]` or `}` | LLM hits max_tokens mid-JSON |
| Pydantic defaults | Missing optional fields | LLM omits `step_by_step` for simple questions |

---

## Fast Pre-check Errors (query_rewriter.py)

Pre-check regex failures are instant (< 1ms). All return `QueryUnderstanding(intent="X")` directly — no LLM call on failure path. No retry needed.

If `understand_query()` LLM call fails (JSON parse error or exception), `_fallback(query)` is returned: intent="question", formal_query=original, is_ambiguous=True. This is a safe fail-open for the query rewriter only.

---

## Demo Impact

| Scenario | Behavior | UI Impact |
|----------|----------|-----------|
| Groq 429 during demo | 3 retries (1s/3s/9s), then 8B, then graceful fallback | Slow response (~15s), then low-confidence card |
| Groq 429 on pre-warmed query | Cache hit — no LLM call needed | < 100ms, no impact |
| Network drops mid-demo | All LLM calls fail; graceful fallback fires | Low-confidence card; cached queries still work |
| Circuit opens (5 failures) | 8B skipped, static fallback for 120s | Graceful fallback card for all queries for 2 min |

---

*Error handling matrix · Cerna Day 2 resilience · 2026-04-22*

---

## Live Validation — 2026-04-22

**Run:** 2026-04-22 11:50 UTC  |  **Result:** PASS

### Test A: Auth failure -> 8B fallback -> static graceful fallback

**Method:** Created `ChatGroq` with `groq_api_key='gsk_INVALID_KEY_FOR_TESTING...'`
and passed to `safe_invoke_json()`. Patched `llm.GROQ_API_KEY` to same invalid value
so the 8B fallback also fails. Verified result is `_GRACEFUL_FALLBACK_JSON`.

**Elapsed:** 1470ms
**Result is graceful fallback:** True
**`[LLM] error` logged:** True
**`final_fallback` logged:** True

**Log output:**
```
[LLM] error category='auth_error' status=401 attempt=1 ts=2026-04-22T11:50:57.009932+00:00 query='BCMA test'
[LLM] error category='auth_error' status=401 attempt=0 ts=2026-04-22T11:50:58.479902+00:00 query='BCMA test'
[LLM] final_fallback ts=2026-04-22T11:50:58.479997+00:00 query='BCMA test'
```

**Result:** PASS

### Test B: Circuit breaker opens -> primary + 8B skipped

**Method:** Injected 5 failure timestamps into `_cb_failures` list, then called
`_cb_record_failure()` to trigger open condition. Verified `_cb_is_open() == True`.
Then ran `safe_invoke_json()` with a valid primary LLM — expected skip and static fallback.

**Circuit opened after 5 injected failures:** True
**`circuit_breaker open` skipped primary:** True
**Result is graceful fallback:** True
**Elapsed (no LLM calls):** 0ms

**Log output:**
```
[LLM] circuit_breaker open — skipping primary model; query='CB test'
[LLM] final_fallback ts=2026-04-22T11:50:59.489811+00:00 query='CB test'
```

**Result:** PASS

### Summary

| Test | Scenario | Result |
|------|----------|--------|
| A | Auth failure (invalid key) -> 8B fail -> static fallback | PASS |
| B | Circuit breaker opens after 5 failures -> skips primary + 8B | PASS |

Fallback chain verified: the pipeline never crashes on LLM failure. Users receive
a `confidence=low` card with a 'try again' message, not an exception trace.

*Live validation · `scripts/test_error_fallback.py` · 2026-04-22 11:50 UTC*
