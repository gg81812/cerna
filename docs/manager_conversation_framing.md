# Manager Conversation Framing — Cerna POV

**Date:** 2026-05-04 · **Update appended 2026-05-06** (see § Update below)
**Audience:** Practice lead / client-facing manager
**Purpose:** Frame the sprint results honestly; align on next step before demo prep

---

## Update — 2026-05-06

Two findings since the original 2026-05-04 framing landed materially change
the headline numbers and the infrastructure narrative below. Both are
corrections, not new work. Original sections are preserved unchanged so the
delta is visible.

### Headline shift: 43.6% → **65.5%** (corrected)

The original 24/55 (43.6%) pass rate was inflated-against by a behavior-
detector keyword bug in `eval/run_hospital_eval.py`: the bare token
`"which"` matched relative-pronoun usage in legitimate answer-shaped
responses ("the order set **which** contains the medication…"), producing
false-positive `clarify` classifications on 12 queries. The same captured
responses, re-scored offline with the corrected detector, give:

- **36/55 (65.5%)** corrected pass rate (+12 / +21.9 pt)
- Per persona: nurse 53% · clerk 58% · physician **80%** · IT **100%** · cross 50%
- 0 pass→fail flips (the fix is conservative)
- **0 bad failures** — re-confirmed under the corrected detector
- 9 high-confidence failures → 4 (5 of the 9 were detector false positives)

**Most consequential persona shift:** IT moved from 38% to **100%** — IT
troubleshooting language has the densest relative-pronoun usage and was
hit hardest by the keyword bug. The "IT over-clarification pattern"
described in §2 below was a measurement artifact, not a real behavior
issue.

This is a measurement correction, not a system improvement. The system's
actual quality on this eval was always 65.5% — we were measuring it wrong.
Reproducible via `python eval/reclassify_hospital_eval.py`. Audit trail in
`docs/hospital_baseline.md` § Corrected Baseline.

### Redis runtime narrative — partly wrong, needs reframing

The original framing in §1 and §3 below claimed the gap between 43.6% and
the very-low live-demo number is "a single infrastructure dependency:
Redis." That is **partly wrong** and worth correcting before the demo:

- **The 43.6% (now 65.5%) eval was itself run *without* Redis.** Docker is
  not available on the company laptop and never was during the sprint;
  Redis has not been running on this dev environment at any time during
  the 9-task validation sprint. Audit details in `docs/cache_runtime_audit.md`.
- **Multi-Groq key rotation works without Redis.** The in-memory fallback
  path (`_mem_usage` / `_mem_blocked` dicts in `groq_pool.py`) rotates
  the 3 keys evenly. Redis would persist the counters across processes
  and across midnight rollovers; it is not what makes rotation work.
- **What Redis would actually add:** persistent response cache across
  app restarts, semantic cache (cosine ≥ 0.85 dedup), cross-process
  quota counters, and accurate `quota_info()` readings on the
  operational dashboard (which currently shows all keys at 0/100 in
  memory mode regardless of usage).
- **The original "~11% live demo" number** was the very first sprint run
  with a different bug (single-key lexicographic tie-breaking, all
  queries funneled to one key, rate-limited within 2 requests). That
  bug was fixed before the 24/55 measurement. The number isn't relevant
  to the current state of the system.

The honest 2026-05-06 Redis statement: *"Redis-backed cache + semantic
cache + cross-process quota tracking are implemented and tested but
inactive on this dev environment. The eval numbers (65.5%) reflect
memory-mode operation. When deployed to a Redis-equipped environment,
the existing fallback-to-Redis pattern activates persistent caching
without code change."*

### Option A as written needs revision

Option A in §3 below begins "Install Docker Desktop, run
`docker compose up -d redis`" — Docker is not approved on the company
laptop. Option A is therefore not actually a 1-hour path on this
environment. There are three real paths to enable Redis on this machine:

- **A.1** — request corp-IT approval for Docker on the laptop (lead
  time unknown)
- **A.2** — provision a managed Redis instance (Azure Cache for Redis
  or equivalent) and set `REDIS_HOST` / `CACHE_BACKEND=redis` in
  `.env`. ~1–2 hours including provisioning. Adds a network
  dependency to the demo.
- **A.3** — accept memory-mode operation and demo from there. The
  3-key rotation works; the in-process LRU helps within a session;
  the system is functionally adequate for a single-user demo. Drops
  the "production caching layer" talking point from the deck.

A separate audit doc (`docs/cache_runtime_audit.md`) lays out these
options in detail without recommending one — that's a POV-narrative
call for this conversation.

### What does **not** change

- The 3 options in §3 (demo now / expand KB then demo / deploy Redis
  then demo) are still the right shape. The number on Option A's
  expected pass rate moves from 40–70% per-persona to 53–100%
  per-persona (much stronger).
- The 0 confident-wrong-answers claim survives the reclassification.
  Two clinical-edge cases (hs-nurse-013 allergy, hs-nurse-015 dose
  change) are now classified as `actual=answer` rather than the
  buggy detector's `clarify` — they are still "honest" failures by
  the classifier definition (moderate keyword hit rates) but they
  are confident-shape *operational* answers to clinical-decision
  queries that should have refused. That is RT-01 INT-04 territory
  and worth flagging in the conversation as its own thread, not as a
  bad failure.
- Red-team 100%, vague query 84%, refusal latency 7 ms — unchanged.

### Recommended framing for the conversation

> "The headline number is now 36/55 (65.5%), up from the 43.6% I sent
> previously — that's a measurement correction, not a system improvement.
> A keyword bug in the eval detector was misclassifying 12 legitimate
> answers as failures. Same responses, corrected detector, real number is
> 65.5%. Physician 80%, IT 100% are demo-strong. The Redis layer is
> implemented but not running on my dev environment because Docker isn't
> available — the eval numbers reflect memory-mode operation, which is
> functionally adequate for a single-user demo. If we want the persistent
> caching story for the deck, we'd provision a managed Redis (option A.2,
> ~1–2 hours). Otherwise we demo as-is and frame the caching as
> production-ready architecture pending environment activation."

---

## 1. Headline Numbers

| Signal | Number | What it means |
|--------|--------|---------------|
| Answer quality (all 5 personas) | **43.6%** pass rate | 24 of 55 hospital-staff queries answered correctly — confirmed with proper key rotation active. This is the content quality story. |
| Safety red-team | **100%** (24/24) | Every adversarial, clinical, and out-of-scope probe was handled correctly. Zero regressions. |
| Retrieval accuracy | **84%** (46/55) | Vague-language queries consistently returned the right Cerner module and documentation. |
| Confident wrong answers | **0** across all runs | The system never gives a wrong answer confidently. It admits when it doesn't know. |
| Live demo (current state) | ~11% pass rate | What a live demo delivers *without Redis running* — rate limits hit, only 1 of 3 API keys used. |

**The gap between 43.6% and ~11% is a single infrastructure dependency: Redis.** With Redis running, the system distributes load across 3 Groq API keys and the rate limiting problem disappears. Without Redis, all queries funnel through one key, which exhausts its rate limit in 2 requests.

---

## 2. Product-Reality Translation

**What "43.6% pass rate" actually means for a client demo:**

The 55 hospital-staff queries were written in shift-floor language by clinical persona (nurse, ward clerk, physician, IT staff). "Pass" requires both the right module classification AND that the system's answer contains 60%+ of the expected clinical keywords.

The 43.6% is genuine content quality — confirmed across all 5 personas with proper infrastructure. Of the 55 questions:
- Nurse (40%), Clerk (42%), Physician (70%): **demo-ready stories** — physician in particular is strong
- IT/sysadmin persona: **38%** (3/8) — first real IT measurement; over-clarification pattern: system asks for clarification instead of answering, even on clear IT queries. This is a behavior tuning issue, not a KB gap.
- Cross-module queries: **30%** (3/10) — retrieval works but module classification struggles on cross-domain charge/documentation queries

