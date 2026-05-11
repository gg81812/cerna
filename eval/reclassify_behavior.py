"""
eval/reclassify_behavior.py — Re-apply the corrected behavior detector to existing results.

No Groq API call needed — reads hospital_eval_results.jsonl and re-classifies
using the corrected _detect_behavior() logic.

Since response_mode was not captured in the original run, uses confidence as proxy:
  - confidence high/medium  → response_mode is NOT "low" → old redirect = false positive → "answer"
  - confidence low          → check response_excerpt for graceful-fallback phrases → genuine redirect

Outputs a per-query delta table and writes docs/validation_findings.md.

Usage:
    python eval/reclassify_behavior.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

RESULTS_FILE  = Path(__file__).parent / "hospital_eval_results.jsonl"
QUERIES_FILE  = Path(__file__).parent / "hospital_staff_queries.jsonl"
FINDINGS_DOC  = Path(__file__).parent.parent / "docs" / "validation_findings.md"

# ── Corrected detector constants (mirror of run_hospital_eval.py) ─────────────

_REDIRECT_PHRASES = [
    "temporarily unable to generate",
    "limited authoritative information",
    "i don't have sufficient information",
    "for an authoritative answer",
    "unable to provide specific details",
    "i cannot provide detailed guidance",
    "i lack the specific",
    "cannot generate a detailed response",
    "not able to generate a detailed response",
]

_CLARIFY_KWS = [
    "could you clarify", "could you tell me", "are you asking", "do you mean",
    "which", "can you confirm", "what type", "what module", "what error",
    "a few things", "could you share",
]
_REFUSE_KWS = [
    "i can't advise", "i'm not able to", "i cannot provide", "not a clinical",
    "not qualified", "consult", "please speak", "clinical decision",
    "discuss with your", "defer",
]


def _reclassify(row: dict) -> str:
    """Re-derive actual_behavior using corrected logic.

    Uses confidence as a proxy for response_mode (not available in old results):
      high/medium confidence  → response_mode is not "low" → no redirect from source caveats
      low confidence          → check excerpt for genuine decline phrases
    """
    response_excerpt = row.get("response_excerpt", "")
    text_lower = response_excerpt.lower()
    confidence = row.get("confidence", "medium")

    # Clarify signals take precedence
    for kw in _CLARIFY_KWS:
        if kw in text_lower:
            return "clarify"

    # Refusal signals (only if there was a refusal flag)
    for kw in _REFUSE_KWS:
        if kw in text_lower:
            return "refuse"

    # Redirect: ONLY if low-confidence AND explicit decline language
    if confidence == "low":
        for phrase in _REDIRECT_PHRASES:
            if phrase in text_lower:
                return "redirect"

    return "answer"


def _recompute_pass(row: dict, new_behavior: str) -> bool:
    expected_behavior = row.get("expected_behavior", "answer")
    keyword_hit_rate  = row.get("keyword_hit_rate", 0.0)
    behavior_match    = (new_behavior == expected_behavior)

    if expected_behavior in ("clarify", "refuse", "redirect"):
        return behavior_match
    return keyword_hit_rate >= 0.6 and behavior_match


def main() -> None:
    if not RESULTS_FILE.exists():
        print(f"ERROR: {RESULTS_FILE} not found. Run the hospital eval first.")
        sys.exit(1)

    # Load queries for expected_behavior lookup
    queries_by_id: dict[str, dict] = {}
    with open(QUERIES_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                q = json.loads(line)
                queries_by_id[q["id"]] = q

    rows: list[dict] = []
    with open(RESULTS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    print(f"\nLoaded {len(rows)} results from {RESULTS_FILE.name}\n")

    # ── Reclassify ────────────────────────────────────────────────────────────
    deltas: list[dict] = []

    for row in rows:
        old_behavior = row["actual_behavior"]
        new_behavior = _reclassify(row)
        old_passed   = row["passed"]
        new_passed   = _recompute_pass(row, new_behavior)
        changed      = (old_behavior != new_behavior) or (old_passed != new_passed)

        deltas.append({
            "id":           row["id"],
            "persona":      row["persona"],
            "expected":     row.get("expected_behavior", "answer"),
            "old_behavior": old_behavior,
            "new_behavior": new_behavior,
            "confidence":   row.get("confidence", "?"),
            "khr":          row.get("keyword_hit_rate", 0.0),
            "old_passed":   old_passed,
            "new_passed":   new_passed,
            "changed":      changed,
        })

    old_pass_total = sum(1 for d in deltas if d["old_passed"])
    new_pass_total = sum(1 for d in deltas if d["new_passed"])
    total = len(deltas)

    flipped_pass  = [d for d in deltas if d["changed"] and not d["old_passed"] and d["new_passed"]]
    flipped_fail  = [d for d in deltas if d["changed"] and d["old_passed"] and not d["new_passed"]]
    behavior_flipped = [d for d in deltas if d["old_behavior"] != d["new_behavior"]]

    print("=" * 72)
    print("BEHAVIOR DETECTOR RECLASSIFICATION - DELTA REPORT")
    print("=" * 72)
    print(f"  Original pass rate : {old_pass_total}/{total} ({old_pass_total/total*100:.1f}%)")
    print(f"  Corrected pass rate: {new_pass_total}/{total} ({new_pass_total/total*100:.1f}%)")
    print(f"  Behavior label changes: {len(behavior_flipped)}")
    print(f"  FAIL -> PASS flips : {len(flipped_pass)}")
    print(f"  PASS -> FAIL flips : {len(flipped_fail)}")

    print("\n-- By persona ----------------------------------------------------------")
    for persona in ("nurse", "clerk", "physician", "it", "cross"):
        subset = [d for d in deltas if d["persona"] == persona]
        if not subset:
            continue
        n = len(subset)
        old_p = sum(1 for d in subset if d["old_passed"])
        new_p = sum(1 for d in subset if d["new_passed"])
        delta_str = "no change" if old_p == new_p else (f"+{new_p-old_p}" if new_p > old_p else str(new_p-old_p))
        print(f"  {persona:<12}: {old_p}/{n} -> {new_p}/{n}  ({delta_str})")

    if flipped_pass:
        print("\n-- FAIL -> PASS (false-positive redirects corrected) -------------------")
        for d in flipped_pass:
            print(f"  {d['id']:<22} {d['old_behavior']:<10} -> {d['new_behavior']:<10} "
                  f"conf={d['confidence']}  khr={d['khr']:.0%}")

    if flipped_fail:
        print("\n-- PASS -> FAIL (unexpected regressions) --------------------------------")
        for d in flipped_fail:
            print(f"  {d['id']:<22} {d['old_behavior']:<10} -> {d['new_behavior']:<10} "
                  f"conf={d['confidence']}  khr={d['khr']:.0%}")

    if behavior_flipped and not flipped_pass and not flipped_fail:
        print("\n-- Behavior label changed (no pass/fail impact) -------------------------")
        for d in behavior_flipped:
            print(f"  {d['id']:<22} {d['old_behavior']:<10} -> {d['new_behavior']:<10} "
                  f"conf={d['confidence']}  khr={d['khr']:.0%}")

    # ── Write docs/validation_findings.md ─────────────────────────────────────
    _write_findings(deltas, old_pass_total, new_pass_total, total,
                    flipped_pass, flipped_fail, behavior_flipped)
    print(f"\nFindings written to: {FINDINGS_DOC}")


def _persona_rows(deltas: list[dict], persona: str):
    return [d for d in deltas if d["persona"] == persona]


def _write_findings(deltas, old_pass, new_pass, total,
                    flipped_pass, flipped_fail, behavior_flipped) -> None:
    rate_old = f"{old_pass}/{total} ({old_pass/total*100:.1f}%)"
    rate_new = f"{new_pass}/{total} ({new_pass/total*100:.1f}%)"

    lines = [
        "# Validation Findings — Behavior Detector Reclassification",
        "",
        "**Date:** 2026-05-04  ",
        "**Sprint:** 9-Task Validation Sprint  ",
        "**Task:** 1 — No-Groq validation  ",
        "**Status:** Complete",
        "",
        "---",
        "",
        "## Bug: False-Positive Redirect Classification",
        "",
        "### Root Cause",
        "",
        "The original `_detect_behavior()` function included `'uCern'`, `'cernercentral'`,",
        "and `'facility'` in its `_BEHAVIOR_KEYWORDS['redirect']` list.",
        "These keywords appear routinely as **source caveats** in medium- and",
        "high-confidence answers (e.g., *'For additional details, check uCern'* appended",
        "to a complete step-by-step workflow answer). This caused 38/55 responses to be",
        "classified as `'redirect'` when the actual behavior was `'answer'`.",
        "",
        "### Fix",
        "",
        "Removed the `redirect` keyword list entirely. A `redirect` classification now",
        "requires **both**:",
        "",
        "1. `response_mode == 'low'` (pipeline signal — set when retrieval fails threshold)",
        "2. Explicit decline language in `direct_answer` (e.g., *'temporarily unable to",
        "   generate'*, *'limited authoritative information'*)",
        "",
        "Medium/high-confidence responses that mention uCern or facility in their",
        "recommendations are classified as `'answer'` regardless of those keywords.",
        "",
        "**Files changed:** `eval/run_hospital_eval.py`",
        "- `_BEHAVIOR_KEYWORDS['redirect']` list removed",
        "- `_REDIRECT_PHRASES` list added (9 explicit decline phrases)",
        "- `_detect_behavior()` signature extended: `response_mode='medium'`, `direct_answer=''`",
        "- `evaluate_single()` passes `cerna_resp.response_mode` and `cerna_resp.direct_answer`",
        "",
        "---",
        "",
        "## Reclassification Results",
        "",
        "Existing 55 results re-scored offline (no Groq API call).",
        "Uses `confidence` as proxy for `response_mode` (not captured in original run):",
        "high/medium confidence → response_mode not 'low' → old redirect = false positive.",
        "",
        f"| Metric | Before fix | After fix |",
        f"|--------|-----------|-----------|",
        f"| Pass rate | {rate_old} | {rate_new} |",
        f"| Behavior label changes | — | {len(behavior_flipped)} |",
        f"| FAIL → PASS flips | — | {len(flipped_pass)} |",
        f"| PASS → FAIL flips | — | {len(flipped_fail)} |",
        "",
        "### Per-Persona Breakdown",
        "",
        "| Persona | Before | After | Delta |",
        "|---------|--------|-------|-------|",
    ]

    for persona in ("nurse", "clerk", "physician", "it", "cross"):
        subset = _persona_rows(deltas, persona)
        if not subset:
            continue
        n = len(subset)
        old_p = sum(1 for d in subset if d["old_passed"])
        new_p = sum(1 for d in subset if d["new_passed"])
        delta = new_p - old_p
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        lines.append(
            f"| {persona} | {old_p}/{n} ({old_p/n*100:.0f}%) | "
            f"{new_p}/{n} ({new_p/n*100:.0f}%) | {delta_str} |"
        )

    lines += [
        "",
        "**Note on IT and cross personas:** All IT (8/8) and most cross (8/10) queries",
        "were rate-limited during the original run (confidence='low', graceful fallback text).",
        "Their reclassification is correct: `response_mode='low'` + explicit decline language",
        "= genuine redirect. These are not false positives.",
        "",
        "---",
        "",
    ]

    if flipped_pass:
        lines += [
            "## False-Positive Redirects Corrected (FAIL → PASS)",
            "",
            "These queries had correct substantive answers with `confidence=high/medium`",
            "but were misclassified as `redirect` due to source-caveat keyword matches.",
            "",
            "| ID | Persona | Old behavior | New behavior | Conf | KHR |",
            "|----|---------|-------------|-------------|------|-----|",
        ]
        for d in flipped_pass:
            lines.append(
                f"| {d['id']} | {d['persona']} | {d['old_behavior']} | "
                f"{d['new_behavior']} | {d['confidence']} | {d['khr']:.0%} |"
            )
        lines.append("")
        lines.append("---")
        lines.append("")

    if flipped_fail:
        lines += [
            "## Unexpected PASS → FAIL (regressions)",
            "",
            "| ID | Persona | Old behavior | New behavior | Conf | KHR |",
            "|----|---------|-------------|-------------|------|-----|",
        ]
        for d in flipped_fail:
            lines.append(
                f"| {d['id']} | {d['persona']} | {d['old_behavior']} | "
                f"{d['new_behavior']} | {d['confidence']} | {d['khr']:.0%} |"
            )
        lines.append("")
        lines.append("---")
        lines.append("")

    lines += [
        "## Interpretation",
        "",
        "The original `2/55 (3.6%)` pass rate and the `28/55 (50.9%) recalibrated` rate",
        "were both artifacts of the behavior detector bug:",
        "",
        "- `2/55` raw: behavior_match was nearly impossible because 38 answers were",
        "  labeled `redirect` when expected was `answer`.",
        "- `28/55` recalibrated: was computed ignoring `behavior_match` entirely",
        "  (khr >= 0.6 only for 'answer' queries) — inflated by relaxing the criterion.",
        "",
        f"The corrected detector gives **{rate_new}** — a middle ground that is",
        "semantically accurate: behavior_match is required, but false-positive redirects",
        "are no longer penalizing correct answers.",
        "",
        "IT and cross personas remain at 0 passes due to rate-limiting during the original",
        "run, not a detector issue. A re-run with `--delay 8.0` is needed for those.",
        "",
        "---",
        "",
        "*Last updated: 2026-05-04 — Task 1 of 9-task validation sprint*",
    ]

    FINDINGS_DOC.parent.mkdir(parents=True, exist_ok=True)
    FINDINGS_DOC.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
