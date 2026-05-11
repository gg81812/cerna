# Cerna — Cerner / Oracle Health AI Specialist

**Phase 2 · Week 5 POV · v1.3.0**

Enterprise-grade RAG chatbot for Cerner (Oracle Health) implementation knowledge.
Covers Millennium, PowerChart, Revenue Cycle, FHIR & APIs, and Clinical Workflows.

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Safety Classifier  (llama-3.1-8b-instant)                          │
│  → in_scope / clinical_decision / out_of_domain                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ in_scope only
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Query Rewriter  (llama-3.1-8b-instant)                             │
│  → resolve follow-up references  /  HyDE hypothesis (if enabled)   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Cache check  (Redis → in-memory LRU)                               │
│  → cache hit: return cached CernaResponse immediately               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ cache miss
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Module Classifier  (llama-3.3-70b-versatile)                       │
│  → MILLENNIUM / POWERCHART / REVENUE_CYCLE / FHIR / CLINICAL / GENERAL │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Hybrid Retrieval  (retriever.py)                                   │
│  ├── Semantic: ChromaDB cosine similarity  (RERANK_TOP_K=20 hits)   │
│  ├── Keyword:  BM25Okapi                   (RERANK_TOP_K=20 hits)   │
│  ├── Fusion:   Reciprocal Rank Fusion (k=60)                        │
│  ├── MMR:      Maximal Marginal Relevance  (MMR_LAMBDA env var)     │
│  └── Tiebreak: source_weight  (ucern=1.0 > open_cerner=0.9 > …)    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Cross-Encoder Reranker  (BAAI/bge-reranker-v2-m3)                  │
│  → scores (query, chunk) pairs → top FINAL_TOP_K=5 chunks           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Prompt Builder  (prompts.py v1.3.0)                                │
│  → SYSTEM_PROMPT_TEMPLATE with JSON schema instruction              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LLM Generation  (llama-3.3-70b-versatile, JSON mode)               │
│  → CernaResponse {direct_answer, context, steps, best_practices,   │
│                   recommendations, confidence}                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
                    Streamlit Structured Card UI
```

### Embedding Collections

| Collection          | Model                    | Dim  | Purpose                |
|---------------------|--------------------------|------|------------------------|
| `cerner_docs_bge`   | BAAI/bge-large-en-v1.5   | 1024 | **Production default** |
| `cerner_docs`       | all-MiniLM-L6-v2         | 384  | A/B / fallback         |

Switch collection without code changes:
```bash
# Linux / Mac
COLLECTION=cerner_docs_bge streamlit run app.py

# Windows
set COLLECTION=cerner_docs_bge && streamlit run app.py
```

---

## Setup

### Option A — Docker (recommended for local dev)

Requires [Docker Desktop](https://docs.docker.com/get-docker/) with Compose v2.

```bash
cp .env.example .env
# Edit .env and set GROQ_API_KEY=your_key_here

# Start Redis + Streamlit app (Redis must be healthy before app starts)
docker compose up

# Access at http://localhost:8501
```

Redis data persists across restarts via the `redis_data` named volume.  
To wipe the cache: `docker compose down -v`

To start only Redis (and run the app locally for faster iteration):
```bash
docker compose up redis
# then in another terminal:
streamlit run app.py
```

### Option B — Manual setup

#### 1. Prerequisites

- Python 3.11+
- [Groq API key](https://console.groq.com) (free tier available)
- (Optional) Redis 7+ for persistent caching — app works without it

#### 2. Install dependencies

```bash
pip install -r requirements.txt
```

#### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and set GROQ_API_KEY=your_key_here
# Optionally set REDIS_HOST=localhost if running Redis locally
```

#### 4. Build the knowledge base

```bash
# Tag documents with metadata (produces scripts/doc_manifest.json)
python scripts/tag_documents.py

# Chunk, embed, and store in ChromaDB
python ingest.py
```

#### 5. Run the app

```bash
streamlit run app.py
```

#### 6. (Optional) Upgrade to BGE embeddings

```bash
# Re-embed all chunks with BAAI/bge-large-en-v1.5 (~1.3 GB download, 15-30 min)
python scripts/ingest_bge.py

# Switch the app to the BGE collection
set COLLECTION=cerner_docs_bge  # Windows
streamlit run app.py
```

---

## LLM Strategy

| Role                   | Current Model              | Planned Production     |
|------------------------|----------------------------|------------------------|
| Main QA generation     | llama-3.3-70b-versatile    | GPT-4.1 mini           |
| Classification/safety  | llama-3.1-8b-instant       | GPT-4.1 nano / o4-mini |
| Query rewriting        | llama-3.1-8b-instant       | GPT-4.1 nano           |

**Migration**: Change only `llm.py`. All other code is provider-agnostic via LangChain.
See `llm.py` for the specific lines to swap (marked with migration comments).

