"""
scripts/prewarm_demo_cache.py — Pre-warm the Cerna in-process cache for demo.

Run this BEFORE the mid-review demo (after starting the Streamlit app):
    python scripts/prewarm_demo_cache.py

Submits all 8 demo queries to the running Cerna API via Streamlit's
internal orchestrator, populating the LRU cache so each query returns
in < 100ms during the live demo.

NOTE: This script calls the orchestrator directly (bypassing the Streamlit UI).
The cache is shared in-process — run this in the SAME Python process as the
Streamlit app. The easiest way is to use the UI directly:
  1. Start `streamlit run app.py`
  2. In the chat box, type each query below in order, wait for full response.
  3. Cache is warm for the session.

This script is a convenience wrapper for programmatic pre-warming (e.g., CI).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from cache import get as cache_get, set as cache_set

# The 8 demo queries in order
DEMO_QUERIES = [
    "How do I authenticate a SMART on FHIR application with Cerner?",
    "What's the FHIR resource for a lab result, and how does it relate to the Cerner Observation API?",
    "Walk me through the charge capture workflow in Cerner Revenue Cycle.",
    "What is the Millennium domain architecture?",
    "How does BCMA scanning work?",
    "why won't my meds show up",
    "What's the best EHR for a small clinic?",
    "What dose of vancomycin for a 70kg patient with renal failure?",
]


def prewarm():
    print("Cerna Demo Cache Pre-Warm")
    print("=" * 40)

    try:
        from orchestrator import Orchestrator
    except ImportError as e:
        print(f"ERROR: Could not import orchestrator: {e}")
        print("Make sure you're running from the project root with dependencies installed.")
        sys.exit(1)

    orch = Orchestrator()

    for i, query in enumerate(DEMO_QUERIES, 1):
        cached = cache_get(query, None)
        if cached:
            print(f"  [{i}/8] CACHED   {query[:55]!r}")
            continue

        print(f"  [{i}/8] WARMING  {query[:55]!r} ...", end="", flush=True)
        t0 = time.time()
        try:
            prepared = orch.prepare(query, history=[])
            if prepared.refusal:
                # Refusal queries are instant (regex) — no LLM call, no cache needed
                print(f" REFUSAL ({int((time.time()-t0)*1000)}ms)")
                continue
            resp = orch.generate_structured(prepared)
            cache_set(query, None, resp.model_dump_json())
            print(f" OK ({int((time.time()-t0)*1000)}ms) [{resp.confidence}]")
        except Exception as exc:
            print(f" ERROR: {exc}")

    print()
    print("Pre-warm complete. Do NOT restart the app before the demo (cache is in-memory).")


if __name__ == "__main__":
    prewarm()
