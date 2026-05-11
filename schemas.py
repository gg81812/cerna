"""
schemas.py — Pydantic response models for Cerna structured outputs.

The LLM is instructed (via prompt + Groq JSON mode) to respond as a CernaResponse JSON.
orchestrator.py parses the raw JSON string into this model.
ui/components.py renders it into a structured card.
"""

from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, Field, model_validator


def _close_truncated_json(s: str) -> str:
    """
    Best-effort recovery for JSON truncated at max_tokens.
    Counts open brackets/braces and appends the right number of closing tokens.
    String-aware: skips bracket characters inside string literals.
    """
    in_string = False
    escape_next = False
    opens: list[str] = []
    for ch in s:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            opens.append("}")
        elif ch == "[":
            opens.append("]")
        elif ch in ("}", "]") and opens:
            opens.pop()
    # Close any unclosed string
    if in_string:
        s += '"'
    # Close any open arrays/objects
    s += "".join(reversed(opens))
    return s


class CernaResponse(BaseModel):
    """Structured response produced by the Cerna main QA pipeline."""

    direct_answer: str = Field(
        description="Concise, direct answer with inline citations [Source: filename]."
    )
    context_explanation: str = Field(
        description="Background on the relevant Cerner module(s) and how they relate."
    )
    step_by_step: list[str] = Field(
        default_factory=list,
        description="Numbered steps if a process/config task; empty list for conceptual questions.",
    )
    best_practices: list[str] = Field(
        default_factory=list,
        description="Cerner-specific best practices and common pitfalls.",
    )
    recommendations: str = Field(
        description="What the user should do next, including uCern or build resources."
    )
    confidence: str = Field(
        default="medium",
        description="Answer confidence: 'high', 'medium', or 'low'.",
    )
    response_mode: str = Field(
        default="high",
        description=(
            "UI rendering mode derived from retrieval confidence: "
            "'high' (full structured response), "
            "'medium' (shorter with source framing), "
            "'low' (limited info with redirect). "
            "Set by the pipeline; not controlled by the LLM."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def _normalise_lists(cls, data: dict) -> dict:
        """Accept string values for list fields (LLM sometimes returns bullet strings)."""
        for key in ("step_by_step", "best_practices"):
            val = data.get(key)
            if isinstance(val, str):
                lines = [ln.lstrip("•-*0123456789.) ").strip() for ln in val.splitlines()]
                data[key] = [ln for ln in lines if ln]
        return data

    # ── Serialisation helpers ──────────────────────────────────────────────────

    @classmethod
    def parse(cls, raw: str) -> "CernaResponse":
        """
        Parse a JSON string into a CernaResponse.

        Repair sequence (in order):
          1. Strip markdown fences (```json ... ```)
          2. Remove trailing commas before ] or } (common LLM error)
          3. Truncated JSON: append missing closing brackets
          4. Pydantic model_validate_json with field defaults
        Raises ValueError if all repair attempts fail.
        """
        stripped = raw.strip()

        # 1. Strip markdown fences
        if stripped.startswith("```"):
            stripped = stripped.split("\n", 1)[-1]
            if stripped.endswith("```"):
                stripped = stripped.rsplit("```", 1)[0]
        stripped = stripped.strip()

        # 2. Remove trailing commas before ] or }
        import re as _re
        stripped = _re.sub(r",\s*([\]\}])", r"\1", stripped)

        # 3. If JSON is truncated (max_tokens hit), close open structures
        try:
            json.loads(stripped)
        except json.JSONDecodeError:
            stripped = _close_truncated_json(stripped)

        return cls.model_validate_json(stripped)

    def to_markdown(self) -> str:
        """Render the response as plain Markdown (fallback for non-card UI)."""
        parts = [f"**DIRECT ANSWER**\n{self.direct_answer}"]
        parts.append(f"\n**CONTEXT & EXPLANATION**\n{self.context_explanation}")
        if self.step_by_step:
            steps = "\n".join(f"{i}. {s}" for i, s in enumerate(self.step_by_step, 1))
            parts.append(f"\n**STEP-BY-STEP GUIDE**\n{steps}")
        if self.best_practices:
            bps = "\n".join(f"- {bp}" for bp in self.best_practices)
            parts.append(f"\n**BEST PRACTICES**\n{bps}")
        parts.append(f"\n**RECOMMENDATIONS**\n{self.recommendations}")
        return "\n".join(parts)


# ── JSON schema for prompt injection ──────────────────────────────────────────

CERNA_RESPONSE_SCHEMA = """{
  "direct_answer": "Full answer scaled to question complexity",
  "context_explanation": "Background on the Cerner module(s) and why it matters",
  "step_by_step": ["Step 1 with exact menu path...", "Step 2...", "...as many steps as needed, or [] if conceptual"],
  "best_practices": ["Cerner-specific pitfall or tip...", "...as many as relevant, or [] if none apply"],
  "recommendations": "Concrete next action with specific uCern or build resource",
  "confidence": "high | medium | low"
}"""
