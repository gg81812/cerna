"""
tests/test_json_parsing.py — JSON parse repair tests for schemas.py

Verifies that CernaResponse.parse() handles common LLM output artifacts:
markdown fences, trailing commas, truncated JSON, and missing optional fields.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from schemas import CernaResponse, _close_truncated_json

_VALID = {
    "direct_answer": "BCMA is the barcode medication administration system.",
    "context_explanation": "BCMA integrates with eMAR.",
    "step_by_step": ["Scan patient wristband", "Scan medication barcode"],
    "best_practices": ["Always verify two patient identifiers"],
    "recommendations": "See uCern BCMA configuration guide.",
    "confidence": "high",
}


def test_parse_clean_json():
    raw = json.dumps(_VALID)
    r = CernaResponse.parse(raw)
    assert r.direct_answer == _VALID["direct_answer"]
    assert r.confidence == "high"


def test_parse_markdown_fence_json():
    raw = "```json\n" + json.dumps(_VALID) + "\n```"
    r = CernaResponse.parse(raw)
    assert r.direct_answer == _VALID["direct_answer"]


def test_parse_markdown_fence_no_lang():
    raw = "```\n" + json.dumps(_VALID) + "\n```"
    r = CernaResponse.parse(raw)
    assert r.confidence == "high"


def test_parse_trailing_comma_in_array():
    raw = json.dumps(_VALID).replace(
        '"Scan medication barcode"]',
        '"Scan medication barcode",]'
    )
    r = CernaResponse.parse(raw)
    assert len(r.step_by_step) == 2


def test_parse_trailing_comma_in_object():
    raw = json.dumps(_VALID).replace('"confidence": "high"}', '"confidence": "high",}')
    r = CernaResponse.parse(raw)
    assert r.confidence == "high"


def test_parse_missing_optional_lists():
    minimal = {
        "direct_answer": "Yes.",
        "context_explanation": "This is context.",
        "recommendations": "Check uCern.",
        "confidence": "medium",
    }
    r = CernaResponse.parse(json.dumps(minimal))
    assert r.step_by_step == []
    assert r.best_practices == []


def test_close_truncated_json_simple():
    truncated = '{"direct_answer": "answer", "step_by_step": ["step 1"'
    repaired = _close_truncated_json(truncated)
    parsed = json.loads(repaired)
    assert parsed["direct_answer"] == "answer"


def test_close_truncated_json_nested():
    truncated = '{"direct_answer": "ok", "step_by_step": ["a", "b'
    repaired = _close_truncated_json(truncated)
    data = json.loads(repaired)
    assert "direct_answer" in data
