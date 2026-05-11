# Cerna Orchestrator — Current Flow (Pre-LangGraph)

> This document is the canonical spec for the LangGraph port (Phase 3).
> Each numbered node below maps 1-to-1 to a future LangGraph `StateGraph` node.
> The edges and branches map to the graph's conditional edges.

---

## Node / Edge Diagram

```
[USER INPUT]
    │  query: str
    │  conversation_history: list[dict]
    │  module_hint: Optional[str]
    ▼
┌─────────────────────────┐
│  1. UNDERSTAND           │  understand_query() — one JSON-mode fast-LLM call
│                         │  IN:  raw query + history string
│  Outputs to state:      │  OUT: intent, formal_query, variants[2], module_hints,
│  intent                 │       entities, is_ambiguous
│  formal_query           │
│  query_variants         │  Cache: keyed on (query, history[-200:])
│  detected_modules       │  Side-effect: Groq API call (GROQ_MODEL_FAST)
│  detected_entities      │
│  is_ambiguous           │
└────────────┬────────────┘
             │
             ▼
    ┌─────────────────────────────────────────────────────┐
    │  INTENT ROUTE  (conditional edge)                    │
    └──────┬──────────────┬─────────────────┬─────────────┘
           │casual        │out_of_scope      │clinical_decision
           ▼              ▼                  ▼              │ (question / troubleshooting /
    ┌──────────┐  ┌──────────────┐  ┌──────────────┐       │  follow_up — default path)
    │ 2a.      │  │ 2b.          │  │ 2c.          │       │
    │ CASUAL   │  │ OOS REFUSAL  │  │ CLINICAL     │       │
    │ REFUSAL  │  │              │  │ REFUSAL      │       │
    └──────────┘  └──────────────┘  └──────────────┘       │
    Sets refusal  Sets refusal       Sets refusal           │
    field, exits  field, exits       field, exits           │
                                                            ▼
                                           ┌──────────────────────────────┐
                                           │  3. CLASSIFY MODULE           │
                                           │                              │
                                           │  Priority order:             │
                                           │  1. module_hint (UI filter)  │
                                           │  2. single module_hint       │
                                           │  3. entity-priority resolver │
                                           │  4. fast-LLM CLASSIFICATION  │
                                           │                              │
                                           │  OUT: classification,        │
                                           │       retrieval_vertical,    │
                                           │       fetch_k, should_hyde   │
                                           └──────────────┬───────────────┘
                                                          │
                                                          ▼
                                           ┌──────────────────────────────┐
                                           │  4. PREPARE RETRIEVAL        │
                                           │                              │
                                           │  Split query_variants[0,1]   │
                                           │  into variant1, variant2     │
                                           │  fields for parallel fanout  │
                                           └──────────────┬───────────────┘
                                                          │
                                                          ▼
                                 ┌────────────────────────────────────────────┐
                                 │  5. RETRIEVE  (parallel fanout)            │
                                 │                                            │
                                 │  RunnableParallel executes simultaneously: │
                                 │  ├─ formal_query  → retriever.query()      │
                                 │  ├─ variant1      → retriever.query()      │
                                 │  ├─ variant2      → retriever.query()      │
                                 │  └─ hyde_text     → generate_hyde()        │
                                 │                   (if should_hyde)         │
                                 │                                            │
                                 │  Then: if hyde_text present,               │
                                 │        retriever.query(hyde_text) appended │
                                 │                                            │
                                 │  OUT: raw_result_lists (list of chunk      │
                                 │       lists, one per query)                │
                                 └──────────────────┬─────────────────────────┘
                                                    │
                                                    ▼
                                     ┌──────────────────────────────┐
                                     │  6. FUSE (RRF)               │
                                     │                              │
                                     │  Reciprocal Rank Fusion over │
                                     │  all N result lists          │
                                     │  k=60, preserves best        │
                                     │  semantic_score per chunk    │
                                     │                              │
                                     │  OUT: fused_chunks           │
                                     └──────────────┬───────────────┘
                                                    │
                                                    ▼
                                     ┌──────────────────────────────┐
                                     │  7. RERANK (optional)        │
                                     │                              │
                                     │  if RERANK_ENABLED:          │
                                     │    cross-encoder reranking   │
                                     │    (BAAI/bge-reranker-v2-m3) │
                                     │  else: trim to TOP_K         │
                                     │                              │
                                     │  OUT: final_chunks           │
                                     └──────────────┬───────────────┘
                                                    │
                                                    ▼
                                     ┌──────────────────────────────┐
                                     │  8. GATE                     │
                                     │                              │
                                     │  a) did_you_mean check:      │
                                     │     top_score < 0.40 AND     │
                                     │     variants exist           │
                                     │  b) low_confidence check:    │
                                     │     all semantic_scores      │
                                     │     < CONFIDENCE_THRESHOLD   │
                                     │  c) citation_warning:        │
                                     │     clinical/FHIR/RCM lacks  │
                                     │     score >= 0.50 chunk      │
                                     │                              │
                                     │  OUT: did_you_mean[],        │
                                     │       low_confidence bool,   │
                                     │       citation_warning bool  │
                                     └──────────────┬───────────────┘
                                                    │
                              ┌─────────────────────┴────────────────────────┐
                              │  GATE ROUTE  (conditional edge)               │
                              └────┬──────────────────────────────────────────┘
                 did_you_mean ≠ [] │                              │ normal path
                                   ▼                              ▼
                        ┌──────────────────┐      ┌──────────────────────────────┐
                        │ 8a. DID YOU MEAN │      │  9. BUILD PROMPT             │
                        │                 │      │                              │
                        │ Sets response   │      │  Selects template:           │
                        │ to suggestion   │      │  - cross-module: COMPARISON  │
                        │ chips, skips    │      │  - single-module: SYSTEM     │
                        │ LLM entirely    │      │                              │
                        └──────────────┬──┘      │  Enriches question with      │
                                       │         │  [Troubleshooting] /         │
                                       │         │  [Vague query] prefix        │
                                       │         │                              │
                                       │         │  OUT: prompt (str)           │
                                       │         └──────────────┬───────────────┘
                                       │                        │
                                       │                        ▼
                                       │         ┌──────────────────────────────┐
                                       │         │  10. GENERATE                │
                                       │         │                              │
                                       │         │  primary: llm_json (70B)     │
                                       │         │  fallback 1: llm_fast_json   │
                                       │         │  fallback 2: graceful error  │
                                       │         │  (via .with_fallbacks())     │
                                       │         │                              │
                                       │         │  OUT: raw_llm_response (str) │
                                       │         └──────────────┬───────────────┘
                                       │                        │
                                       │                        ▼
                                       │         ┌──────────────────────────────┐
                                       │         │  11. PARSE                   │
                                       │         │                              │
                                       │         │  CernaResponse.parse(raw)    │
                                       │         │  Apply citation warning      │
                                       │         │  Deduplicate sources         │
                                       │         │                              │
                                       │         │  OUT: response (dict),       │
                                       │         │       sources (list[dict])   │
                                       │         └──────────────┬───────────────┘
                                       │                        │
                                       └────────────┬───────────┘
                                                    │
                                                    ▼
                                           [FINAL CernaState]
                                           All fields populated,
                                           trace[] contains one
                                           TraceEvent per step
```

