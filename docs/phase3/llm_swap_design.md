# Phase 3 Design: LLM Transition — Groq Llama 3.3 70B to GPT-5.4 Mini
**Status:** Design complete — implementation planned for Phase 3  
**Target:** Gate 2 / Week 6 of Project Delivery Plan  
**Dependencies:** OpenAI API key or Azure OpenAI deployment, GPT-5.4 mini availability  
**Effort estimate:** 2–3 days (optimistic 1 day; realistic 3 days if JSON mode behavior diverges)

---

## Problem

The Project Delivery Plan specifies GPT-5.4 mini as the production LLM. Groq Llama 3.3 70B is used for development. The swap is architecturally simple — `llm.py` is a single-file factory where all four LLM instances are created, and the migration note at the top of that file describes the change as a 20-line edit. That claim is technically accurate but understates the risk.

**The actual risk is not the code change — it's prompt behavior divergence.** Cerna's prompts are tuned for Llama 3.3 70B. The prompts include:
- A JSON-mode response format constraint (the model must respond with a specific 6-field JSON schema)
- An intent classification taxonomy with Cerner-specific enum values
- Clinical decision refusal instructions ("I'm Cerna, a Cerner implementation specialist...")
- PII non-echo instructions embedded in the system prompt
- A 5-section structured response format (`direct_answer`, `context_explanation`, `step_by_step`, `best_practices`, `recommendations`)

Each of these may behave differently on GPT-5.4 mini. Most importantly: GPT-5.4 mini's JSON mode is more reliable than Groq's implementation (fewer cases of markdown wrapping or truncated JSON), but it may be more rigid about response structure in ways that break the current prompt's field ordering assumptions.

**There is no production budget to discover these differences post-deployment.** The swap must be benchmarked before Gate 2, not deployed and monitored afterward.

---

## Proposed Approach: Four-Phase Validation

### Phase 1 — Baseline Benchmark (No Prompt Changes)

Run the 75-query golden set with GPT-5.4 mini, using the exact same prompts currently in `prompts.py`. Record:
- KHR per query (same methodology as existing golden eval)
- JSON parse success rate (does `CernaResponse.parse()` succeed on every response?)
- Field population rate (does `step_by_step` get populated? Are there missing fields?)
- Classification accuracy (does the intent classification match expected intents?)

Compare against the Groq baseline (73.3% raw KHR). The goal is not to beat the baseline yet — it's to establish where GPT-5.4 mini diverges.

### Phase 2 — Failure Mode Analysis

Categorize the queries where GPT-5.4 mini underperforms or produces malformed output. Expected failure categories:

1. **JSON structure violations** — GPT-5.4 mini may produce extra fields, renamed fields, or nested structures not in the schema. `CernaResponse.parse()` should handle most of these via Pydantic defaults, but validate explicitly.

2. **Verbose `step_by_step` fields** — GPT-5.4 mini tends to produce longer, more detailed step arrays. The current UI expects short steps (1–2 sentences each). Excessive length may overflow the UI card layout.

3. **Classification prompt interpretation** — The classification prompt uses Cerner-specific module names (`MILLENNIUM`, `POWERCHART`, etc.) as enum values. GPT-5.4 mini may resolve ambiguous queries differently than Llama, particularly for short or jargon-heavy queries. Run all 5 formal benchmark queries manually and confirm module classification matches expected.

4. **Refusal message tone** — The clinical decision refusal prompt produces a specific message in Cerna's voice. Test that GPT-5.4 mini uses the template message and does not improvise a different refusal.

### Phase 3 — Targeted Prompt Adjustments

For each identified failure category, make the minimum prompt change that resolves the failure without regressing other queries. Do not rewrite prompts wholesale.

Typical adjustments needed when moving from Llama to GPT-class models:
- Tighten the JSON schema instruction: explicitly state "respond with ONLY a JSON object, no markdown, no explanation outside the JSON"
- Add explicit field-length constraints to `step_by_step` and `best_practices`: "each step should be 1–2 sentences, maximum 30 words"
- For the classification prompt: add a few-shot example if the model produces out-of-schema intent values

Constraint: every prompt change must be accompanied by a re-run of the formal benchmark queries (5 queries) to confirm no regression.

### Phase 4 — Re-Benchmark and Decision

Re-run the 75-query golden set after prompt adjustments. The acceptance criterion is: KHR ≥ Groq baseline (73.3%) AND JSON parse success rate = 100% AND classification accuracy ≥ Groq baseline on the 5 formal benchmark queries.

If Phase 4 passes: deploy GPT-5.4 mini as the production LLM. Update `.env` with `OPENAI_API_KEY`, change model constants in `config.py`, update `llm.py` (the 20-line change described in the migration comment).

If Phase 4 fails on KHR: escalate to a design review before deployment. Do not deploy a model that underperforms the current production baseline.

