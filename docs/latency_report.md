# Cerna — Latency Report
**Day 3 Observability · 2026-04-22**

---

## Instrumentation Status

All pipeline steps are instrumented via the `@traced(step_name)` decorator in `pipeline.py`. Each step records `duration_ms`, `success`, `input_summary`, and `output_summary` into `CernaState["trace"]`. The full trace is appended to `logs/trace_log.jsonl` at request completion via `log_pipeline_trace()`.

**New in Day 3:**
- `scripts/analyze_traces.py` — reads `logs/trace_log.jsonl`, produces p50/p95/p99 per-step latency, error rates, intent distribution, and slow-query flags
- Health check at `?health=1` — returns JSON `{status, version, chroma_dir_exists, chunk_total}`
- Version string `_VERSION = "0.5.0"` in `app.py` footer

---

## Baseline Latency Profile (Design Targets)

| Step | Expected p50 | Expected p95 | Notes |
|------|-------------|-------------|-------|
| understand | 150ms | 400ms | 1 JSON-mode LLM call (8B model) |
| classify_module | 80ms | 200ms | 1 LLM call (8B model) |
| prepare_retrieval | <1ms | 2ms | No network; splits state fields |
| retrieve | 80ms | 200ms | ChromaDB + BM25 parallel; network-free |
| fuse | <1ms | 2ms | RRF computation; CPU-only |
| rerank | <1ms | 5ms | Disabled by default; cross-encoder if enabled |
| gate | <1ms | 5ms | Regex + score threshold; no network |
| build_prompt | <1ms | 2ms | String formatting |
| generate | 1500ms | 4000ms | 70B model on Groq; main latency source |
| parse | <1ms | 5ms | JSON parse + Pydantic validation |
| **Total (cold)** | **~2s** | **~5s** | End-to-end without cache |
| **Total (cache)** | **<100ms** | **200ms** | LRU cache hit: no LLM calls |

---

## Pre-Check Latency (Fast Path)

Queries matched by pre-check regex (casual, OOS, clinical_decision, roleplay, injection, CCL export) return without any LLM call:

| Pre-check | Latency | How measured |
|-----------|---------|--------------|
| _CASUAL_PAT | < 1ms | Python regex on short string |
| _OOS_PAT | < 1ms | Python regex |
| _CLINICAL_PAT | < 1ms | Python regex |
| _ROLEPLAY_PAT (RT-05) | < 1ms | Python regex |
| _INJECTION_PAT (RT-02) | < 1ms | Python regex |
| _CCL_EXPORT_PAT (RT-04) | < 1ms | Python regex |
| RT-01 dual-regex | < 1ms | Two regex searches |

**Safety refusals are instant from the user's perspective.**

---

## How to Generate a Live Report

After running the demo (or any session with 10+ queries):

```bash
python scripts/analyze_traces.py
python scripts/analyze_traces.py --last 50   # last 50 requests only
```

This produces per-step p50/p95/p99, error rates, intent distribution, and slow query list.

---

## Demo Latency Strategy

- **Pre-warm all 8 demo queries** before the session starts (`scripts/prewarm_demo_cache.py` or run them manually in the UI)
- **Cache hit**: all pre-warmed queries return in < 100ms (no Groq API call)
- **If cache miss**: queries 7 and 8 (out-of-scope, clinical safety refusal) are instant from regex — no LLM call; < 500ms on any hardware
- **Fallback**: if the app crashes and can't be restarted, the `docs/demo_runbook.md` provides narrative fallback with exact numbers

---

*Latency report · Cerna Day 3 observability · 2026-04-22*
