"""
pii_guard.py — PII masking for query and log boundaries.

Applied at two points:
  1. pipeline.py:step_build_prompt — masks original_query and formal_query
     before they reach the LLM generation prompt, preventing PII echo.
  2. logger.py:log_interaction and pipeline.py:log_pipeline_trace — masks
     query fields before writing to JSONL logs.

Patterns are ordered from most-specific to least-specific. Each pattern
replaces matched text with a bracketed placeholder token.
"""

import re

# (compiled_pattern, replacement_string)
_PATTERNS: list[tuple[re.Pattern, str]] = [
    # SSN: 123-45-6789
    (
        re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        '[SSN_REDACTED]',
    ),
    # Explicit MRN with label: "MRN 1234567", "MRN: 9876543", "medical record 1234567"
    (
        re.compile(
            r'\b(?:MRN|mrn|medical\s+record(?:\s+number)?)\s*:?\s*\d{6,10}\b',
            re.IGNORECASE,
        ),
        '[MRN_REDACTED]',
    ),
    # Bare numeric MRN adjacent to "patient": "patient 1234567"
    (
        re.compile(r'\bpatient\s+\d{6,10}\b', re.IGNORECASE),
        'patient [MRN_REDACTED]',
    ),
    # DOB adjacent to label — slash format: "DOB 01/15/1980", "born 05/22/1965"
    (
        re.compile(
            r'\b(?:DOB|date\s+of\s+birth|born|birthday)\s*:?\s*\d{1,2}/\d{1,2}/\d{2,4}\b',
            re.IGNORECASE,
        ),
        '[DOB_REDACTED]',
    ),
    # DOB adjacent to label — ISO format: "date of birth 1965-05-22", "DOB 1965-05-22"
    (
        re.compile(
            r'\b(?:DOB|date\s+of\s+birth|born|birthday)\s*:?\s*\d{4}-\d{2}-\d{2}\b',
            re.IGNORECASE,
        ),
        '[DOB_REDACTED]',
    ),
    # Patient name: "patient John Smith", "Patient Jane Doe" (Title-case first+last)
    (
        re.compile(r'\bpatient\s+[A-Z][a-z]{1,20}\s+[A-Z][a-z]{1,20}\b', re.IGNORECASE),
        'patient [NAME_REDACTED]',
    ),
    # Titled name: "Mrs. Johnson", "Mr. Smith", "Dr. Adams" adjacent to clinical context
    (
        re.compile(r'\b(?:Mrs?|Ms|Dr)\.\s+[A-Z][a-z]{1,20}\b'),
        '[NAME_REDACTED]',
    ),
]


def mask_pii(text: str) -> str:
    """
    Apply all PII masking patterns to text. Returns the masked string.
    Patterns are applied in order; overlapping replacements are handled
    by running patterns sequentially on the already-masked string.
    """
    if not text:
        return text
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ── False-positive register ────────────────────────────────────────────────────
# Patterns to monitor:
#  - SSN \d{3}-\d{2}-\d{4}: distinctive format; low FP risk in Cerner context
#    (no standard Cerner ID uses this 3-2-4 hyphen format).
#  - MRN label: requires explicit "MRN" or "medical record" prefix; low FP risk.
#  - Patient + number: fires if a user writes "patient 1234567" — could theoretically
#    match "patient 2024" (year) but the 6-10 digit minimum avoids this.
#  - DOB adjacent to label: requires date-signaling prefix word; low FP risk.
#    Does NOT fire on standalone dates like "admitted 2024-03-15" (different format).
#  - Patient name (Title-case): requires "patient" prefix + two Title-case words.
#    Could match documentation text like "patient John Hopkins Hospital" — acceptable
#    since the goal is masking in query context, not documentation.
#  - Titled name (Mrs/Mr/Dr): intentionally aggressive — any titled name in a query
#    suggests a real patient reference.
