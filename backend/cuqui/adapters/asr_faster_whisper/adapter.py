"""Adapter that wraps ``faster-whisper`` to satisfy the ``SpeechToText`` protocol.

This is the default ASR adapter — runs locally, free, offline-capable.
Model is downloaded on first ``transcribe()`` call (lazy) or can be
pre-downloaded via ``preload_model()`` with progress reporting.

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
from typing import Callable

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


class _ProgressTqdm:
    """Minimal tqdm-compatible wrapper that reports progress to a callback."""

    def __init__(
        self,
        progress_callback: Callable[[int, int, str], None] | None = None,
        description: str = "",
    ) -> None:
        self._cb = progress_callback
        self._desc = description
        self._total = 0
        self._n = 0

    def __call__(self, iterable, **kwargs):  # noqa: ANN001, ANN204
        self._total = kwargs.get("total", 0)
        self._desc = kwargs.get("description", self._desc)
        return self

    def __iter__(self):
        return iter([])

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        pass

    def update(self, n: int = 1) -> None:
        self._n += n
        if self._cb and self._total > 0:
            self._cb(self._n, self._total, self._desc)

    def close(self) -> None:
        pass


class FasterWhisperAdapter:
    """Transcribe audio via local ``faster-whisper``.

    Parameters
    ----------
    model_size:
        Whisper model size (``"tiny"``, ``"base"``, ``"small"``, ``"medium"``, etc.).
        Default ``"small"`` (~500 MB).
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
        self._model_status: str = "pending"  # pending | downloading | ready | error
        self._download_progress: float = 0.0

    @property
    def model_status(self) -> str:
        return self._model_status

    @property
    def download_progress(self) -> float:
        return self._download_progress

    @property
    def model_size(self) -> str:
        return self._model_size

    async def preload_model(
        self,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> None:
        """Pre-download and load the model, reporting progress via callback.

        If the model is already loaded, this is a no-op.
        If ``progress_callback`` is provided, it is called with
        ``(current, total, description)`` during the HuggingFace download.
        """
        if self._model is not None:
            return

        self._model_status = "downloading"
        try:
            # Pre-download via huggingface_hub so we can track progress
            from faster_whisper.utils import _MODELS

            repo_id = _MODELS.get(self._model_size, self._model_size)

            def _download() -> None:
                from huggingface_hub import snapshot_download

                tqdm_cls = type(
                    "_ProgressTqdm",
                    (_ProgressTqdm,),
                    {},
                )
                instance = tqdm_cls(progress_callback=progress_callback)

                class _TqdmFactory:
                    def __new__(cls, *a, **kw):  # noqa: ANN204
                        instance._total = kw.get("total", 0)
                        instance._desc = kw.get("description", "")
                        instance._n = 0
                        return instance

                snapshot_download(
                    repo_id,
                    tqdm_class=_TqdmFactory,
                    allow_patterns=[
                        "config.json",
                        "preprocessor_config.json",
                        "model.bin",
                        "tokenizer.json",
                        "vocabulary.*",
                    ],
                )

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _download)

            # Now load the model from cache (no re-download)
            self._model = await loop.run_in_executor(
                None,
                lambda: WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=self._compute_type,
                    local_files_only=True,
                ),
            )
            self._model_status = "ready"
            self._download_progress = 1.0
            log.info(
                "faster-whisper model %r preloaded (device=%s)",
                self._model_size,
                self._device,
            )
        except Exception:
            self._model_status = "error"
            log.exception("Failed to preload faster-whisper model %r", self._model_size)
            raise

    async def _ensure_model(self) -> WhisperModel:
        if self._model is None:
            # Fallback: load without progress tracking (e.g. model already cached)
            loop = asyncio.get_running_loop()
            self._model = await loop.run_in_executor(
                None,
                lambda: WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=self._compute_type,
                ),
            )
            self._model_status = "ready"
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