---

## Trade-offs

**Cost: GPT-5.4 mini pricing vs. Groq**

Groq free tier: zero cost, 14,400 tokens/day limit.  
Groq paid tier: approximately $0.05–0.10 per 1M input tokens (varies by model).  
GPT-5.4 mini (OpenAI direct): approximately $0.15–0.30 per 1M input tokens (estimated based on current mini model pricing; confirm at integration time).  
Azure OpenAI (GPT-5.4 mini via Azure): pricing depends on Accenture enterprise agreement; likely lower than direct OpenAI pricing.

At 500 queries/day with an average 2,000 tokens per query: ~1M tokens/day. Direct OpenAI cost: $0.15–0.30/day. Azure OpenAI under enterprise agreement: likely lower. Budget cap and approval path should be confirmed before selecting the billing model.

**Latency: GPT-5.4 mini vs. Groq Llama 3.3 70B**

Groq provides hardware-accelerated inference (LPU chips) for Llama. Typical generation latency: 1–2s for a 500-token response.  
GPT-5.4 mini via OpenAI API: typically 1.5–3s for the same output length, depending on server load.  
Azure OpenAI: typically 2–4s, with provisioned throughput deployments offering more predictable latency.

The latency difference is real but not disqualifying. The demo cache mitigates latency for rehearsed queries.

**Rate limits: per-minute vs. per-day**

Groq free tier: 30 RPM, 14,400 RPD (per-day is the binding constraint for eval runs).  
GPT-5.4 mini (OpenAI): per-minute RPM limits at tier level; no per-day hard limit. For a demo use case this is a significant improvement — concurrent users don't compete against a daily budget.  
Azure OpenAI: provisioned throughput in tokens-per-minute per deployment; reserved capacity.

**JSON mode behavior differences**

OpenAI's native JSON mode (`response_format: {"type": "json_object"}`) is more reliable than Groq's implementation. In Groq, models occasionally produce markdown-wrapped JSON or truncate at `max_tokens` leaving an unclosed object. The `CernaResponse.parse()` repair chain handles these cases, but they reduce reliability. GPT-5.4 mini's JSON mode is more likely to produce clean, complete JSON on the first attempt.

**Function calling vs. JSON mode**

The `llm.py` migration note suggests using native function calling for GPT-5.4 mini instead of JSON mode. Function calling defines the response schema as a tool spec and eliminates the need for `response_format` altogether. This is the preferred approach for production because it makes schema violations a model-side parse error rather than an application-side repair task. However, migrating from JSON mode to function calling requires prompt restructuring (the current prompt embeds the schema as instructions; function calling externalizes it). This is a 0.5-day refactor but changes a prompt that has been validated. Recommendation: start with JSON mode in Phase 1–2 to establish the KHR baseline, then evaluate whether function calling is worth the additional refactoring in Phase 3.

---

## Effort Estimate

| Phase | Task | Duration |
|-------|------|----------|
| 1 | Baseline benchmark (75 queries, GPT-5.4 mini, no changes) | 0.5 days |
| 2 | Failure mode analysis (categorize divergence cases) | 0.5 days |
| 3 | Prompt adjustments (1–3 targeted edits, re-run benchmark queries) | 0.5–1 day |
| 4 | Re-benchmark and decision | 0.5 days |
| — | `llm.py` and `config.py` code change (if passing) | 0.5 days |
| **Total** | | **2–3 days** |

The 2-day vs. 3-day range depends on whether the JSON structure violations require a prompt rewrite (unlikely) or a simple schema instruction addition (typical).

---

## Open Questions (Require Human Resolution)

1. **Is the OpenAI API key obtained?** The phase 3 LLM swap cannot start without it. Alternatively, does the project have access to Azure OpenAI through the Accenture enterprise agreement? Azure OpenAI is preferred for production (Accenture-managed, compliant with internal data policies).

2. **Direct OpenAI vs. Azure OpenAI?** For a production POV in a healthcare context, Azure OpenAI is the correct choice (data residency controls, Accenture enterprise terms, HIPAA Business Associate Agreement available). Direct OpenAI requires a separate BAA and is less common in Accenture delivery. Confirm the target deployment platform before starting Phase 1.

3. **Is GPT-5.4 mini available in the target Azure region?** Azure OpenAI model availability varies by region. The deployment must be in a region where GPT-5.4 mini is available AND where data residency requirements are met.

4. **What is the production-tier token budget?** The 75-query benchmark run consumes approximately 75,000–150,000 tokens. At Phase 2–3 iteration pace, total development consumption is 500,000–1,000,000 tokens. Confirm the approved token budget before starting eval runs.

---

*Design doc: Phase 3 LLM Swap (Groq → GPT-5.4 mini) · Cerna · 2026-04-22*