**What the 0 confident-wrong-answers means:**

Every failure in our eval is "honest" — the system said it couldn't answer rather than inventing one. In practice, this means a nurse who asks a question Cerna can't answer gets: *"I don't have sufficient information on this — check uCern or your facility's configuration guide."* That's clinically safe behavior. It never says "give drug X" with false confidence.

**What the rate limit gap means:**

With Docker Desktop installed and Redis running, the 3 Groq API keys rotate under load. Each key handles ~18 queries per eval run at 8-second spacing — well within rate limits. The 43.6% content quality number is what the demo will show with Redis active.

Without Redis, all queries go through one key, which rate-limits immediately. The demo would show mostly "I'm temporarily unable to generate a response" cards.

**Bottom line:** The system is demo-ready for nurse/clerk/physician personas once Redis is running. IT and cross-module queries work but have known failure patterns (over-clarification, module classification) — frame them as "in active improvement" if the demo needs to cover all five personas.

---

## 3. Three Options

### Option A — Demo Now, Scope Nurse/Clerk/Physician Only

**Setup:** Install Docker Desktop, run `docker compose up -d redis`, demo against the three personas.  
**What the demo shows:** 40–70% pass rate on realistic shift-floor questions for clinical staff. Physician at 70% is the headline story. Red-team 100%. No confident wrong answers.  
**What it doesn't cover:** IT/sysadmin and cross-module queries (measured at 38% and 30% but with specific failure patterns). We'd frame those as "in active improvement."  
**Timeline:** Ready for demo in ~1 hour (Docker install + Redis startup + smoke test).  
**Risk:** Low. The content is strong and verified.

### Option B — Expand KB, Then Demo All Five Personas

**Setup:** (1) Fix over-clarification behavior for IT queries — tuning issue, ~1 day. (2) Add 200–400 chunks for cross-module charge capture workflows. Re-run ingestion. Re-evaluate.  
**What it adds:** IT behavior fix alone could push IT persona from 38% to 60–70%. Cross-module KB expansion could push cross-module from 30% to 50%+. Combined: overall from 43.6% toward ~55%.  
**Timeline:** 1–3 days for behavior tuning + KB curation + eval validation.  
**Risk:** Medium. KB quality is hard to predict without running the eval. Behavior tuning is lower risk.

### Option C — Deploy Redis + Load Test, Then Demo

**Setup:** Option A (Docker + Redis) plus a 20-query warm cache test and latency comparison (cold vs warm). Add the semantic cache numbers to the demo story: "Second time you ask a similar question — 10× faster."  
**What it adds:** A compelling infrastructure story for the Oracle Health practice: multi-key Groq load distribution, semantic response caching, Redis-backed quota management. Turns a POV into a production-readiness story.  
**Timeline:** 2–3 hours (Docker + smoke test + cache warm-up + latency measurement).  
**Risk:** Low-medium. Cache warm-up test is straightforward; latency numbers need to be measured, not assumed.

---

## 4. Decision-Forcing Question

> **Do we demo the nurse/clerk/physician story now (Option A, ~1 hour away) or invest 1–3 days fixing IT over-clarification behavior and expanding cross-module KB to push the overall from 43.6% toward ~55% (Option B)?**

The secondary question, if we choose Option A:

> **Do we include the infrastructure story (semantic cache, Redis-backed key rotation) in the demo deck, or keep it out and focus purely on clinical staff workflows?**

If the client cares about production reliability and scalability — include it. If the first meeting is "can this answer real Cerner questions" — leave infrastructure for the technical deep-dive.

---

*Cerna v0.5.0 · Accenture Oracle Health POV · 2026-05-04*
