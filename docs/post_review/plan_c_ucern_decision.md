# Post-Review Plan C: uCern Decision Lands During the Review Window
**Scenario:** The uCern access decision (due 2026-04-26) arrives on the day of or within 48 hours of the mid-review  
**Critical rule:** Do not ingest uCern content within 48 hours of the mid-review, regardless of when the decision lands

---

## The Critical Rule — Explained

If the uCern decision lands at 9am on 2026-04-26 (mid-review day) and access is granted, the instinct will be to immediately ingest the 14 documents and demo with the updated KB. **Do not do this.**

Reasons:
1. **Ingest changes the retrieval behavior.** Adding 14 new documents shifts chunk density and retrieval scores across all five modules. Queries that returned high-confidence responses before ingest may return different results after. This has not been tested.
2. **The demo is pre-warmed.** The LRU cache contains responses to all 8 demo queries. After ingest, the KB state changes but the cache does not — the cached responses were generated from the pre-ingest KB. Cache invalidation must happen before the first post-ingest demo run.
3. **The verification pass is already done.** The system is in a known-good state as of 2026-04-22. Any change before the review introduces unknown regression risk that cannot be re-verified in time.
4. **The review evaluates what was built, not what is being built.** If reviewers ask about PowerChart and Clinical, the honest answer is "limited coverage now, unlocked pending uCern access decision" — a confident answer based on a known state. Rushing a same-day ingest to change that answer is theater, not substance.

**When to ingest:** After the review is complete, the team is rested, and there is time for a proper verification cycle. Target: 2026-04-28 or later.

---

## If uCern Access Is Granted

### Ingest Sequence (starting 2026-04-28)

**Day 1: Download and prepare.**
Download the 14 gated documents from the uCern portal. Convert any PDF exports to plain text (`.txt` or `.md`). Place in appropriate `data/[module]/` directories. Update `scripts/doc_manifest.json` with source type (`primary`), doc_type, and priority_tier for each new document.

**Day 2: Ingest and validate.**
1. Run `python ingest.py` — adds new documents to ChromaDB with BGE embeddings
2. Run `python scripts/ingest_bge.py` to confirm the BGE collection is updated
3. Verify chunk count increased as expected (estimate: +150–300 chunks across PowerChart, Clinical, RCM)
4. Run `python eval/vague_query_eval.py` — confirm 55/55 still pass (regression check)
5. Run the 5 formal benchmark queries manually — confirm no classification regressions
6. Run the 8 demo queries manually — confirm responses reflect new content where expected

**Day 3: Demo script update.**
Update `docs/demo_script.md` to include PowerChart and Clinical demo queries. Remove the archival banner notes from Q4 and Q5 talking points if the banner no longer fires. Add a Q9 (PowerChart-specific) and Q10 (Clinical advanced) to the extended demo.

Update UI positioning strings in `app.py` or wherever module banners are configured — PowerChart and Clinical should no longer show "limited" labels after primary sources are ingested.

Update `docs/cerna_status_and_pov.md` Section 6 (POV): remove the "limited coverage" language for PowerChart and Clinical. Update the KB inventory table.

**Day 4: Re-benchmark.**
Re-run the 75-query golden set with updated KB. Record new KHR. Update `docs/golden_eval_baseline.md`. This becomes the new baseline for Gate 2.

**Day 5 onward: Normal Phase 3 schedule (Plan A).**
Proceed with Plan A post-review schedule. The reranker decision test is now timely — run it on the updated KB.

### Narrative Shift

With uCern access granted and ingested, the POV narrative shifts from Path B (FHIR + RCM specialist, limited modules) to the full five-module positioning. The external message becomes: "Cerna covers all five Oracle Health modules — FHIR, Millennium, Revenue Cycle, PowerChart, and Clinical — with primary Oracle documentation across all modules."

The archival banners come down. The "limited" labels come off. The demo can confidently show any module.

This is the stronger POV. Gate 2 accuracy target (82%) becomes more reachable with primary sources in PowerChart and Clinical replacing archival secondary content.

### Communication Plan

- Notify reviewers (or the engagement lead) that uCern access was granted and content is being ingested
- Updated benchmark numbers are available by 2026-04-30
- Revised demo script available for Gate 2 planning call

