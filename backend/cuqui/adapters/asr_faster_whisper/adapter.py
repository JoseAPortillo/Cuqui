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
        model_size: str = "tiny",
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

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe *audio_bytes* using local faster-whisper.

        Writes the bytes to a temporary WAV file, transcribes it,
        and returns the concatenated segment text.
        """
        model = await self._ensure_model()
        loop = asyncio.get_running_loop()

        def _run() -> str:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                tmp = f.name
            try:
                segments, info = model.transcribe(
                    tmp,
                    beam_size=5,
                    language=self._language,
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
