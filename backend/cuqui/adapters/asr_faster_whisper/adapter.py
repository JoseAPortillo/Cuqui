"""Adapter that wraps ``faster-whisper`` to satisfy the ``SpeechToText`` protocol.

This is the default ASR adapter — runs locally, free, offline-capable.
Model is loaded lazily on first ``transcribe()`` call.

Usage::

    from cuqui.adapters.asr_faster_whisper import FasterWhisperAdapter

    adapter = FasterWhisperAdapter(model_size="tiny", language="es")
    text = await adapter.transcribe(audio_bytes)
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

from cuqui.ports.speech_to_text import SpeechToText

__all__ = [
    "FasterWhisperAdapter",
]

log = logging.getLogger(__name__)

_CONTENT_TYPE_EXT: dict[str, str] = {
    "audio/webm": ".webm",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
}


def _ext_from_content_type(content_type: str | None) -> str:
    """Map a MIME type to a file extension for ffmpeg.

    Returns ``.wav`` as the fallback when the type is unknown or ``None``.
    """
    if not content_type:
        return ".wav"
    # Handle extended types like "audio/webm;codecs=opus"
    base = content_type.split(";")[0].strip()
    return _CONTENT_TYPE_EXT.get(base, ".wav")


class FasterWhisperAdapter:
    """Transcribe audio via local ``faster-whisper``.

    Parameters
    ----------
    model_size:
        Whisper model size (``"tiny"``, ``"base"``, ``"small"``, etc.).
        Default ``"tiny"`` (~150 MB) — fastest, least accurate.
    device:
        Computation device (``"cpu"`` or ``"cuda"``).  Default ``"cpu"``.
    compute_type:
        Precision type (``"int8"``, ``"float16"``, ``"float32"``).
        Default ``"int8"`` — best speed/accuracy trade-off on CPU.
    language:
        Language code hint passed to the model (e.g. ``"es"``, ``"en"``).
        Default ``"es"``.
    """

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "es",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._language = language
        self._model: WhisperModel | None = None

    async def _ensure_model(self) -> WhisperModel:
        if self._model is None:
            loop = asyncio.get_running_loop()
            self._model = await loop.run_in_executor(
                None,
                lambda: WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=self._compute_type,
                ),
            )
            log.info("faster-whisper model %r loaded (device=%s)", self._model_size, self._device)
        return self._model

    async def transcribe(self, audio_bytes: bytes, content_type: str | None = None) -> str:
        """Transcribe *audio_bytes* using local faster-whisper.

        Writes the bytes to a temporary file (extension inferred from
        *content_type*), transcribes it, and returns the concatenated
        segment text.
        """
        model = await self._ensure_model()
        loop = asyncio.get_running_loop()

        suffix = _ext_from_content_type(content_type)
        log.info("faster-whisper transcribe: %d bytes, suffix=%s, content_type=%r", len(audio_bytes), suffix, content_type)

        def _run() -> str:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(audio_bytes)
                tmp = f.name
            try:
                segments, info = model.transcribe(
                    tmp,
                    beam_size=8,
                    language=self._language,
                    condition_on_previous_text=False,
                )
                text = " ".join(seg.text.strip() for seg in segments)
                log.debug(
                    "faster-whisper transcribed %d segments (duration=%.1fs)",
                    info.duration if info else 0,
                )
                return text.strip()
            finally:
                Path(tmp).unlink(missing_ok=True)

        return await loop.run_in_executor(None, _run)
