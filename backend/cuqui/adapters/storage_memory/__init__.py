"""In-memory storage adapter — implements ``Storage`` protocol via dict."""

from cuqui.adapters.storage_memory.adapter import InMemoryTimerStore

__all__ = [
    "InMemoryTimerStore",
]
