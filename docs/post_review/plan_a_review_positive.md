# Post-Review Plan A: Review Goes Well
**Scenario:** Reviewers accept the current state, note the deferred items as appropriate for the stage, and confirm Gate 2 is on track  
**Trigger:** No major concerns raised; team maintains momentum  
**Horizon:** 30 days post-review (2026-04-27 to 2026-05-27)

---

## Immediate Actions (Week 1: 2026-04-27 to 2026-05-03)

**uCern decision (Day 1 of post-review week).**
The uCern access decision lands on or around 2026-04-26 during the mid-review. If access is granted, do not ingest immediately — wait until the review is complete and the team has confirmed no regression risk from the system as demoed. Target first ingest on 2026-04-28 or later.

Ingest sequence if granted:
1. Download the 14 gated documents (PowerChart: items 3–6; Clinical: items 7–11; RCM: items 12–14 from `docs/ucern_access_decision.md`)
2. Run `python ingest.py` and `python scripts/ingest_bge.py`
3. Run the 55-query vague eval to confirm no regression
4. Run the 5 formal benchmark queries to confirm no classification regression
5. If both pass: update `docs/cerna_status_and_pov.md` to remove archival banners and limited-coverage labels for PowerChart and Clinical
6. Update demo script to include PowerChart and Clinical module queries

**IT ticket follow-up (Day 1).**
Confirm the Azure AD app registration IT ticket is in the queue. If not filed, file it immediately. The 2+ week lead time means every day of delay shifts Gate 2.

**SME review results (if received).**
If the golden-set SME review package (sent 2026-04-20, deadline 2026-04-26) returns results, incorporate them into the eval baseline. Update `docs/golden_eval_baseline.md` with SME-validated scores.

---

## Week 2 (2026-05-04 to 2026-05-10): GPT-5.4 Mini Baseline

Primary focus: Phase 1 and 2 of the LLM swap (`docs/phase3/llm_swap_design.md`).

- Obtain OpenAI API key or confirm Azure OpenAI deployment access.
- Run the 75-query golden set with GPT-5.4 mini, no prompt changes.
- Categorize divergence cases (JSON structure, step verbosity, classification mismatches).
- Deliverable: failure mode analysis report (not a formal doc — a working notes file is sufficient).

**Parallel: reranker decision.**
If uCern docs were ingested in Week 1, run the 15-query reranker human eval (see `docs/phase3/reranker_e2e_decision.md`). The test takes one day. Decision: enable or permanently disable.

Owner: developer. No blockers if API key is available.

---

## Week 3 (2026-05-11 to 2026-05-17): GPT-5.4 Mini Tuning + RBAC Prep

**GPT-5.4 mini prompt adjustments (Phase 3 of LLM swap).**
Make targeted prompt edits based on Week 2 failure analysis. Re-run formal benchmark (5 queries) after each change.

**RBAC prep (if IT ticket confirms).**
If Azure AD app registration details arrive this week, begin implementing token validation and session management. See `docs/phase3/rbac_sso_design.md`. This can run in parallel with prompt tuning.

**RT-01 refinement decision.**
Conduct the design review ("gap or acceptable behavior?") for INT-04. If the decision is "should be refused," implement Option 2 from `docs/phase3/rt01_refinement_design.md`. Expand integration test suite. If the decision is "acceptable," document and close.

Deliverable: RT-01 decision recorded. If implemented: updated integration tests, green.

---

## Week 4 (2026-05-18 to 2026-05-24): Gate 2 Readiness Validation

**GPT-5.4 mini full benchmark (Phase 4 of LLM swap).**
Re-run the 75-query golden set after prompt adjustments. Gate acceptance criterion: KHR ≥ 73.3% (Groq baseline) AND JSON parse success = 100%.

**RBAC integration testing (if IT ticket is resolved).**
Test all four roles against the orchestrator gate. Three test scenarios per role: (1) permitted query and module, (2) denied module, (3) expired token. If IT ticket is still in queue, defer RBAC to post-Gate-2.

**Gate 2 criteria check.**
Per the Project Delivery Plan, Gate 2 requires:
- Golden-set accuracy ≥ 82% (this is the stretch target; 73.3% → 82% requires meaningful KB improvement or LLM improvement or both)
- Azure AD SSO operational (or formally deferred with written justification)
- Red-team ≥ 90% (currently 100% — this should hold without code changes)
- Latency < 5s P95 (not formally measured; latency report design targets suggest this is achievable)

If the 82% target looks unreachable by 2026-05-24: escalate to project lead for Gate 2 scope or timing discussion. Don't wait until Gate 2 day to flag the gap.

---

## Week 5 (2026-05-25 to 2026-05-27): Gate 2 Buffer

Three days for: final demo prep, pre-warm cache for Gate 2 queries, brief dry runs. No new features. No new code.

---

## Summary Table

| Week | Primary Focus | Owner | Gate 2 Dependency |
|------|--------------|-------|-------------------|
| 1 (Apr 27 – May 3) | uCern ingest (if granted), IT ticket, SME review | TBD | uCern: impacts accuracy; IT: enables RBAC |
| 2 (May 4–10) | GPT-5.4 mini Phase 1–2, reranker decision | Developer | Accuracy target |
| 3 (May 11–17) | GPT-5.4 mini Phase 3, RBAC prep, RT-01 decision | Developer | RBAC: Gate 2 criteria |
| 4 (May 18–24) | Gate 2 validation, full benchmark, RBAC test | Developer + IT | All criteria |
| 5 (May 25–27) | Buffer, demo prep | Developer | — |

---

## Gate 2 Target: On Schedule

If uCern access is granted and ingested in Week 1, and GPT-5.4 mini matches or exceeds the Groq baseline in Week 2–3, the 82% target is reachable. The primary risk is the IT ticket lead time for Azure AD — if it slips past Week 4, RBAC cannot be tested before Gate 2 and must be formally deferred with written justification accepted by reviewers.

---

*Post-review Plan A (positive outcome) · Cerna · 2026-04-22*
