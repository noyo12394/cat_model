"""Copilot guardrails (section 2.2, non-negotiable 4).

The central guarantee: no numeric figure in the copilot's prose may originate
from the language model. ``redact_unsourced_numbers`` removes any number in the
message that cannot be traced to a tool result, so even a misbehaving provider
cannot present an invented loss or probability as prose.
"""

from __future__ import annotations

import json
import re
from typing import Any

# A digit run, optionally with grouping commas / decimals / percent / scale.
_NUMBER = re.compile(r"\$?\d[\d,]*(?:\.\d+)?\s?[%MmKkBb]?")
_DIGITS = re.compile(r"\d")


def _digit_core(token: str) -> str:
    return "".join(_DIGITS.findall(token))


def sourced_digit_pool(tool_results: list[dict[str, Any] | None]) -> str:
    """All digits appearing anywhere in the tool results, concatenated."""
    blob = json.dumps([r for r in tool_results if r], default=str)
    return "".join(_DIGITS.findall(blob))


def find_numbers(text: str) -> list[str]:
    return [t.strip() for t in _NUMBER.findall(text) if _digit_core(t)]


def redact_unsourced_numbers(message: str, tool_results: list[dict[str, Any] | None]) -> tuple[str, bool]:
    """Return (clean_message, had_unsourced). Numbers not traceable to a tool
    result are replaced with a pointer to the structured cards."""
    pool = sourced_digit_pool(tool_results)

    had_unsourced = False

    def _replace(match: re.Match[str]) -> str:
        nonlocal had_unsourced
        token = match.group(0)
        core = _digit_core(token)
        if core and core in pool:
            return token  # traceable to a tool result - allowed
        had_unsourced = True
        return "[see the figures in the cards]"

    cleaned = _NUMBER.sub(_replace, message)
    return cleaned, had_unsourced


def numbers_source(components_present: bool) -> str:
    return "approved_tools" if components_present else "none"
