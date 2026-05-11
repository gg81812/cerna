# Cerna — Mid-Review Summary
**Date:** 2026-04-22 · Phase 2 Week 5

---

## What Cerna Is Today

Cerna is a RAG-based specialist assistant for Oracle Health (Cerner), running on Groq's Llama 3.3 70B with a 1,322-chunk curated knowledge base across five modules: FHIR, Millennium, PowerChart, Revenue Cycle, and Clinical. The system uses module-aware classification before retrieval, hybrid BM25 + semantic search with Reciprocal Rank Fusion, and structured five-section JSON responses with per-source quality badges. It refuses clinical decision queries, masks PII before any LLM call or log write, and surfaces honest coverage signals (archival banners, limited-module indicators) rather than projecting false confidence. The demo is positioned on Path B: FHIR + Revenue Cycle as the primary demonstration modules, with Millennium as depth and PowerChart/Clinical as flagged-limited.

---

## Measurable State

**Knowledge Base:** 1,322 chunks across 98 documents. Source distribution: 437 reference chunks, 408 workflow chunks, 477 prose chunks. 85% verifiable primary or secondary sources; ~15% archival community wiki (clearly badged in UI).

**Retrieval:** 84% on vague queries (55/55 pass on ≥ 0.40 threshold). 5/5 formal benchmark regression queries pass. Top-1 semantic scores ranging 0.67–0.76 across modules on benchmark queries.

**End-to-end accuracy:** 73.3% raw / 80.9% TPD-adjusted on 75-query golden set (run 2026-04-20). Clinical module severely impacted by Groq TPD quota exhaustion during that run; estimated 67–73% on answered clinical queries. Next full golden-set run planned post-uCern-decision when KB state changes.

**Red-team:** 24/24 (100%) — MEASURED via full live run 2026-04-22. All six findings (RT-01 through RT-06) patched and confirmed. One residual gap documented: plain first+last name + MRN format not caught by pre-check regex (LLM also misclassifies; PII guard prevents echo). Post-review fix identified; not in any demo query.

**Latency:** Not formally measured in this cycle. Prior session logs show median end-to-end ~2.5–4s on Groq free tier outside of rate-limit events.

---

## What Is Deferred and Why

**RBAC / SSO (Azure AD):** IT ticket dependency with 2+ week lead time. Filed; targeting Week 7. No path to unblock before mid-review. Full implementation design: `docs/phase3/rbac_sso_design.md`.

**API gateway:** Same Azure AD dependency. Phase 3 item alongside RBAC. Full implementation design: `docs/phase3/api_gateway_design.md`.

**uCern content (PowerChart, Clinical primary docs):** Decision pending 2026-04-26 inside the mid-review window. Two POV narratives pre-written for both outcomes: `docs/pov_narrative_ucern_granted.md`, `docs/pov_narrative_ucern_denied.md`. Demo is scoped to modules with strong KB regardless of outcome. Decision path status and open items: `docs/ucern_access_status.md`. Post-review ingest plan: `docs/post_review/plan_c_ucern_decision.md`.

**RT-01 (multi-turn clinical escalation):** ~~Deferred~~ **PATCHED (2026-04-22)** — dual-regex fast pre-check (`_PATIENT_ID_PAT` + `_CLINICAL_ACTION_PAT`) in `query_rewriter.py`. Validated via 12-case test suite and confirmed by full live red-team run (24/24). Design doc: `docs/rt01_clinical_escalation_design.md`. Residual gap (INT-04) and post-review fix design: `docs/phase3/rt01_refinement_design.md`.

**LLM swap (Groq → GPT-5.4 mini):** Planned for Phase 3 Week 2–3. Design and 4-phase validation approach: `docs/phase3/llm_swap_design.md`.

**Reranker:** Disabled pending uCern ingest. Post-uCern evaluation design: `docs/phase3/reranker_e2e_decision.md`.

---

## Post-Review Plans

Three contingency plans pre-written for the review outcome:

| Scenario | Document |
|----------|---------|
| Review goes well — Gate 2 on track | `docs/post_review/plan_a_review_positive.md` |
| Reviewers surface concerns (accuracy, Clinical, auth, LLM) | `docs/post_review/plan_b_review_concerns.md` |
| uCern decision lands during or within 48h of review | `docs/post_review/plan_c_ucern_decision.md` |

---

## Health Check Endpoint (`?health=1`)

Available as `streamlit run app.py` → navigate to `http://localhost:8501?health=1`. Returns JSON with `status`, `version`, `chroma_dir_exists`, `chunk_total`.

| State | Condition | Response |
|-------|-----------|----------|
| Green | ChromaDB dir exists AND chunk_total > 0 | `{"status": "ok", "chunk_total": 1322, ...}` |
| Degraded | ChromaDB dir missing or `get_doc_counts()` error | `{"status": "degraded", "chunk_total": 0, ...}` |
| API key invalid | Does not affect health check | Returns same as green (no Groq call) |

**Notes:** All operations are local (no network calls). Response < 50ms in all states. Streamlit always returns HTTP 200; check `status` field in JSON body, not HTTP status code. API key validity is not tested — Groq failures at query time are handled by `safe_invoke_json()` fallback chain (validated 2026-04-22, see `docs/error_handling_matrix.md`).

---

## 30/60/90 Trajectory

**30 days (by 2026-05-22):** uCern decision executed — KB expanded into PowerChart and Clinical if access granted, or scope formally narrowed. Gate 2 target (82% raw golden-set pass rate) validated. GPT-5.4 mini integration and prompt re-tuning complete. Safety: INT-04 plain-name/MRN regex gap addressed.

**60 days (by 2026-06-22):** Azure AD SSO and RBAC integration complete. End-to-end accuracy ≥ 85% (TPD-adjusted). All RT-01 through RT-06 safety findings closed (RT-01–05 patched 2026-04-22; RT-06 resolved 2026-04-21). Redis caching replacing in-process LRU for cross-session persistence.

**90 days (by 2026-07-22):** Production deployment readiness. Azure API gateway integrated. GPT-5.4 mini fully tuned and load-tested. Monitoring dashboards live. Accenture internal compliance review complete.

---

*Cerna Phase 2 Week 5 · mid-review 2026-04-22 · one-page summary*
