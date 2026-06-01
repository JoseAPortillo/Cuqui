"""ASR router — tries the primary adapter, falls back to a secondary adapter.

The router allows a primary (local, free) adapter and an optional
secondary (cloud, paid) fallback.  If the primary raises or returns
empty text, the secondary is tried.

Usage::

    from cuqui.adapters.asr import SpeechToTextRouter
    from cuqui.adapters.asr_faster_whisper import FasterWhisperAdapter
    from cuqui.adapters.asr_openai import OpenAIWhisperAdapter

    router = SpeechToTextRouter(
        primary=FasterWhisperAdapter(),
        fallback=OpenAIWhisperAdapter(),
    )
    text = await router.transcribe(audio_bytes)
"""

from __future__ import annotations

import logging

from cuqui.ports.speech_to_text import SpeechToText

__all__ = [
    "SpeechToTextRouter",
]

log = logging.getLogger(__name__)


class SpeechToTextRouter:
    """Composite adapter that delegates to *primary* with *fallback* support.

    Parameters
    ----------
    primary:
        The default ``SpeechToText`` adapter (e.g. local faster-whisper).
    fallback:
        Optional secondary adapter (e.g. OpenAI Whisper API).
        Skipped if ``None``.
    """

    def __init__(
        self,
        primary: SpeechToText,
        fallback: SpeechToText | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    async def transcribe(self, audio_bytes: bytes, content_type: str | None = None) -> str:
        """Transcribe via *primary*; fall back to *secondary* on failure.

        *content_type* is forwarded to each adapter as a format hint.

        Raises ``RuntimeError`` if both adapters fail.
        """
        text = await self._try_transcribe(self._primary, audio_bytes, content_type, "primary")
        if text:
            return text

        if self._fallback is not None:
            text = await self._try_transcribe(self._fallback, audio_bytes, content_type, "fallback")
            if text:
                return text

        raise RuntimeError("All ASR adapters failed to produce a transcription")

    async def _try_transcribe(
        self,
        adapter: SpeechToText,
        audio_bytes: bytes,
        content_type: str | None,
        label: str,
    ) -> str:
        """Attempt transcription with a single adapter."""
        try:
            text = await adapter.transcribe(audio_bytes, content_type)
            if text:
                log.info("ASR %s succeeded (%d chars)", label, len(text))
                return text
            log.warning("ASR %s returned empty text", label)
        except Exception:
            log.exception("ASR %s failed", label)
            return ""
        return ""