---

## State Fields Written Per Node

| Node | Reads | Writes |
|------|-------|--------|
| understand | original_query, conversation_history | intent, formal_query, query_variants, detected_modules, detected_entities, is_ambiguous |
| casual/oos/clinical | — | refusal |
| classify_module | detected_modules, detected_entities, module_hint | classification, retrieval_vertical, fetch_k, should_hyde |
| prepare_retrieval | query_variants | variant1, variant2 |
| retrieve | formal_query, variant1, variant2, should_hyde, retrieval_vertical, fetch_k | raw_result_lists, hyde_doc |
| fuse | raw_result_lists | fused_chunks |
| rerank | fused_chunks, formal_query | final_chunks |
| gate | final_chunks, classification, query_variants | did_you_mean, low_confidence, citation_warning |
| did_you_mean | did_you_mean | response, sources |
| build_prompt | final_chunks, classification, intent, is_ambiguous, formal_query, original_query, conversation_history, detected_modules | prompt |
| generate | prompt | raw_llm_response |
| parse | raw_llm_response, citation_warning, final_chunks | response, sources |

---

## Current Implementation Notes

- **Parallel execution**: Nodes 4 (retrieve) run in a `RunnableParallel` (previously `ThreadPoolExecutor`).
- **Short-circuit exits**: Nodes 2a/2b/2c and 8a bypass the LLM entirely.
- **Caching**: Node 1 (understand) has an in-process dict cache on `(query, history[-200:])`.
- **Streaming path**: `stream_json_tokens()` is an alternative to Node 10 that yields tokens incrementally; it reuses the same `PreparedQuery` adapter from the pre-refactor API.

---

## LangGraph Port Map (Phase 3)

Each numbered node above becomes a `graph.add_node(name, fn)` call. Each branch becomes a `graph.add_conditional_edges(source, condition_fn, {branch: target})`. See `docs/langgraph_migration.md` for full details.
