"""ASR router adapter — tries primary adapter, falls back to secondary."""

from cuqui.adapters.asr.adapter import SpeechToTextRouter

__all__ = [
    "SpeechToTextRouter",
]
