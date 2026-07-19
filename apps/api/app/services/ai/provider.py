"""Provider-agnostic narration layer (section 13, deliverable 10).

The rest of the copilot must not depend on any one LLM vendor. A provider only
turns a set of already-computed tool summaries into plain prose; it is given no
authority to produce numbers. The default provider is fully offline and
deterministic so the platform works with no API key and tests never touch the
network. A Groq adapter is included as the real-provider seam and is used only
when a key is configured; its output still passes the numeric guardrail.
"""

from __future__ import annotations

from typing import Protocol

from app.core.config import Settings

# A short, number-free house style. Providers must not introduce figures; the
# numbers live in the structured components, each traceable to a tool result.
_SYSTEM_STYLE = (
    "You are RiskChain's catastrophe-model copilot. You explain and operate approved "
    "models. You must NOT state any numeric loss, probability, or currency figure in prose - "
    "those appear only in the attached components, computed by the deterministic engine. "
    "Keep the message to two or three plain sentences and point the user to the components."
)


class NarrationProvider(Protocol):
    name: str

    def narrate(self, mode: str, user_message: str, tool_summaries: list[str]) -> str: ...


class OfflineNarrator:
    """Deterministic, number-free narration. No external calls."""

    name = "offline-deterministic"

    _INTRO = {
        "ask": "Here is a grounded answer using the approved model library.",
        "explain": "Here is what this result means, in plain language.",
        "analyse": "Here is what the current scenario shows.",
        "run": "I ran the approved catastrophe-model chain for you.",
        "research": "Here is what the method library returns for your query.",
        "audit": "Here is an independent review of the current model run.",
    }

    def narrate(self, mode: str, user_message: str, tool_summaries: list[str]) -> str:
        intro = self._INTRO.get(mode, self._INTRO["ask"])
        if tool_summaries:
            body = " " + " ".join(tool_summaries)
        else:
            body = " I could not find an approved tool for that request, so no numbers are shown."
        tail = " Every figure below is computed by the approved engine and carries its own sources, confidence and assumptions - none of it is produced by the language model."
        return intro + body + tail


class GroqNarrator:
    """Real-provider seam. Only narrates; the numeric guardrail still applies to
    its output. Falls back to offline text if the call fails for any reason."""

    name = "groq"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._fallback = OfflineNarrator()

    def narrate(self, mode: str, user_message: str, tool_summaries: list[str]) -> str:
        try:  # pragma: no cover - network path not exercised in tests
            import httpx

            prompt = (
                f"Mode: {mode}\nUser: {user_message}\n"
                f"Verified tool summaries (do not add numbers): {tool_summaries}"
            )
            resp = httpx.post(
                f"{self._settings.groq_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._settings.groq_api_key}"},
                json={
                    "model": self._settings.groq_model,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_STYLE},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 220,
                },
                timeout=12.0,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            return self._fallback.narrate(mode, user_message, tool_summaries)


def get_provider(settings: Settings) -> NarrationProvider:
    """Select a narration provider. Offline unless a key is configured."""
    if settings.groq_api_key:
        return GroqNarrator(settings)
    return OfflineNarrator()
