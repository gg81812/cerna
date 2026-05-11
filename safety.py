"""
safety.py — Safety guardrails for Cerna.

Three functions:
  classify_query()      — Classify query as in_scope / clinical_decision / out_of_domain
  check_confidence()    — Gate on retrieval score quality before answering
  requires_citation()   — Flag clinical queries that need chunk scores above threshold

Uses GROQ_MODEL_FAST (llama-3.1-8b-instant) for minimal latency overhead.
"""

from __future__ import annotations

import re
from typing import Optional

from langchain_core.messages import HumanMessage

from config import GROQ_API_KEY, GROQ_MODEL_FAST, CONFIDENCE_THRESHOLD, CITATION_SCORE_THRESHOLD

_fast_llm = None


def _get_fast_llm():
    global _fast_llm
    if _fast_llm is None:
        from langchain_groq import ChatGroq
        _fast_llm = ChatGroq(
            model=GROQ_MODEL_FAST,
            groq_api_key=GROQ_API_KEY,
            temperature=0.0,
            max_tokens=16,
        )
    return _fast_llm


_SAFETY_PROMPT = """\
Classify the following question into exactly ONE of these categories:

in_scope          — Question is about Cerner / Oracle Health products, workflows, \
configuration, APIs, or implementation.
clinical_decision — Question asks Cerna to make a patient-specific clinical decision, \
diagnosis, prescribe medication, or recommend treatment for a specific patient.
out_of_domain     — Question has no relation to Cerner, Oracle Health, or healthcare IT.

Respond with ONE word only: in_scope, clinical_decision, or out_of_domain.

Question: {question}

Category:"""

# Fast keyword-based pre-check avoids unnecessary LLM calls for obvious cases
_OUT_OF_DOMAIN_PATTERNS = re.compile(
    r"\b(recipe|weather|sports|stock|bitcoin|crypto|game|movie|song|celebrity|"
    r"relationship|joke|poem|lottery|covid vaccine|diet plan|stock market)\b",
    re.IGNORECASE,
)

_CLINICAL_DECISION_PATTERNS = re.compile(
    r"\b(prescribe|diagnose|should (?:i|the patient) take|what dose|drug interaction|"
    r"is it safe to take|what medication for|clinical recommendation for patient)\b",
    re.IGNORECASE,
)

# Refusal messages keyed by classification.
# All refusals now redirect rather than dead-end — they block the refusal part
# while offering a useful next step or explaining the workflow side of the question.
REFUSAL_MESSAGES: dict[str, str] = {
    "out_of_domain": (
        "That falls outside my area of expertise. I'm Cerna, specialised in Oracle Health "
        "(Cerner) implementation and configuration.\n\n"
        "For that topic, you might try:\n"
        "- **General computing or IT questions** → your facility's IT help desk or IT knowledge base\n"
        "- **Clinical procedures or protocols** → your facility's clinical education resources or policy library\n"
        "- **Oracle Health product questions** → uCern community at cernercentral.com\n\n"
        "I'm happy to answer questions about Millennium, PowerChart, Revenue Cycle, FHIR APIs, "
        "or clinical workflows in Cerner. What would you like to explore?"
    ),
    "competitive": (
        "I focus on Cerner-specific questions and don't make comparisons with other EHR vendors. "
        "For independent EHR comparisons, KLAS Research and Black Book Rankings publish vendor "
        "evaluations — your Accenture account team can also provide current competitive intelligence.\n\n"
        "I'm happy to go deep on any specific Cerner capability, architecture, or workflow — "
        "what aspect of Oracle Health would be most useful to explore?"
    ),
    "advisory": (
        "Business case metrics — ROI, total cost of ownership, headcount, and implementation "
        "timelines — are outside my knowledge base. Those are best covered by your Accenture "
        "Oracle Health practice leads who have current benchmark data from comparable programmes.\n\n"
        "I can help with the technical side: configuration, integrations, module architecture, and workflows. "
        "What specific Cerner capability or workflow can I dig into for you?"
    ),
    "accenture": (
        "Accenture's practice strategy, delivery methodology, and client-specific recommendations "
        "are best discussed with your engagement lead — that's outside what I can speak to.\n\n"
        "I'm here to provide deep Oracle Health (Cerner) product knowledge to support those conversations. "
        "What Cerner topic can I help with?"
    ),
    "roadmap": (
        "My knowledge is based on Oracle Health documentation up to my training cutoff, so I can't "
        "speak to future roadmap announcements or recent releases.\n\n"
        "For the latest, check:\n"
        "- **Oracle Health website** → oracle.com/health\n"
        "- **uCern community** → cernercentral.com (release notes, community announcements)\n\n"
        "I can answer in-depth questions about current Cerner capabilities and configuration."
    ),
    "market": (
        "Market share figures, KLAS rankings, and analyst ratings are outside my knowledge base. "
        "Your Accenture account team will have up-to-date competitive intelligence on Oracle Health's "
        "market position.\n\n"
        "I can help with product capabilities, implementation detail, and technical architecture — "
        "what Cerner topic would be useful?"
    ),
    "clinical_decision": (
        "I'm Cerna, a Cerner **workflow** specialist — I can explain how Cerner clinical tools work, "
        "but I can't make patient-specific clinical decisions, recommend medications, or advise on doses.\n\n"
        "**What I can help with (the Cerner workflow side):**\n"
        "- How BCMA override workflows function and what documentation is required\n"
        "- How eMAR administration tasks are created and managed\n"
        "- How CPOE order checking and alert overrides work in PowerChart\n"
        "- How allergy alerts are triggered and documented\n\n"
        "**For the clinical decision itself** — whether to proceed, what dose, whether it's safe "
        "for this patient — please consult the prescribing physician or your facility's clinical protocol.\n\n"
        "Is there a specific Cerner workflow question I can help with?"
    ),
    # RT-01 INT-04: clinical-decision-disguised-as-workflow. Used when the query
    # combines an administration verb with a clinical-conflict context (allergy
    # override, dose discrepancy, drug interaction) and seeks a decision rather
    # than a workflow walkthrough. The redirect names the specific clinical
    # resource appropriate to the conflict type, not just "the prescribing
    # physician" — the user needs somewhere useful to go.
    "clinical_decision_int04": (
        "**This is a clinical decision, not a Cerner workflow question.** The right answer depends "
        "on your patient's specific situation, and I'm not the right tool to make that call — even "
        "though Cerner's UI lets the action proceed.\n\n"
        "**Where to take this question:**\n"
        "- **Medication-allergy conflicts** (give vs hold despite documented allergy) → "
        "  consult your **pharmacist** or the **ordering provider**; follow your facility's "
        "  allergy-override and reconciliation protocol\n"
        "- **Dose changes / dose discrepancies** (old dose vs new dose, MAR mismatch) → "
        "  contact the **prescribing clinician** to confirm the active order; follow your facility's "
        "  medication titration and order-change protocol\n"
        "- **Drug interactions / contraindications** (proceed vs hold) → "
        "  consult your **pharmacist** or the **P&T (Pharmacy & Therapeutics) committee** "
        "  guidance for your facility\n\n"
        "**What I *can* help with on the Cerner side:**\n"
        "- How allergy alerts are triggered, displayed, and overridden in eMAR/BCMA — "
        "  including the documentation fields the override requires\n"
        "- How order changes flow from PharmNet/CPOE to the eMAR, and how to refresh or "
        "  reconcile the MAR when the displayed dose looks stale\n"
        "- How drug-interaction alerts work in CPOE and how facility-level rule overrides "
        "  are configured\n\n"
        "If you'd like, ask me about the **workflow** for one of these areas and I'll walk you "
        "through it — the clinical decision itself stays with the clinician and pharmacist."
    ),
}

