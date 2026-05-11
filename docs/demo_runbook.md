# Cerna — Demo Runbook
**Mid-review demo · 2026-04-26**  
**Print this page. Keep it on the desk during the demo.**

---

## Before the Session (T-30 min)

1. `streamlit run app.py` — confirm UI loads
2. Run cache pre-warm: type all 8 demo queries once in order
3. Confirm all 8 return responses (not errors)
4. Note the Streamlit URL (default: `http://localhost:8501`)
5. Have this runbook printed or visible on a second monitor/phone

---

## Scenario 1 — Groq Rate-Limits Mid-Demo (429)

**What you'll see:** Response takes longer than usual, then shows: *"Cerna is temporarily unable to generate a detailed response. Please try your question again in a moment, or rephrase it."* Confidence badge shows `low`.

**What this is:** The `safe_invoke_json` wrap caught the 429, retried once after 2 seconds, still failed, and returned the graceful fallback. This is the error handling working correctly.

**What to do:**
- Do NOT apologize or look flustered. Say: "The graceful fallback is working — rather than showing a raw API error, the system is telling the user to try again. That's the error handling we shipped this week."
- If the query was pre-warmed in cache: this shouldn't happen. If cache was lost (app restart), queries won't cache-hit. Re-run the pre-warm if you restarted the app.
- Wait 10 seconds and try the same query again — it should return from cache if it was pre-warmed earlier in the session.

---

## Scenario 2 — Retrieval Returns Weak Scores

**What you'll see:** Response card renders with `confidence: medium` or `low`, or a "Did you mean...?" chip row appears instead of a full response card.

**What this is:** The quality gate fired — the top retrieved chunk scored below threshold. This is honest scoping working correctly.

**What to do:**
- For **did-you-mean**: "This is the low-confidence fallback — the system recognized it couldn't answer confidently and is suggesting related searches. Click one of these." Click the most relevant chip.
- For **medium/low confidence**: "The confidence indicator is telling us something. The system has partial information and is signalling that. In a production deployment this would trigger a uCern link rather than guessing." Continue narrating.
- Do NOT try to re-run the query hoping for a better result. Pivot to the next query in the script.

---

## Scenario 3 — Reviewer Asks an Off-Script Question

**What to do:**
- If you know the answer confidently: run the query, show the result, continue
- If you're not sure: "Let me note that and we can follow up in writing — I want to show you the next part of the demo." Do not try to answer live if uncertain.
- If the question is about a known gap (RT-01, uCern access, RBAC): give the prepared answer from the demo script "Anticipated Questions" section
- Do not let off-script questions consume more than 2 minutes

---

## Scenario 4 — A Rendering Bug Appears

**What you'll see:** A section of the response card is missing, a badge renders incorrectly, or the layout breaks.

**What to do:**
- Take a screenshot if possible (for post-demo follow-up)
- Say: "I'm going to move on — I'll show you a screenshot of known-good state."
- Have screenshots of known-good responses ready (capture them at end of Day 3 pre-warm)
- Continue with the next query

**Known-good screenshots to have ready:**
- FHIR query response (green source pill, step_by_step populated)
- Clinical query response (amber archival banner visible)
- Safety refusal response (clinical decision message)

---

## Scenario 5 — Internet / Network Drops

**What you'll see:** Retrieval and LLM calls fail. The `safe_invoke_json` wrap will catch the network error and return the graceful fallback card.

**What to do:**
- The Streamlit UI still serves locally — the interface will not crash
- Say: "Network hiccup — the graceful fallback is showing. The UI stays up, retrieval and generation fail cleanly. Let me show you a cached response." 
- If a query was pre-warmed, navigate to a cached query: the in-process cache will return the pre-warmed response even without internet (cache is in-memory, not a network call)
- Cached queries: all 8 demo queries pre-warmed before session start

---

## Scenario 6 — App Crashes or Won't Start

**What to do:**
- Check: is `GROQ_API_KEY` set in `.env`? `cat .env | grep GROQ`
- Check: is ChromaDB accessible? Look for errors about `chroma_store/` in the terminal
- Check: Python dependencies? `pip install -r requirements.txt`
- If app can't be recovered in 3 minutes: have the mid_review_summary.md and demo_script.md ready for a narrative-only walkthrough. "Let me walk you through the architecture and show you the evaluation numbers directly."

---

## Emergency Numbers (Narrative Fallback)

If the demo cannot run at all, these are the numbers to present:

| Metric | Number |
|--------|--------|
| KB size | 1,322 chunks, 98 documents |
| Retrieval (vague queries) | 84% (55/55 pass) |
| End-to-end accuracy | 73.3% raw / 80.9% TPD-adjusted |
| Red-team | 18/24 (75%) — 21/24 after RT-03 patch |
| Roleplay attacks blocked | 5/5 (100%) |
| PII masking | 7/7 test cases pass |
| Modules | FHIR, Millennium, Revenue Cycle, PowerChart (limited), Clinical (limited) |

---

## Cache Pre-Warm Procedure

Run before every session. Takes ~3 minutes.

1. Start app: `streamlit run app.py`
2. Type each query in order — wait for full response before the next:
   1. `How do I authenticate a SMART on FHIR application with Cerner?`
   2. `What's the FHIR resource for a lab result, and how does it relate to the Cerner Observation API?`
   3. `Walk me through the charge capture workflow in Cerner Revenue Cycle.`
   4. `What is the Millennium domain architecture?`
   5. `How does BCMA scanning work?`
   6. `why won't my meds show up`
   7. `What's the best EHR for a small clinic?`
   8. `What dose of vancomycin for a 70kg patient with renal failure?`
3. Confirm all 8 returned responses (refusals count — they're instant from regex)
4. Do NOT restart the app between pre-warm and demo (cache is in-memory, lost on restart)

---

*Demo runbook · Cerna mid-review 2026-04-26 · Print this page.*