---

## Environment Variables

| Variable                   | Default        | Description                                                |
|----------------------------|----------------|------------------------------------------------------------|
| `GROQ_API_KEY`             | *(required)*   | Groq API key (console.groq.com)                            |
| `GROQ_API_KEYS`            | *(not set)*    | Comma-separated keys for multi-key quota pooling           |
| `REDIS_HOST`               | `localhost`    | Redis hostname (`redis` when using docker compose)         |
| `REDIS_PORT`               | `6379`         | Redis port                                                 |
| `REDIS_DB`                 | `0`            | Redis database index                                       |
| `CACHE_BACKEND`            | `memory`       | `redis` or `memory` — switches between Redis and LRU cache |
| `RESPONSE_CACHE_TTL`       | `3600`         | Exact-match cache TTL in seconds                           |
| `SEMANTIC_CACHE_THRESHOLD` | `0.85`         | Cosine similarity threshold for semantic cache hits        |
| `COLLECTION`               | `cerner_docs`  | ChromaDB collection (`cerner_docs_bge` for BGE)           |
| `RERANK_ENABLED`           | `true`         | Enable cross-encoder reranking                             |
| `HYDE_ENABLED`             | `false`        | Enable HyDE query expansion                                |
| `MMR_LAMBDA`               | `0.5`          | MMR diversity (0=max diversity, 1=pure relevance)          |

---

## Running Evaluations

```bash
# Full 75-query golden set
python eval/run_eval.py

# Quick smoke test (10 queries)
python eval/run_eval.py --limit 10

# Single module
python eval/run_eval.py --module fhir

# Summary report
python eval/report.py
```

**Golden set**: `eval/golden_set.jsonl` — 75 queries (15/module × 5 easy/7 medium/3 hard + 10 out-of-scope).

**Metrics**: keyword hit rate, refusal accuracy, confidence distribution, latency p95, top chunk score.

---

## Admin View

Append `?admin=1` to the Streamlit URL to reveal the admin panel:
```
http://localhost:8501/?admin=1
```
Shows: cache backend/stats, recent query log with latency and confidence.

---

## Data Sources

Documents live in `data/[module]/`. Run `python scripts/tag_documents.py` to re-classify after adding files.

| Module          | Doc Types                                           |
|-----------------|-----------------------------------------------------|
| `millennium`    | CCL docs, MPages guides, domain architecture        |
| `powerchart`    | CPOE guides, patient list config, workflow docs     |
| `revenue_cycle` | Charge capture, CDI, RCM configuration guides      |
| `fhir`          | FHIR R4 resource pages, SMART on FHIR specs         |
| `clinical`      | eMAR, BCMA, PharmNet, SurgiNet workflow guides      |

**Source weighting** (applied during retrieval tiebreaking):

| Source        | Weight |
|---------------|--------|
| ucern         | 1.0    |
| open_cerner   | 0.9    |
| hl7_cerner    | 0.9    |
| engineering_blog | 0.7 |
| third_party   | 0.5    |

---

## Project Structure

```
cerna/
├── app.py                    ← Streamlit entry point
├── config.py                 ← All constants and env vars
├── orchestrator.py           ← Main pipeline coordinator
├── retriever.py              ← Hybrid BM25+semantic+RRF+MMR retriever
├── reranker.py               ← BGE cross-encoder reranker
├── query_rewriter.py         ← Follow-up resolution + HyDE
├── memory.py                 ← Conversation buffer
├── safety.py                 ← Safety classifier + guardrails
├── schemas.py                ← Pydantic CernaResponse model
├── cache.py                  ← Redis + in-memory LRU cache
├── redis_client.py           ← Shared Redis connection pool (all tasks use this)
├── prompts.py                ← All LangChain prompt templates (v1.3.0)
├── ingest.py                 ← Document loading + structural chunking
├── llm.py                    ← LLM factory (swap provider here)
├── logger.py                 ← JSONL structured logging
├── Dockerfile                ← App container image
├── docker-compose.yml        ← Local dev stack (Redis + Streamlit app)
├── ui/
│   ├── components.py         ← Streamlit UI components
│   └── styles.py             ← CSS + Web Speech API voice input
├── scripts/
│   ├── tag_documents.py      ← Document metadata classifier → doc_manifest.json
│   └── ingest_bge.py         ← BGE re-embedding script
├── eval/
│   ├── golden_set.jsonl      ← 75-query evaluation dataset
│   ├── run_eval.py           ← Evaluation runner
│   └── report.py             ← Results summariser
└── data/
    ├── millennium/
    ├── powerchart/
    ├── revenue_cycle/
    ├── fhir/
    └── clinical/
```

---

*Generated by Cerna Week 5 POV build — 2026-04-18*
