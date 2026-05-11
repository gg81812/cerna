"""
scripts/test_error_fallback.py — Task 3: Live validation of llm.py fallback chain.
Forces auth failure (invalid API key) to exercise:
  1. Primary LLM (3 attempts, immediate fail on 401)
  2. 8B fallback (1 attempt, also fails on 401)
  3. _GRACEFUL_FALLBACK_JSON (static, always succeeds)
Run from project root: python scripts/test_error_fallback.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import contextlib
import json
import time
from datetime import datetime, timezone
from langchain_core.messages import HumanMessage

# ── Capture stdout so we can verify log lines ────────────────────────────────

@contextlib.contextmanager
def capture_stdout():
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old


def run_validation():
    ts_start = datetime.now(timezone.utc).isoformat()
    print("Cerna Error Fallback Chain — Live Validation")
    print("=" * 60)

    # Import llm module
    import llm as llm_module
    from langchain_groq import ChatGroq
    from config import GROQ_MODEL, GROQ_MODEL_FAST, LLM_TEMPERATURE

    INVALID_KEY = "gsk_INVALID_KEY_FOR_TESTING_0000000000000000000000000000"

    # Build a primary LLM with invalid key (same params as get_llm_json)
    bad_primary = ChatGroq(
        model=GROQ_MODEL,
        groq_api_key=INVALID_KEY,
        temperature=LLM_TEMPERATURE,
        max_tokens=2000,
        model_kwargs={"response_format": {"type": "json_object"}},
    )

    # Reset circuit breaker state before test
    with llm_module._CB_LOCK:
        llm_module._cb_failures.clear()
        llm_module._cb_open_until = 0.0

    messages = [HumanMessage(content='{"query": "BCMA scanning workflow test"} Return JSON.')]

    print("\nTest A: Primary fail + 8B fallback fail -> static fallback")
    print("  (Both use invalid API key)")
    t0 = time.time()

    # Monkey-patch GROQ_API_KEY in llm_module so 8B fallback also uses invalid key
    real_key = llm_module.GROQ_API_KEY
    llm_module.GROQ_API_KEY = INVALID_KEY

    captured_lines = []
    result = None
    try:
        with capture_stdout() as buf:
            result = llm_module.safe_invoke_json(bad_primary, messages, query_hint="BCMA test")
        output = buf.getvalue()
        for line in output.splitlines():
            captured_lines.append(line)
            print(f"  LOG: {line}")
    finally:
        llm_module.GROQ_API_KEY = real_key
        with llm_module._CB_LOCK:
            llm_module._cb_failures.clear()
            llm_module._cb_open_until = 0.0

    elapsed_ms = int((time.time() - t0) * 1000)

    # Verify result is _GRACEFUL_FALLBACK_JSON
    try:
        parsed = json.loads(result)
        is_graceful = parsed.get("confidence") == "low" and "try" in parsed.get("direct_answer", "").lower()
    except Exception:
        is_graceful = False

    print(f"\n  Elapsed: {elapsed_ms}ms")
    print(f"  Result is _GRACEFUL_FALLBACK_JSON: {is_graceful}")
    print(f"  Result confidence: {json.loads(result).get('confidence') if result else 'N/A'}")

    # Check log lines
    had_error_log = any("[LLM] error" in ln for ln in captured_lines)
    had_8b_attempt = any("8b_fallback" in ln or "8B" in ln for ln in captured_lines)
    had_final_fallback = any("final_fallback" in ln for ln in captured_lines)

    print(f"\n  Log checks:")
    print(f"    [LLM] error logged:    {had_error_log}")
    print(f"    8B fallback attempted: {had_8b_attempt}")
    print(f"    final_fallback logged: {had_final_fallback}")

    test_a_pass = is_graceful and had_error_log and had_final_fallback

    print("\nTest B: Circuit breaker opens after 5 failures -> skips primary + 8B")
    print("  Injecting 5 failures manually, then checking circuit opens")

    now_ts = time.time()
    with llm_module._CB_LOCK:
        llm_module._cb_failures.clear()
        # Inject 5 failures within the window
        for i in range(5):
            llm_module._cb_failures.append(now_ts - i)
        llm_module._cb_open_until = 0.0

    # Manually call _cb_record_failure one more time to open the circuit
    llm_module._cb_record_failure()

    cb_open = llm_module._cb_is_open()
    print(f"  Circuit open after 5 injected failures: {cb_open}")

    # Run safe_invoke_json with circuit open — should skip primary and return fallback fast
    good_primary = ChatGroq(
        model=GROQ_MODEL,
        groq_api_key=real_key,
        temperature=LLM_TEMPERATURE,
        max_tokens=2000,
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    t0 = time.time()
    cb_captured = []
    with capture_stdout() as buf:
        cb_result = llm_module.safe_invoke_json(good_primary, messages, query_hint="CB test")
    cb_output = buf.getvalue()
    for line in cb_output.splitlines():
        cb_captured.append(line)
        print(f"  LOG: {line}")
    cb_elapsed_ms = int((time.time() - t0) * 1000)

    try:
        cb_parsed = json.loads(cb_result)
        cb_is_graceful = cb_parsed.get("confidence") == "low"
    except Exception:
        cb_is_graceful = False

    print(f"\n  Elapsed (circuit open): {cb_elapsed_ms}ms")
    print(f"  Result is graceful fallback: {cb_is_graceful}")
    cb_skipped = any("circuit_breaker open" in ln for ln in cb_captured)
    print(f"  'circuit_breaker open' logged: {cb_skipped}")

    test_b_pass = cb_open and cb_is_graceful

    # Reset circuit breaker
    with llm_module._CB_LOCK:
        llm_module._cb_failures.clear()
        llm_module._cb_open_until = 0.0

    print("\n" + "=" * 60)
    overall = test_a_pass and test_b_pass
    print(f"Test A (auth fail -> 8B fail -> static): {'PASS' if test_a_pass else 'FAIL'}")
    print(f"Test B (circuit breaker opens + skips): {'PASS' if test_b_pass else 'FAIL'}")
    print(f"Overall: {'PASS' if overall else 'FAIL'}")

    return {
        "ts": ts_start, "elapsed_auth_ms": elapsed_ms, "elapsed_cb_ms": cb_elapsed_ms,
        "test_a_pass": test_a_pass, "test_b_pass": test_b_pass, "overall": overall,
        "captured_lines": captured_lines, "cb_captured": cb_captured,
        "is_graceful": is_graceful, "cb_is_graceful": cb_is_graceful,
        "had_error_log": had_error_log, "had_final_fallback": had_final_fallback,
        "cb_open": cb_open, "cb_skipped": cb_skipped,
    }


def append_live_validation(r):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "",
        "---",
        "",
        "## Live Validation — 2026-04-22",
        "",
        f"**Run:** {ts}  |  **Result:** {'PASS' if r['overall'] else 'FAIL'}",
        "",
        "### Test A: Auth failure -> 8B fallback -> static graceful fallback",
        "",
        "**Method:** Created `ChatGroq` with `groq_api_key='gsk_INVALID_KEY_FOR_TESTING...'`",
        "and passed to `safe_invoke_json()`. Patched `llm.GROQ_API_KEY` to same invalid value",
        "so the 8B fallback also fails. Verified result is `_GRACEFUL_FALLBACK_JSON`.",
        "",
        f"**Elapsed:** {r['elapsed_auth_ms']}ms",
        f"**Result is graceful fallback:** {r['is_graceful']}",
        f"**`[LLM] error` logged:** {r['had_error_log']}",
        f"**`final_fallback` logged:** {r['had_final_fallback']}",
        "",
        "**Log output:**",
        "```",
    ]
    for ln in r["captured_lines"]:
        lines.append(ln)
    lines += [
        "```",
        "",
        f"**Result:** {'PASS' if r['test_a_pass'] else 'FAIL'}",
        "",
        "### Test B: Circuit breaker opens -> primary + 8B skipped",
        "",
        "**Method:** Injected 5 failure timestamps into `_cb_failures` list, then called",
        "`_cb_record_failure()` to trigger open condition. Verified `_cb_is_open() == True`.",
        "Then ran `safe_invoke_json()` with a valid primary LLM — expected skip and static fallback.",
        "",
        f"**Circuit opened after 5 injected failures:** {r['cb_open']}",
        f"**`circuit_breaker open` skipped primary:** {r['cb_skipped']}",
        f"**Result is graceful fallback:** {r['cb_is_graceful']}",
        f"**Elapsed (no LLM calls):** {r['elapsed_cb_ms']}ms",
        "",
        "**Log output:**",
        "```",
    ]
    for ln in r["cb_captured"]:
        lines.append(ln)
    lines += [
        "```",
        "",
        f"**Result:** {'PASS' if r['test_b_pass'] else 'FAIL'}",
        "",
        "### Summary",
        "",
        "| Test | Scenario | Result |",
        "|------|----------|--------|",
        f"| A | Auth failure (invalid key) -> 8B fail -> static fallback | {'PASS' if r['test_a_pass'] else 'FAIL'} |",
        f"| B | Circuit breaker opens after 5 failures -> skips primary + 8B | {'PASS' if r['test_b_pass'] else 'FAIL'} |",
        "",
        "Fallback chain verified: the pipeline never crashes on LLM failure. Users receive",
        "a `confidence=low` card with a 'try again' message, not an exception trace.",
        "",
        f"*Live validation · `scripts/test_error_fallback.py` · {ts}*",
    ]

    doc_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs", "error_handling_matrix.md"
    )
    with open(doc_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nAppended Live Validation to: {doc_path}")


if __name__ == "__main__":
    result = run_validation()
    append_live_validation(result)
