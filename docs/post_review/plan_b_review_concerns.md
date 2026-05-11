# Post-Review Plan B: Review Surfaces Concerns
**Scenario:** Reviewers flag one or more of the following: accuracy, Clinical module reliability, single-LLM risk, or absence of authentication  
**Trigger:** Mid-review produces specific action items or conditions that must be met before Gate 2  
**Horizon:** 30 days post-review with contingency sequences by concern type

---

## Concern Category 1: "73.3% End-to-End Accuracy Is Too Low"

**What the concern looks like:** "Your golden set says 73%. Gate 2 requires 82%. That's a 9-point gap. How confident are you that you can close it?"

**Root cause analysis first.** Before committing to a remediation plan, confirm what is driving the 73.3%. Known decomposition:
- 7 failures attributed to Groq TPD quota exhaustion (not model failures — these are infrastructure failures that would not occur on a paid tier or with GPT-5.4 mini)
- 5–7 failures attributed to KB coverage gaps (PowerChart and Clinical queries with no primary source)
- Remaining failures: genuine retrieval or generation errors

If TPD failures are removed (80.9% TPD-adjusted), the gap to 82% is 1.1 points, not 8.7 points. If reviewers accept the TPD-adjusted number as the relevant baseline, the Gate 2 target is nearly in reach with any incremental improvement.

**Remediation sequence by cause:**
1. TPD failures: switch to paid Groq tier or GPT-5.4 mini — eliminates ~7 failures immediately. Estimate: +4–5 KHR points. Timeline: 1–2 days.
2. KB coverage gaps: ingest uCern docs if granted — addresses PowerChart and Clinical failures. Estimate: +3–5 KHR points. Timeline: 1 week (including re-benchmark).
3. Retrieval failures: enable reranker (see `docs/phase3/reranker_e2e_decision.md`) — marginal improvement on borderline queries. Estimate: +1–3 KHR points. Timeline: 1–2 days.
4. Generation failures: GPT-5.4 mini prompt tuning — depends on where Llama diverges from GPT. Estimate: 0–3 KHR points. Timeline: 1 week.

**Gate 2 timing impact:** If reviewers flag the accuracy number but confirm the TPD-adjusted framing is acceptable, Gate 2 timing does not change. If reviewers require the raw number to reach 82% independently of infrastructure, Gate 2 may need to slip by 2 weeks to allow full LLM swap and benchmark cycle.

**How to present in the review:** "The 73.3% is the raw infrastructure-inclusive number. The 80.9% TPD-adjusted number removes the 7 queries that failed due to Groq daily quota exhaustion — an infrastructure constraint, not a model failure, that would not occur in production on a paid tier. The defensible floor is 78% after SME review of the golden set, which is scheduled for this week. The gap to Gate 2 at 82% is approximately 1–3 points on the adjusted baseline, achievable through the LLM swap and uCern KB expansion already planned."

---

## Concern Category 2: "Clinical Module Is Not Demo-Ready"

**What the concern looks like:** "You're showing archival banners and caveats on Clinical queries. Why is this in the demo?"

**The concern is valid.** The Clinical module uses archival secondary sources for eMAR, BCMA, and nursing workflow documentation. Primary uCern sources have not been obtained. The archival banner is honest scoping — but it does undermine the impression of completeness.

**Remediation options:**
1. **Grant uCern access and ingest:** removes the archival constraint for the 5 Clinical gated documents. Timeline: 1 week after access is granted.
2. **Drop Clinical from active demo scope:** narrows to FHIR + RCM + Millennium. The Clinical module is still accessible but not featured in the demo walk-through. No KB changes needed. Timeline: 1 day (demo script update).
3. **SME-authored Clinical content:** have a Cerner-experienced team member write verified workflow content for the 3–4 most common Clinical queries. Legitimate but resource-intensive. Timeline: 1–2 weeks.

**Recommended response to this concern:** Accept the concern, commit to option 2 (drop from active demo scope) immediately, and position uCern access as the unlock for option 1. This is not a retreat — it is honest scoping that protects the POV's credibility on the modules where the KB is strong.

