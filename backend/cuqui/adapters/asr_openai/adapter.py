"""Adapter that wraps the OpenAI Whisper API to satisfy the ``SpeechToText`` protocol.

Cloud fallback adapter — requires an ``OPENAI_API_KEY`` environment variable
and incurs API costs.  Disabled by default (returns ``None`` if no key is set).

Usage::

    from cuqui.adapters.asr_openai import OpenAIWhisperAdapter

    adapter = OpenAIWhisperAdapter()
    text = await adapter.transcribe(audio_bytes)
"""

from __future__ import annotations

import logging
import os

from openai import AsyncOpenAI

from cuqui.ports.speech_to_text import SpeechToText

__all__ = [
    "OpenAIWhisperAdapter",
]

log = logging.getLogger(__name__)


class OpenAIWhisperAdapter:
    """Transcribe audio via the OpenAI Whisper REST API.

    Parameters
    ----------
    api_key:
        OpenAI API key.  Falls back to the ``OPENAI_API_KEY`` env var
        if ``None``.  Pass an empty string to keep the adapter disabled.
    model:
        OpenAI Whisper model name.  Default ``"whisper-1"``.
    language:
        Input language hint (``"es"``, ``"en"``, etc.).  Default ``"es"``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "whisper-1",
        language: str = "es",
    ) -> None:
        resolved_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            log.warning("OpenAIWhisperAdapter: no API key — disabled")
            self._disabled = True
            self._client = None
        else:
            self._disabled = False
            self._client = AsyncOpenAI(api_key=resolved_key)
        self._model = model
        self._language = language

    async def transcribe(self, audio_bytes: bytes, content_type: str | None = None) -> str:
        """Transcribe *audio_bytes* via the OpenAI Whisper API.

        *content_type* is ignored — the API auto-detects the format.
        Raises ``RuntimeError`` if the adapter is disabled (no API key).
        """
        if self._disabled or self._client is None:
            raise RuntimeError("OpenAIWhisperAdapter is disabled — no API key configured")

        from openai import NOT_GIVEN

        response = await self._client.audio.transcriptions.create(
            model=self._model,
            file=("audio.wav", audio_bytes, "audio/wav"),
            language=self._language or NOT_GIVEN,
            response_format="text",
        )
        text = response.strip() if response else ""
        log.debug("OpenAI Whisper API transcribed %d chars", len(text))
        return text
