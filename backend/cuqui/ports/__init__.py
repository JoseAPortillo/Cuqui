"""Ports — framework-agnostic contracts for the application layer."""

from cuqui.ports.intent_parser import IntentParser
from cuqui.ports.speech_to_text import SpeechToText
from cuqui.ports.storage import Storage

__all__ = [
    "IntentParser",
    "SpeechToText",
    "Storage",
]