**Gate 2 timing impact:** No change to Gate 2 timing. Dropping Clinical from the demo scope does not affect any gate criteria.

---

## Concern Category 3: "Single LLM Dependency on Groq Is a Production Risk"

**What the concern looks like:** "What happens when Groq has an outage? Your whole system goes down."

**Current mitigation (already in place):**
- `safe_invoke_json()` in `llm.py`: exponential backoff (3 retries, 1s/3s/9s), 8B fallback model, static graceful fallback JSON
- Circuit breaker: 5 failures in 60s → skip Groq for 120s, serve static fallback
- Demo cache: all 8 demo queries are pre-warmed; Groq outage during demo does not prevent cached queries from returning in < 100ms

**The real answer:** Groq is development infrastructure, not production infrastructure. The production plan specifies GPT-5.4 mini via Azure OpenAI, which has an Azure SLA (99.9%). The fallback chain is a development-period safety net. The concern about Groq reliability is valid but resolves itself when the LLM swap to Azure OpenAI is complete.

**Gate 2 timing impact:** If reviewers require the LLM swap to Azure OpenAI before Gate 2, that accelerates the Phase 3 timeline by 2 weeks. Document whether this is a formal condition or a recommendation.

---

## Concern Category 4: "No Authentication Is Not Acceptable for UAT"

**What the concern looks like:** "You're planning to do UAT with clinical staff and there's no login. How does that work?"

**The correct answer:** Authentication via Azure AD SSO is in Phase 3, currently blocked on an IT ticket with a 2+ week lead time. The design is complete (`docs/phase3/rbac_sso_design.md`). For UAT with clinical staff, authentication is a prerequisite — no authenticated access means no UAT with clinical data.

**Two options presented to reviewers:**
1. **Accelerate RBAC:** File or escalate the IT ticket immediately, accelerate development to Week 3, and require authentication before UAT begins. UAT slips from Week 5 to Week 6.
2. **Scope UAT to non-clinical workflows:** Conduct UAT with IT staff and administrators on FHIR API and Revenue Cycle queries (no patient-identifying data involved). Clinical staff UAT deferred until RBAC is complete.

**Recommended response:** Commit to option 2 as the default, with option 1 as the accelerated path if the IT ticket moves faster than expected. This keeps UAT on schedule for the non-clinical scope.

**Gate 2 timing impact:** If reviewers require full RBAC before Gate 2 sign-off, Gate 2 slips by approximately 3 weeks (IT ticket lead time + implementation). Flag this explicitly. Do not commit to "RBAC by Gate 2" without confirming the IT ticket timeline first.

---

## How Gate 2 Timing Changes Under Each Concern

| Concern | Gate 2 Timing | Mitigation |
|---------|--------------|------------|
| 73.3% accuracy | No change (if TPD-adjusted baseline accepted) | LLM swap, uCern KB |
| Clinical module | No change | Drop from active demo scope |
| Single LLM dependency | Depends on whether LLM swap is required | Accelerate LLM swap |
| No authentication | May slip 3 weeks if full RBAC required | Scope UAT to non-clinical |

The risk is that multiple concerns land simultaneously. If all four concerns are raised and all require remediation before Gate 2, the timeline needs a formal reset. Do not make verbal commitments in the review to close all four within the original Gate 2 window without calculating whether that is achievable.

---

## Triage Rule for the Review

If a concern is framed as: **"You should address this before Gate 2"** → Accept, add to the post-review plan, confirm timeline.

If a concern is framed as: **"This is a condition for Gate 2 sign-off"** → Document it as a Gate 2 blocker, assess whether the current timeline holds or needs to slip.

Do not accept vague commitments. If reviewers say "fix the accuracy," ask: "To confirm — are you asking us to reach 82% raw or 82% TPD-adjusted? And is this a condition for Gate 2 or a recommendation?" The precision of the ask determines the precision of the commitment.

---

*Post-review Plan B (concerns raised) · Cerna · 2026-04-22*
