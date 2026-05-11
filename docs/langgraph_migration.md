# LangGraph Migration Plan — Phase 3

> **Current state:** Cerna uses LangChain LCEL with pure step functions and explicit
> CernaState. This is the pre-migration foundation. No LangGraph code exists yet.
>
> **When to pull the trigger:** When the pipeline needs a genuine loop (e.g. iterative
> retrieval → rerank → decide whether to retrieve again), multi-agent coordination,
> human-in-the-loop interrupts, or persistent cross-session checkpointing.
> A linear pipeline is not a reason to adopt LangGraph.

---

## What Already Exists (The Hard Part)

The refactor done in Phase 2 Week 5 already implements everything LangGraph needs at
the data layer. The migration is purely a wiring change — **zero changes to step functions**.

| Already done | LangGraph equivalent |
|---|---|
| `CernaState` TypedDict | `StateGraph(CernaState)` state schema |
| `make_initial_state()` | `graph.invoke(initial_state)` entry |
| Each `step_X(state) -> state` function | `graph.add_node("X", step_X)` |
| `@traced` decorator events | LangGraph checkpointer state snapshots |
| `log_pipeline_trace()` JSONL | `SqliteSaver` / `PostgresSaver` checkpointer |
| `RunnableBranch` for intent routing | `add_conditional_edges()` |
| `RunnableParallel` for retrieval | `Send()` fan-out + reducer |

---

## The Port, Step by Step

### 1. Replace `build_pipeline()` with a `StateGraph`

**Current (`pipeline.py`):**
```python
def build_pipeline(retriever, llm_json, llm_fast, llm_fast_json):
    _understand = RunnableLambda(make_step_understand())
    _classify   = RunnableLambda(make_step_classify_module(llm_fast))
    # ...
    return (
        _understand
        | RunnableBranch(
            (lambda s: s["intent"] == "casual", _casual),
            # ...
            _content,
        )
    )
```

**After (`pipeline_lg.py`):**
```python
from langgraph.graph import StateGraph, END

def build_pipeline(retriever, llm_json, llm_fast, llm_fast_json):
    graph = StateGraph(CernaState)

    graph.add_node("understand",        make_step_understand())
    graph.add_node("casual",            step_casual)
    graph.add_node("out_of_scope",      step_out_of_scope)
    graph.add_node("clinical_decision", step_clinical_decision)
    graph.add_node("classify_module",   make_step_classify_module(llm_fast))
    graph.add_node("prepare_retrieval", step_prepare_retrieval)
    graph.add_node("retrieve",          make_step_retrieve(retriever))
    graph.add_node("fuse",              step_fuse)
    graph.add_node("rerank",            step_rerank)
    graph.add_node("gate",              step_gate)
    graph.add_node("did_you_mean",      step_did_you_mean)
    graph.add_node("build_prompt",      step_build_prompt)
    graph.add_node("generate",          make_step_generate(llm_json, llm_fast_json))
    graph.add_node("parse",             step_parse)

    graph.set_entry_point("understand")

    graph.add_conditional_edges("understand", _route_intent, {
        "casual":            "casual",
        "out_of_scope":      "out_of_scope",
        "clinical_decision": "clinical_decision",
        "continue":          "classify_module",
    })

    for refusal_node in ("casual", "out_of_scope", "clinical_decision"):
        graph.add_edge(refusal_node, END)

    graph.add_edge("classify_module",   "prepare_retrieval")
    graph.add_edge("prepare_retrieval", "retrieve")
    graph.add_edge("retrieve",          "fuse")
    graph.add_edge("fuse",              "rerank")
    graph.add_edge("rerank",            "gate")

    graph.add_conditional_edges("gate", _route_gate, {
        "did_you_mean": "did_you_mean",
        "continue":     "build_prompt",
    })
    graph.add_edge("did_you_mean", END)
    graph.add_edge("build_prompt", "generate")
    graph.add_edge("generate",     "parse")
    graph.add_edge("parse",        END)

    return graph.compile()

def _route_intent(state: CernaState) -> str:
    intent = state["intent"]
    if intent in ("casual", "out_of_scope", "clinical_decision"):
        return intent
    return "continue"

def _route_gate(state: CernaState) -> str:
    return "did_you_mean" if state.get("did_you_mean") else "continue"
```

That is the entire migration. One function, ~50 lines.

---

### 2. Parallel Retrieval: `RunnableParallel` → `Send()` Fan-Out

**Current:** `RunnableParallel` in `make_step_retrieve()` fans out to 4 branches.

**After:** LangGraph's `Send()` primitive distributes over a dynamic list:

```python
from langgraph.constants import Send

def route_to_retrievers(state: CernaState):
    queries = [
        state["formal_query"],
        state.get("variant1", ""),
        state.get("variant2", ""),
    ]
    if state.get("should_hyde"):
        queries.append(state["formal_query"])  # HyDE handled inside node
    return [
        Send("retrieve_single", {"query": q, **state})
        for q in queries if q
    ]

graph.add_conditional_edges("prepare_retrieval", route_to_retrievers)
```

This is more flexible than `RunnableParallel` for dynamic query counts
and gives LangGraph visibility into each retrieval as a separate checkpoint.

---

### 3. Checkpointing (Persistent State)

Add a `SqliteSaver` checkpointer to enable:
- Resumable conversations across sessions
- Mid-request interrupt + replay (human-in-the-loop)
- Cross-session memory (user preferences, prior context)

```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("logs/checkpoints.db")
compiled = graph.compile(checkpointer=checkpointer)

# Each request provides a thread_id so state persists across calls
result = compiled.invoke(
    initial_state,
    config={"configurable": {"thread_id": session_id}},
)
```

The `trace_log.jsonl` written by `log_pipeline_trace()` contains exactly the same
data the checkpointer would store — so the analytical pipeline already exists.

---

### 4. Phase 3 Features That Unlock the Migration

These are capabilities the current pipeline cannot express without LangGraph:

| Capability | Why LangGraph Needed | Example in Cerna |
|---|---|---|
| **Iterative retrieval** | Requires a loop edge (retrieve → evaluate → retrieve again) | "Did retrieval quality improve after HyDE? If not, widen the query." |
| **Tool-calling agent** | Requires a loop + tool node pattern | Cerna calling a live uCern search API |
| **Human-in-the-loop** | Requires `interrupt_before` / `interrupt_after` | "This query looks clinical — should I proceed?" |
| **Multi-agent routing** | Requires sub-graphs per module | Specialist sub-agents for FHIR vs. Revenue Cycle |
| **Cross-session memory** | Requires checkpointer persistence | "You asked about eMAR last week — here's what changed." |

**The signal to migrate:** When any one of the above appears in the Phase 3 spec,
pull the trigger. The migration itself is one day of wiring work.

---

## What Does NOT Change

- All step functions (`step_understand`, `step_fuse`, etc.) — zero changes
- `CernaState` and `TraceEvent` — zero changes
- `state.py`, `retriever.py`, `reranker.py`, `safety.py`, `prompts.py` — zero changes
- `Orchestrator` public API (`prepare`, `generate_structured`, `stream_json_tokens`) — zero changes
- `app.py` — zero changes

The only file that changes is `pipeline.py` — specifically the `build_pipeline()` function.
Everything else is preserved.
