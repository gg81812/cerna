"""
eval/run_hospital_eval.py — Run the hospital-staff benchmark against Cerna.

Evaluates 55 queries across 5 clinical personas (nurse, clerk, physician, IT, cross-module)
written in shift-floor language. This is the primary benchmark for the hospital-staff sprint.

Output: eval/hospital_eval_results.jsonl
Summary: printed to stdout; save to docs/hospital_baseline.md on first run.

Usage:
    python eval/run_hospital_eval.py
    python eval/run_hospital_eval.py --persona nurse
    python eval/run_hospital_eval.py --limit 10 --delay 2.0

Metrics per query:
  - pass:               True if success_criterion is met (heuristic: keyword hit rate >= 0.6
                        AND behavior matches expected_behavior)
  - keyword_hit_rate:   fraction of expected_keywords found in full response text
  - behavior_match:     True if actual behavior matches expected_behavior
  - classification_correct: True if system's module classification matches expected_module
  - latency_ms:         end-to-end wall-clock ms
  - confidence:         "high" | "medium" | "low" from CernaResponse
  - retrieval_pass:     which retrieval pass produced the answer (1/2/3 if iterative)
  - top_chunk_score:    highest semantic retrieval score
  - fail_mode:          "honest" (low-conf, clarified) | "bad" (wrong answer, no warning)
                        | "pass" — categorises failures for sprint analysis
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator import Orchestrator

_EVAL_DIR = Path(__file__).parent
_HOSPITAL_SETS = {
    "v1": _EVAL_DIR / "hospital_staff_queries.jsonl",
    "v2": _EVAL_DIR / "hospital_staff_queries_v2.jsonl",
}
_RESULTS_FILES = {
    "v1": _EVAL_DIR / "hospital_eval_results.jsonl",
    "v2": _EVAL_DIR / "hospital_eval_v2_results.jsonl",
}
HOSPITAL_SET   = _HOSPITAL_SETS["v2"]
RESULTS_FILE   = _RESULTS_FILES["v2"]

_MODULE_MAP = {
    "clinical":      "CLINICAL",
    "powerchart":    "POWERCHART",
    "revenue_cycle": "REVENUE_CYCLE",
    "millennium":    "MILLENNIUM",
    "fhir":          "FHIR",
}

import re as _re

# Bug fix (2026-05-06): the bare token "which" matched relative pronouns in
# answer-shaped responses ("the order set which contains the medication…"),
# and "what type/module/error" fired on instructional text ("determine what
# type of error is shown…"). Both produced false-positive `clarify`
# classifications on responses that were genuine answers. The substring list
# now contains only phrases that are unambiguous clarification framing; the
# regex patterns below capture interrogative "which X" / "what X …?" forms.
_BEHAVIOR_KEYWORDS = {
    "clarify":  ["could you clarify", "could you tell me", "could you share", "could you specify",
                 "can you clarify", "can you confirm", "can you tell me",
                 "are you asking", "do you mean",
                 "which one", "which of these", "which of the following", "which of the two",
                 "which scenario", "which version", "which module",
                 "which step", "which workflow", "which signature",
                 "clarify which", "specify which",
                 "a few things", "to clarify"],
    "refuse":   ["i can't advise", "i'm not able to", "i cannot provide", "not a clinical",
                 "not qualified", "consult", "please speak", "clinical decision",
                 "discuss with your", "defer"],
}

# Interrogative forms that the substring list cannot cleanly express.
# Both fire only when the phrase ends in a question mark within ~80 chars,
# which keeps them out of declarative / instructional passages.
_CLARIFY_PATTERNS = [
    _re.compile(
        r"\bwhat\s+(type|module|error|kind|version|specific|exact)\b[^.?!]{0,80}\?",
        _re.IGNORECASE,
    ),
    _re.compile(
        r"\bwhich\s+(specific|particular|exact)\b[^.?!]{0,80}\?",
        _re.IGNORECASE,
    ),
]

# Explicit decline phrases that, combined with response_mode=="low", signal a genuine redirect.
# Words like "uCern" or "facility" appear in normal source caveats (medium/high answers)
# and must NOT trigger redirect classification.
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


def load_hospital_set(persona_filter: str | None = None, version: str = "v2") -> list[dict]:
    path = _HOSPITAL_SETS[version]
    queries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                q = json.loads(line)
                if persona_filter and q["persona"] != persona_filter:
                    continue
                queries.append(q)
    return queries


def _detect_behavior(
    response_text: str,
    refusal: str,
    did_you_mean: list,
    response_mode: str = "medium",
    direct_answer: str = "",
) -> str:
    """Infer actual behavior from response content.

    redirect requires response_mode == 'low' AND explicit decline language in the
    direct_answer — keywords like 'uCern' or 'facility' appear in normal source
    caveats on medium/high answers and must not trigger redirect classification.
    """
    text_lower = (response_text + " " + refusal).lower()
    if did_you_mean:
        return "clarify"
    for kw in _BEHAVIOR_KEYWORDS["clarify"]:
        if kw in text_lower:
            return "clarify"
    for pat in _CLARIFY_PATTERNS:
        if pat.search(text_lower):
            return "clarify"
    if refusal:
        for kw in _BEHAVIOR_KEYWORDS["refuse"]:
            if kw in text_lower:
                return "refuse"
    if response_mode == "low":
        da_lower = direct_answer.lower()
        for phrase in _REDIRECT_PHRASES:
            if phrase in da_lower or phrase in text_lower:
                return "redirect"
    return "answer"


def _classify_fail_mode(
    passed: bool,
    expected_behavior: str,
    actual_behavior: str,
    confidence: str,
    keyword_hit_rate: float,
) -> str:
    if passed:
        return "pass"
    # Honest failure: system admitted uncertainty or asked for clarification
    if confidence == "low" or actual_behavior == "clarify":
        return "honest"
    # Bad failure: system gave a confident wrong answer with no warning
    if confidence == "high" and keyword_hit_rate < 0.4:
        return "bad"
    return "honest"


def evaluate_single(orch: Orchestrator, item: dict) -> dict:
    question          = item["question"]
    expected_module   = item.get("expected_module", "").upper()
    expected_behavior = item.get("expected_behavior", "answer")
    expected_keywords = item.get("expected_keywords", [])
    expected_refusal  = item.get("expected_refusal", False)

    t0 = time.time()
    try:
        prepared      = orch.prepare(question, [], module_hint=None)
        cerna_resp    = orch.generate_structured(prepared)
        latency_ms    = int((time.time() - t0) * 1000)

        response_text = cerna_resp.to_markdown()
        actual_refusal = bool(prepared.refusal)
        confidence     = cerna_resp.confidence
        top_chunk_score = max((c.semantic_score for c in prepared.chunks), default=0.0)

        # Classification accuracy
        actual_classification = prepared.classification.upper()
        classification_correct = (
            actual_classification == expected_module
            or actual_classification in (
                expected_module, _MODULE_MAP.get(expected_module.lower(), "")
            )
        )

        # Behavior detection
        actual_behavior = _detect_behavior(
            response_text, prepared.refusal or "", prepared.did_you_mean,
            response_mode=cerna_resp.response_mode,
            direct_answer=cerna_resp.direct_answer,
        )
        behavior_match = (actual_behavior == expected_behavior)

        # Keyword hit rate (over full response text + refusal text)
        full_text = (response_text + " " + (prepared.refusal or "")).lower()
        if expected_keywords:
            hits = sum(1 for kw in expected_keywords if kw.lower() in full_text)
            keyword_hit_rate = round(hits / len(expected_keywords), 3)
        else:
            keyword_hit_rate = 1.0

        # Pass: keyword hit rate >= 0.6 AND behavior matches
        # For clarify/refuse queries, behavior match is the primary criterion
        if expected_behavior in ("clarify", "refuse", "redirect"):
            passed = behavior_match
        else:
            passed = keyword_hit_rate >= 0.6 and behavior_match

        fail_mode = _classify_fail_mode(
            passed, expected_behavior, actual_behavior, confidence, keyword_hit_rate
        )

        # Retrieval pass count — read from trace if available
        retrieval_pass = 1
        state = prepared._state
        if state:
            trace = state.get("trace", [])
            retrieve_events = [e for e in trace if e.get("step") == "retrieve"]
            retrieval_pass = len(retrieve_events)

    except Exception as exc:
        latency_ms          = int((time.time() - t0) * 1000)
        response_text       = f"ERROR: {exc}"
        actual_refusal      = False
        confidence          = "error"
        top_chunk_score     = 0.0
        classification_correct = False
        actual_behavior     = "error"
        behavior_match      = False
        keyword_hit_rate    = 0.0
        passed              = False
        fail_mode           = "bad"
        retrieval_pass      = 0
        actual_classification = "ERROR"

    return {
        "id":                    item["id"],
        "persona":               item["persona"],
        "module":                item["module"],
        "expected_module":       expected_module,
        "expected_behavior":     expected_behavior,
        "difficulty":            item.get("difficulty", "medium"),
        "question":              question,
        "actual_classification": actual_classification,
        "classification_correct": classification_correct,
        "actual_behavior":       actual_behavior,
        "behavior_match":        behavior_match,
        "keyword_hit_rate":      keyword_hit_rate,
        "passed":                passed,
        "fail_mode":             fail_mode,
        "confidence":            confidence,
        "top_chunk_score":       round(top_chunk_score, 4),
        "latency_ms":            latency_ms,
        "retrieval_pass":        retrieval_pass,
        "response_excerpt":      response_text[:400],
        "success_criterion":     item.get("success_criterion", ""),
    }


def print_summary(results: list[dict]) -> None:
    total    = len(results)
    passed   = sum(1 for r in results if r["passed"])
    pass_rate = round(passed / total * 100, 1) if total else 0.0

    honest_fails = sum(1 for r in results if r["fail_mode"] == "honest")
    bad_fails    = sum(1 for r in results if r["fail_mode"] == "bad")
    cls_correct  = sum(1 for r in results if r["classification_correct"])
    behav_match  = sum(1 for r in results if r["behavior_match"])
    latencies    = [r["latency_ms"] for r in results if r["latency_ms"] > 0]

    print("\n" + "=" * 70)
    print("HOSPITAL-STAFF BENCHMARK — SUMMARY")
    print("=" * 70)
    print(f"Total queries  : {total}")
    print(f"Pass rate      : {passed}/{total} ({pass_rate}%)")
    print(f"Classification : {cls_correct}/{total} ({round(cls_correct/total*100,1)}%) correct module")
    print(f"Behavior match : {behav_match}/{total} ({round(behav_match/total*100,1)}%) expected behavior")
    print(f"Honest fails   : {honest_fails}  (system admitted uncertainty)")
    print(f"Bad fails      : {bad_fails}  (confident wrong answer)")
    if latencies:
        avg_ms = round(sum(latencies) / len(latencies))
        p95_ms = sorted(latencies)[int(len(latencies) * 0.95)]
        print(f"Latency avg    : {avg_ms}ms  p95={p95_ms}ms")

    print("\n-- By persona ------------------------------------------------------")
    for persona in ("nurse", "clerk", "physician", "it", "cross"):
        subset = [r for r in results if r["persona"] == persona]
        if not subset:
            continue
        n = len(subset)
        p = sum(1 for r in subset if r["passed"])
        print(f"  {persona:<12}: {p}/{n} ({round(p/n*100)}%) pass")

    print("\n-- Failed queries --------------------------------------------------")
    for r in results:
        if not r["passed"]:
            mode  = r["fail_mode"].upper()
            khr   = f"khr={r['keyword_hit_rate']:.0%}"
            behav = f"behav={r['actual_behavior']}"
            print(f"  [{mode}] {r['id']:<20} {khr}  {behav}  conf={r['confidence']}")
            print(f"          Q: {r['question'][:80]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", type=str, default=None,
                        help="Filter to one persona: nurse|clerk|physician|it|cross")
    parser.add_argument("--limit",   type=int,   default=None)
    parser.add_argument("--delay",   type=float, default=3.0,
                        help="Seconds between queries (default 3.0)")
    parser.add_argument("--version", type=str, default="v2", choices=["v1", "v2"],
                        help="Query set version: v1 (55 queries) or v2 (80 queries, default)")
    parser.add_argument("--output",  type=str,   default=None,
                        help="Output path (defaults to version-specific results file)")
    args = parser.parse_args()

    output_default = _RESULTS_FILES[args.version]
    if args.output is None:
        args.output = str(output_default)

    print("=" * 70)
    print(f"Cerna — Hospital-Staff Benchmark (version={args.version})")
    print("=" * 70)

    queries = load_hospital_set(args.persona, version=args.version)
    if args.limit:
        queries = queries[: args.limit]

    print(f"\nLoaded {len(queries)} queries"
          + (f" (persona={args.persona})" if args.persona else ""))
    print("Initialising orchestrator…")
    orch = Orchestrator()
    print()

    results = []
    for i, item in enumerate(queries, 1):
        print(
            f"[{i:02d}/{len(queries)}] {item['id']:<22} {item['question'][:55]}…",
            end=" ",
            flush=True,
        )
        result = evaluate_single(orch, item)
        results.append(result)
        status = "PASS" if result["passed"] else f"FAIL({result['fail_mode']})"
        print(
            f"{status:<12} khr={result['keyword_hit_rate']:.0%}  "
            f"conf={result['confidence']}  {result['latency_ms']}ms"
        )
        if args.delay > 0 and i < len(queries):
            time.sleep(args.delay)

    output_path = Path(args.output)
    if args.persona:
        output_path = output_path.parent / f"hospital_eval_results_{args.persona}.jsonl"

    with open(output_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"\nResults written to: {output_path}")
    print_summary(results)


if __name__ == "__main__":
    main()
