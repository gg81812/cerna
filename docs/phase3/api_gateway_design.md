# Phase 3 Design: Accenture API Gateway Routing
**Status:** Design complete — implementation pending infrastructure access  
**Target:** Gate 3 / production readiness (Week 9–10 of Project Delivery Plan)  
**Dependencies:** Accenture infrastructure team, gateway product confirmation  
**Effort estimate:** 3–5 days of development after infrastructure coordination

---

## Problem

Cerna currently makes direct calls from the application server to the Groq API (development) and, in the production plan, to the OpenAI API. In a production Accenture delivery:

1. **Direct outbound traffic to LLM providers is not permissible** without routing through an approved internal gateway. Healthcare data — even indirect queries containing workflow context — may not leave the Accenture network via unapproved paths.

2. **API key management** is a security risk when provider keys live in `.env` files managed by individual developers. The gateway layer should own key rotation and secret management; the application should authenticate to the gateway, not directly to the provider.

3. **Observability and billing** require a centralized record of all LLM API calls — latency, token count, model, cost attribution by project. App-side logging (which Cerna already has in `logger.py`) is necessary but not sufficient; a gateway log provides an independent audit record.

The current `llm.py` factory is the correct abstraction point for this change. All LLM calls in the application flow through `get_llm()`, `get_llm_json()`, `get_llm_fast()`, and `get_llm_fast_json()`. The gateway change is a configuration change to those four functions — not a codebase refactor.

---

## Proposed Approach

### Gateway as Environment-Selectable Endpoint

The `ChatGroq` and `ChatOpenAI` clients both accept a `base_url` parameter that overrides the provider endpoint. In a gateway configuration:

```python
# llm.py (gateway-enabled version)
GATEWAY_URL = os.getenv("CERNA_GATEWAY_URL")          # e.g. https://gateway.accenture.com/llm/v1
GATEWAY_KEY  = os.getenv("CERNA_GATEWAY_API_KEY")     # gateway auth token, NOT provider key

def get_llm_json() -> ChatOpenAI:
    if GATEWAY_URL:
        return ChatOpenAI(
            model=GPT_MODEL,
            api_key=GATEWAY_KEY,
            base_url=GATEWAY_URL,
            ...
        )
    # local dev fallback: direct provider
    return ChatGroq(model=GROQ_MODEL, groq_api_key=GROQ_API_KEY, ...)
```

Setting `CERNA_GATEWAY_URL` in the production `.env` switches all calls to the gateway. Unsetting it falls back to direct-provider mode for local development. No code path changes required.

### Authentication: Gateway-Managed Keys

The application authenticates to the gateway using a service-principal key (`CERNA_GATEWAY_API_KEY`). The gateway holds the provider API keys and is responsible for key rotation. From the application's perspective, the provider key disappears from `.env` entirely — only the gateway key remains, and the gateway key is issued by the Accenture infrastructure team.

This eliminates the risk of provider API keys in developer machines, CI/CD secrets, or accidentally committed `.env` files.

### Retry Logic: Application Wins

Cerna has exponential backoff with circuit breaker logic in `llm.py` (`safe_invoke_json`, `_invoke_with_backoff`). The gateway will also have its own retry behavior. These must not both be active simultaneously — double retry creates multiplicative worst-case latency (3 app retries × gateway retries = 9+ round trips on a 429 event).

**Recommended:** Disable app-side retry when gateway is active. The gateway handles 429s and 5xx transparently; the app only needs to handle cases where the gateway itself is unreachable (treated as a network error, not a retryable LLM error). The circuit breaker remains useful for detecting gateway-down scenarios and returning the graceful fallback.

Configuration flag: `GATEWAY_HANDLES_RETRY=true` in `.env` sets `_RETRY_DELAYS = ()` (no app-side retry) when the gateway URL is set.

### Rate Limits: Gateway vs. Provider

Direct Groq: 30 RPM / 14,400 RPD (free tier).  
Typical Accenture gateway: metered per project, usually no RPM limit but per-call cost accounting.  
OpenAI via Azure OpenAI: provisioned throughput in tokens-per-minute, allocated per deployment.

The gateway model eliminates the per-developer provider rate limit but introduces project-level cost governance. This is the correct tradeoff for a production system.

---

## Trade-offs Considered

**Gateway-side retry vs. application-side retry**

Keeping both active is the most defensive configuration but produces confusing behavior: a 429 from the provider becomes a slow response (up to 13 seconds in the 3-attempt backoff sequence), and the gateway adds its own delay on top. Disabling app-side retry when the gateway is active is the cleaner contract: the gateway is responsible for provider-level reliability; the app is responsible for circuit-breaking if the gateway itself is down.

**Observability: gateway logs vs. app traces**

Cerna already writes per-request traces to `logs/trace_log.jsonl` (pipeline step timings, intent, confidence). Gateway logs capture a different layer: provider latency, token usage, model version, cost. Both are needed for production. They should be correlated via the `trace_id` field in Cerna's logs — the gateway log should accept a correlation header (`X-Cerna-Trace-ID`) passed from the app.

**LangChain client compatibility**

LangChain's `ChatOpenAI` supports `base_url` override natively. `ChatGroq` does not expose `base_url` in the same way — if the gateway exposes an OpenAI-compatible endpoint (most modern gateways do), the production client should be `ChatOpenAI` pointed at the gateway, regardless of the underlying provider. This is another reason the LLM swap (Groq → GPT-5.4 mini) and the gateway integration should be done together rather than sequentially.

**Latency impact**

An internal gateway adds one network hop. Typical Accenture internal gateway latency for LLM proxying: 20–50ms additional per call. At the current end-to-end latency of 2–4s (dominated by the 70B model inference on Groq), this is not a meaningful addition.

---

## Implementation Sequence

1. Confirm gateway product and endpoint format with Accenture infrastructure team. (Not dev work — this is a coordination task.)
2. Confirm whether the gateway exposes OpenAI-compatible API or requires a custom SDK.
3. Update `llm.py` factory functions with gateway/direct switch based on `CERNA_GATEWAY_URL` env var.
4. Update `config.py` to read `CERNA_GATEWAY_URL` and `CERNA_GATEWAY_API_KEY`.
5. Update `.env.example` with gateway variables documented.
6. Test with a staging gateway endpoint: confirm all four LLM functions route correctly, retry behavior is disabled, circuit breaker still fires for gateway-down scenarios.
7. Confirm correlation header (`X-Cerna-Trace-ID`) is accepted by the gateway.

Dev effort: 3–5 days including coordination time. The coordination (steps 1–2) is the unpredictable element.

---

## Open Questions (Require Human Resolution)

1. **Which gateway product?** Accenture uses multiple API gateway platforms depending on the account and region (Kong, Azure API Management, MuleSoft, Apigee). The integration steps depend on the product. The infrastructure team must confirm.

2. **Does the gateway expose an OpenAI-compatible API?** If yes, the `ChatOpenAI(base_url=GATEWAY_URL)` approach works directly. If no, a custom HTTP client wrapping LangChain's `BaseLLM` is needed (~2 additional days).

3. **Are there existing healthcare AI apps routed through the Accenture gateway?** A reference implementation from another Oracle Health or healthcare project would significantly reduce coordination time. Ask the infrastructure team before starting.

4. **What is the service principal provisioning process?** Obtaining `CERNA_GATEWAY_API_KEY` likely requires a formal service principal request. Lead time is unknown. This should be requested in parallel with development, not after.

---

*Design doc: Phase 3 API Gateway · Cerna · 2026-04-22*