---

## If uCern Access Is Denied

### Immediate Actions (Day 1 post-decision)

1. Confirm the denial is definitive — denied by Oracle Health, or denied because no team member holds current Oracle Health credentials?
2. If denied by Oracle Health: escalate to Accenture Oracle Health practice lead to understand whether a formal engagement access request is possible.
3. If denied because no team member holds credentials: assess whether acquiring credentials through the Oracle Partner Network (free account) provides access to CustomerConnect community content (lower quality than uCern Help Center but publicly-supported documentation).

### Permanent Scope Narrowing

Update `docs/cerna_status_and_pov.md` Section 6:
- Remove PowerChart and Clinical from the active module roadmap
- Change "limited — uCern docs pending" to "FHIR, Millennium, Revenue Cycle — primary source documentation"
- Retire the uCern access pending language from all external-facing materials

Update `docs/pov_narrative_ucern_denied.md` (already pre-written) — activate this as the canonical POV narrative.

The three-module positioning is not a failure scenario. FHIR + RCM + Millennium covers:
- Every interoperability mandate question under 21st Century Cures Act (FHIR)
- The most common Cerner revenue cycle implementation questions (RCM — 18 files, 83k words, strong KB)
- Platform architecture and CCL scripting questions (Millennium — 19 files, 80k words)

This is a credible, differentiated specialist POV. The Clinical and PowerChart modules are explicitly positioned as "community-content supported, primary documentation not available — verify critical workflow steps against your Oracle Help Center."

### KB Stabilization

With denial confirmed, the KB state is stable: no more ingestion attempts for PowerChart or Clinical gated content. Redirect Phase 3 KB work to:
1. Deepening the RCM content (Items 12–14 from `docs/ucern_access_decision.md` if Oracle Partner Network provides access)
2. Adding additional FHIR resources (official HL7 spec, Cerner Ignite documentation that may be publicly available through GitHub archives)
3. SME-authored content for Millennium advanced topics (CCL performance tuning, MPages advanced configuration) — if a Cerner-experienced team member is available to write verified content

### Gate 2 Implications

Gate 2 accuracy target (82%) becomes harder without uCern docs. Current baseline: 73.3% raw (80.9% TPD-adjusted). Three-module specialist positioning may actually improve accuracy on answered queries because the model isn't attempting to answer PowerChart and Clinical workflow questions from archival sources. Queries that currently fail due to KB coverage gaps on Clinical and PowerChart would route to a scoped refusal rather than a low-confidence generic answer.

Recommend re-running the 75-query golden set after KB stabilization to establish the denial-scenario baseline. If the new baseline is ≥ 78% raw, Gate 2 at 82% is reachable via LLM swap and retrieval improvements alone.

### Communication Plan

- Notify reviewers that uCern access has been definitively denied
- Present the three-module specialist positioning as the permanent POV (not a fallback)
- Remove "pending uCern access" language from all presentations going forward
- Update Gate 2 accuracy target discussion: 82% is achievable for the three-module scope; the denied modules are explicitly out of scope

---

## Summary Decision Tree

```
uCern decision arrives 2026-04-26
│
├─ Decision is YES (granted)
│   ├─ Before review? → Do NOT ingest until 2026-04-28
│   └─ After review? → Begin ingest sequence immediately
│       └─ Day 1: Download + manifest
│       └─ Day 2: Ingest + vague eval + benchmark queries
│       └─ Day 3: Demo script + UI positioning update
│       └─ Day 4: Full 75-query re-benchmark
│       └─ Day 5+: Proceed with Plan A schedule
│
└─ Decision is NO (denied)
    ├─ Confirm: denied by Oracle Health vs. no credentials?
    │   └─ No credentials: escalate to Oracle Partner Network assessment
    │   └─ Denied by Oracle Health: proceed to permanent narrowing
    ├─ Activate pov_narrative_ucern_denied.md
    ├─ Update positioning: FHIR + Millennium + RCM only
    ├─ Redirect KB work: deepen existing three modules
    └─ Re-run 75-query golden set on narrowed scope
```

---

*Post-review Plan C (uCern decision) · Cerna · 2026-04-22*
