"""Port — SpeechToText protocol.

Defines the contract for transcribing audio bytes into text.
Any adapter that satisfies this Protocol can be swapped in
(e.g., local faster-whisper, OpenAI Whisper API, Google STT)
without changing the application layer.

See ``cuqui/adapters/asr_faster_whisper/`` for the reference
implementation and ``cuqui/adapters/asr_openai/`` for the
cloud fallback.
"""

from __future__ import annotations

import typing

__all__ = [
    "SpeechToText",
]


class SpeechToText(typing.Protocol):
    """Transcribe audio bytes into natural-language text.

    Usage::

        stt: SpeechToText = FasterWhisperAdapter()
        text = await stt.transcribe(audio_bytes)
    """

    async def transcribe(self, audio_bytes: bytes, content_type: str | None = None) -> str:
        """Transcribe *audio_bytes* to a text string.

        *content_type* is an optional MIME type hint (e.g. ``"audio/webm"``)
        that some adapters use to determine the file format.
        """
        ...
