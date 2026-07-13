"""Narrative providers: live DeepSeek, deterministic fake, recorded replay.

The lens (app.ai.lens) builds the request and validates the reply; the
providers here only produce a raw JSON reply dict plus reporting
metadata. All three implementations share the small
:class:`NarrativeProvider` protocol so tests and the offline demo can
swap them freely.

The live provider uses the OpenAI python client pointed at the DeepSeek
base URL with JSON response mode, low temperature, a small output-token
cap, a 20-second timeout and at most ONE retry (all from config). The
API key is never logged and never included in any error message.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app import config
from app.data.provider import canonical_content_hash
from app.schemas import AiStatus

logger = logging.getLogger("pairscope.ai")


class NarrativeError(Exception):
    """A narrative provider failed. Message is safe to log (no key, no prompt)."""


@dataclass
class NarrativeCompletion:
    reply: dict  # raw JSON object returned by the model (unvalidated)
    model: str
    ai_status: AiStatus  # OK for live, RECORDED for replayed fixtures
    recorded_at: str | None = None


class NarrativeProvider(Protocol):
    @property
    def identity(self) -> str:
        """Stable identity string used in the request cache key."""
        ...

    def complete(self, system_prompt: str, payload: dict) -> NarrativeCompletion: ...


# ---------------------------------------------------------------------------
# Live DeepSeek
# ---------------------------------------------------------------------------


class DeepSeekNarrativeProvider:
    """OpenAI-compatible DeepSeek chat completion with strict JSON output.

    Runs the short classification task in plain (non-thinking) chat mode:
    JSON response format, temperature 0.1 and a small max-token cap keep
    the call fast and deterministic-ish.
    """

    @property
    def identity(self) -> str:
        return f"deepseek:{config.DEEPSEEK_MODEL}"

    def complete(self, system_prompt: str, payload: dict) -> NarrativeCompletion:
        if not config.DEEPSEEK_API_KEY:
            raise NarrativeError("DeepSeek API key is not configured.")
        try:
            from openai import OpenAI

            client = OpenAI(
                base_url=config.DEEPSEEK_BASE_URL,
                api_key=config.DEEPSEEK_API_KEY,
                timeout=config.DEEPSEEK_TIMEOUT_SECONDS,
                max_retries=config.DEEPSEEK_MAX_RETRIES,  # at most one retry
            )
            response = client.chat.completions.create(
                model=config.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(payload)},
                ],
                response_format={"type": "json_object"},
                temperature=config.DEEPSEEK_TEMPERATURE,
                max_tokens=config.DEEPSEEK_MAX_OUTPUT_TOKENS,
            )
            content = response.choices[0].message.content or ""
            reply = json.loads(content)
            if not isinstance(reply, dict):
                raise NarrativeError("DeepSeek returned JSON that is not an object.")
            return NarrativeCompletion(
                reply=reply,
                model=response.model or config.DEEPSEEK_MODEL,
                ai_status=AiStatus.OK,
            )
        except NarrativeError:
            raise
        except Exception as exc:
            # Only the exception type is surfaced — never the key or prompt.
            raise NarrativeError(
                f"DeepSeek request failed ({type(exc).__name__})."
            ) from exc


# ---------------------------------------------------------------------------
# Deterministic fake (tests / local development without a key)
# ---------------------------------------------------------------------------


class FakeNarrativeProvider:
    """Deterministic in-process provider for tests.

    With no arguments it derives a valid, boring reply from the payload.
    Tests may pass a canned ``reply`` dict (including invalid ones, to
    exercise validation) or an ``error`` to raise (to simulate timeouts).
    """

    def __init__(
        self,
        reply: dict | None = None,
        *,
        model: str = "fake-narrative",
        error: Exception | None = None,
    ):
        self._reply = reply
        self._model = model
        self._error = error

    @property
    def identity(self) -> str:
        marker = canonical_content_hash(self._reply) if self._reply is not None else "default"
        return f"fake:{self._model}:{marker}"

    def complete(self, system_prompt: str, payload: dict) -> NarrativeCompletion:
        if self._error is not None:
            raise self._error
        reply = self._reply if self._reply is not None else self._default_reply(payload)
        return NarrativeCompletion(reply=reply, model=self._model, ai_status=AiStatus.OK)

    @staticmethod
    def _default_reply(payload: dict) -> dict:
        companies = payload.get("companies", [])

        def summary(index: int) -> str:
            if index >= len(companies):
                return "No news was supplied."
            ticker = companies[index].get("ticker", "?")
            return (
                f"Recent headlines for {ticker} show routine coverage with no "
                "obvious company-specific driver."
            )

        evidence = []
        for company in companies:
            items = company.get("items", [])
            if items:
                evidence.append(
                    {
                        "claim": f"Coverage of {company.get('ticker', '?')} looks routine.",
                        "source_ids": [items[0]["source_id"]],
                    }
                )
        return {
            "summary_a": summary(0),
            "summary_b": summary(1),
            "shared_story": None,
            "classification": "NO_OBVIOUS_NEWS_EXPLANATION",
            "confidence": "LOW",
            "risk_flags": [],
            "evidence": evidence[: config.MAX_EVIDENCE_CLAIMS],
            "explanation": (
                "Deterministic fake narrative used for tests; the supplied "
                "headlines were not analysed by a live model."
            ),
        }


# ---------------------------------------------------------------------------
# Recorded replay (offline demo)
# ---------------------------------------------------------------------------


class RecordedNarrativeProvider:
    """Replays a frozen DeepSeek response from ``narrative_<A>_<B>.json``.

    Preserves the recorded model name and capture time, and reports
    ``ai_status == "recorded"`` so the UI labels it Recorded AI response,
    never live AI. The reply's content hash is verified when present.
    """

    def __init__(self, path: Path):
        self._path = Path(path)
        try:
            payload = json.loads(self._path.read_text())
            self._metadata = payload["metadata"]
            self._reply = payload["reply"]
        except (OSError, ValueError, KeyError) as exc:
            raise NarrativeError(
                f"Recorded narrative fixture '{self._path.name}' is malformed."
            ) from exc
        expected = self._metadata.get("content_hash")
        if expected and canonical_content_hash(self._reply) != expected:
            raise NarrativeError(
                f"Recorded narrative fixture '{self._path.name}' failed its "
                "integrity check (content hash mismatch)."
            )

    @classmethod
    def find(
        cls, fixtures_dir: Path | str, ticker_a: str, ticker_b: str
    ) -> RecordedNarrativeProvider | None:
        """Return a provider when a recorded fixture exists for the pair."""
        directory = Path(fixtures_dir)
        a, b = ticker_a.strip().upper(), ticker_b.strip().upper()
        for name in (f"narrative_{a}_{b}.json", f"narrative_{b}_{a}.json"):
            path = directory / name
            if path.exists():
                try:
                    return cls(path)
                except NarrativeError as exc:
                    logger.warning("recorded narrative fixture rejected: %s", exc)
                    return None
        return None

    @property
    def identity(self) -> str:
        return f"recorded:{self._path.name}"

    def complete(self, system_prompt: str, payload: dict) -> NarrativeCompletion:
        return NarrativeCompletion(
            reply=self._reply,
            model=self._metadata.get("model", "recorded"),
            ai_status=AiStatus.RECORDED,
            recorded_at=self._metadata.get("captured_at"),
        )