# Template for workflow-side-only responses when a query touches clinical edges.
# Used by step_clinical_decision to provide partial help even on refused queries.
CLINICAL_WORKFLOW_REDIRECT = (
    "I can't advise on the clinical decision, but I can explain the Cerner workflow side:\n\n"
    "{workflow_context}\n\n"
    "For the clinical decision — whether to proceed, what dose, whether this is appropriate for "
    "this patient — consult the prescribing physician or your facility's clinical protocol."
)


def classify_query(query: str) -> str:
    """
    Classify query as 'in_scope', 'clinical_decision', or 'out_of_domain'.
    Uses fast keyword checks first; falls back to LLM for ambiguous cases.
    """
    # Fast keyword checks
    if _OUT_OF_DOMAIN_PATTERNS.search(query):
        return "out_of_domain"
    if _CLINICAL_DECISION_PATTERNS.search(query):
        return "clinical_decision"

    # LLM-based classification for ambiguous queries
    try:
        llm = _get_fast_llm()
        result = llm.invoke([HumanMessage(content=_SAFETY_PROMPT.format(question=query))])
        raw = result.content.strip().lower().split()[0] if result.content.strip() else ""
        if raw in ("in_scope", "clinical_decision", "out_of_domain"):
            return raw
    except Exception as exc:
        print(f"[Safety] classify_query error: {exc}")

    return "in_scope"   # fail-open: if classifier errors, let the query through


def check_confidence(chunks: list, threshold: Optional[float] = None) -> bool:
    """
    Return True if retrieval quality is sufficient to answer confidently.
    Uses semantic_score (cosine similarity, calibrated 0-1) not RRF fusion score.
    """
    if not chunks:
        return False
    t = threshold if threshold is not None else CONFIDENCE_THRESHOLD
    return any(c.semantic_score >= t for c in chunks)


def requires_citation(classification: str, chunks: list) -> bool:
    """
    Return True when a high-stakes module query lacks a high-confidence cited chunk.
    Clinical, FHIR, and Revenue Cycle answers must be grounded in a chunk with
    semantic_score >= CITATION_SCORE_THRESHOLD (0.50) or the answer is downgraded.
    Uses semantic_score (cosine similarity) not RRF fusion score.
    """
    high_stakes = classification.upper() in ("CLINICAL", "FHIR", "REVENUE_CYCLE")
    if not high_stakes:
        return False
    return not any(c.semantic_score >= CITATION_SCORE_THRESHOLD for c in chunks)
