# uCern Access — Decision Path Status
**Date:** 2026-04-22  
**Decision deadline:** 2026-04-26 (mid-review day)  
**Related docs:** `docs/ucern_access_decision.md` (full context), `docs/post_review/plan_c_ucern_decision.md`

---

## Purpose of This Document

The uCern decision is due in four days. This document is not about resolving the access issue — it is about confirming whether the decision path is active or has quietly stalled. A stalled decision that nobody surfaces before 2026-04-26 is worse than a clean "access denied" — it leaves the team preparing for a POV pivot that may or may not happen, and it surfaces as an open item in the review with no owner.

---

## Current Status

**Request filed:** Unknown.

The `docs/ucern_access_decision.md` (written 2026-04-19) frames uCern access as a business decision requiring the project lead's input. It names three scenarios (A: access granted, B: delayed, C: denied) and sets a decision deadline of 2026-04-26. It does not record whether an actual access request was submitted to Oracle Health, or whether the decision is about access Oracle Health must grant vs. a team-internal decision about whether someone with existing credentials can download content.

**This gap must be resolved by end of day 2026-04-23 (tomorrow) to maintain the 2026-04-26 decision window.**

---

## What Is Known

| Item | Status |
|------|--------|
| 14 gated documents identified and listed | Done — `docs/ucern_access_decision.md` |
| Ingest procedure documented | Done — `docs/kb_gap_inventory.md`, `Cerna_Missing_Documents_List.md` |
| Scenarios A/B/C pre-written | Done — `docs/pov_narrative_ucern_granted.md`, `docs/pov_narrative_ucern_denied.md` |
| Post-review ingest plan documented | Done — `docs/post_review/plan_c_ucern_decision.md` |
| Decision path active and owned | **UNKNOWN — open item** |

---

## What Is Unknown (Open Items)

**OI-1: Has a formal uCern access request been submitted?**

The Oracle Health uCern portal (help.oracle.com/healthcare, formerly ucern.com) requires an Oracle Health customer or partner account. Access requests are typically submitted by the Accenture Oracle Health practice lead or by a team member who holds current Oracle Health engagement credentials.

Does any team member currently have uCern/Oracle Help Center credentials? If yes, can they access and download the 14 documents listed in `docs/ucern_access_decision.md`?

**Owner to resolve:** Project lead / Accenture Oracle Health practice lead.  
**Deadline:** 2026-04-23 (tomorrow).

---

**OI-2: Who is the Accenture-side owner of this decision?**

The `docs/ucern_access_decision.md` was written for "[project lead / Accenture engagement manager]" — the owner is bracketed, not named. Decisions with unnamed owners do not get made.

**Owner to resolve:** Whoever is reading this document should either (a) own this decision or (b) name who does, in writing, by end of day 2026-04-23.

---

**OI-3: Who is the Oracle Health-side contact?**

If the team does not have existing credentials, is there an Oracle Health engagement manager or partner relationship manager who could facilitate portal access? This question is only relevant if the team does not already have access — but if they don't, knowing the Oracle Health contact is the only path to Scenario A.

**Owner to resolve:** Accenture Oracle Health practice lead.  
**Deadline:** Only relevant if OI-1 answer is "no credentials."

---

**OI-4: When was the last communication or follow-up on this request?**

The escalation document was written 2026-04-19. As of 2026-04-22, there is no recorded follow-up. Either:
(a) The project lead was notified and is actively pursuing the decision — in which case this document adds nothing except confirmation.
(b) The escalation document was written, saved, and not acted on — in which case this document is the follow-up.

**Owner to resolve:** Project lead.  
**Action required:** Respond to the `docs/ucern_access_decision.md` escalation with a status update by 2026-04-23.

---

## Escalation Path (If No Movement by 2026-04-24)

If OI-1 through OI-4 are unresolved by 2026-04-24 (two days before the deadline):

1. **Assume Scenario B** (access delayed indefinitely). Update all external materials to reflect FHIR + RCM + Millennium positioning. Remove "pending uCern access" language from the demo script and review materials.
2. **Notify the mid-review audience** (whoever is reviewing on 2026-04-26) that the uCern decision did not land before the review and the team is proceeding with the three-module positioning.
3. **Do not present the uCern decision as "pending" in the review** if no one owns it. A pending decision with no owner is an open risk, not a deferred item.

Escalation contact (to be filled in): [Accenture Oracle Health practice lead name and contact].

---

## Decision Communication Path

How will the uCern decision reach the Cerna team?

**If access is confirmed:**
- Who confirms it? The person with credentials downloads a test document and reports success.
- How does the team know? Direct message to the developer running ingest.
- When can ingest begin? Per `docs/post_review/plan_c_ucern_decision.md`: not before 2026-04-28 (after the mid-review) regardless of when the decision lands.

**If access is denied:**
- Who delivers the denial? The project lead communicates that no team member holds current Oracle Health credentials and the Oracle Partner Network path is not viable within the project timeline.
- How does the team know? Written confirmation in the project channel.
- What triggers next steps? Receipt of the denial message triggers activation of `docs/pov_narrative_ucern_denied.md` and permanent scope narrowing.

**If the decision simply doesn't arrive:**
- Default to Scenario B by end of day 2026-04-24.
- No further waiting. Certainty is more valuable than the possibility of a better outcome.

---

## Recommended Actions by Date

| Date | Action | Owner |
|------|--------|-------|
| **2026-04-23** (tomorrow) | Confirm whether any team member holds uCern/Oracle Help Center credentials | Project lead |
| **2026-04-23** | Name the owner of this decision explicitly | Project lead |
| **2026-04-24** (two days before deadline) | If no resolution: default to Scenario B, update materials | Developer |
| **2026-04-26** (mid-review day) | If access granted: note it in review, commit to post-review ingest (2026-04-28) | Project lead |
| **2026-04-28** | Begin ingest sequence if access granted | Developer |

---

*uCern access status · Cerna · 2026-04-22*
