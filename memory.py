"""
memory.py — Conversation history buffer for Cerna.

Maintains a rolling window of the last MAX_HISTORY_EXCHANGES user/assistant
pairs. Provides formatted representations for LLM prompts.
"""

from __future__ import annotations

from config import MAX_HISTORY_EXCHANGES


class ConversationBuffer:
    """
    Stores up to MAX_HISTORY_EXCHANGES (user, assistant) exchange pairs.
    Thread-safe within a single Streamlit session (single-threaded).
    """

    def __init__(self):
        self._exchanges: list[tuple[str, str]] = []   # (user_msg, assistant_msg)

    def add_exchange(self, user_message: str, assistant_message: str) -> None:
        """Append a completed turn and trim to the rolling window."""
        self._exchanges.append((user_message, assistant_message))
        if len(self._exchanges) > MAX_HISTORY_EXCHANGES:
            self._exchanges.pop(0)

    def to_message_list(self) -> list[dict]:
        """Return history as [{"role": ..., "content": ...}] pairs for LLM."""
        messages = []
        for user_msg, asst_msg in self._exchanges:
            messages.append({"role": "user",      "content": user_msg})
            messages.append({"role": "assistant",  "content": asst_msg})
        return messages

    def to_prompt_string(self) -> str:
        """Return history as a plain-text block for prompt injection."""
        if not self._exchanges:
            return ""
        lines = []
        for user_msg, asst_msg in self._exchanges:
            lines.append(f"User: {user_msg}")
            lines.append(f"Assistant: {asst_msg[:300].rstrip()}{'…' if len(asst_msg) > 300 else ''}")
        return "\n".join(lines)

    def is_empty(self) -> bool:
        return len(self._exchanges) == 0

    def last_user_message(self) -> str | None:
        if not self._exchanges:
            return None
        return self._exchanges[-1][0]

    def clear(self) -> None:
        self._exchanges.clear()

    @classmethod
    def from_message_list(cls, messages: list[dict]) -> "ConversationBuffer":
        """Reconstruct from a Streamlit session_state messages list."""
        buf = cls()
        user_msg = None
        for m in messages:
            if m["role"] == "user":
                user_msg = m["content"]
            elif m["role"] == "assistant" and user_msg is not None:
                buf.add_exchange(user_msg, m["content"])
                user_msg = None
        return buf
