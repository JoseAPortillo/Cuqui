"""Security utilities — log sanitisation to prevent credential leaks."""

from __future__ import annotations

import logging
import re

__all__ = [
    "SafeFormatter",
    "sanitize_message",
]

# Matches OpenAI API keys: sk-... or sk-proj-...
_API_KEY_PATTERN = re.compile(r"(?i)\b(sk-(?:proj-)?)[a-z0-9_-]{20,}\b")


def sanitize_message(message: str) -> str:
    """Replace OpenAI API keys in *message* with a masked placeholder."""
    return _API_KEY_PATTERN.sub(r"\1***[REDACTED]***", message)


class SafeFormatter(logging.Formatter):
    """Log formatter that sanitises credentials from the **formatted** message.

    Works after ``Formatter.format()`` has merged ``msg % args``, so it
    catches keys split between the format string and its arguments.

    Usage in a FastAPI lifespan::

        import logging
        from cuqui.adapters.api_fastapi.security import SafeFormatter

        handler: logging.Handler
        handler.setFormatter(SafeFormatter("%(levelname)s: %(message)s"))
    """

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        return sanitize_message(formatted)
