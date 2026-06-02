"""Adapter that wraps ``TimerParser`` to satisfy the ``IntentParser`` protocol.

This is the reference implementation of the inbound parser port.
It delegates all ``parse()`` calls to the domain ``TimerParser``
with default language ``"es"``.

Usage::

    from cuqui.adapters.parser_rules.adapter import TimerParserAdapter

    adapter = TimerParserAdapter()           # Spanish, default
    adapter = TimerParserAdapter(lang="en")  # English
    result = adapter.parse("set 5 minute timer for pasta")
"""

from __future__ import annotations

from cuqui.domain.commands import CuquiCommand
from cuqui.domain.parser import ParseError, TimerParser

__all__ = [
    "TimerParserAdapter",
]


class TimerParserAdapter:
    """Wrap ``TimerParser`` as an ``IntentParser``-compatible adapter.

    Parameters
    ----------
    lang:
        Language code passed to the underlying ``TimerParser``
        (default ``"es"``).
    """

    def __init__(self, lang: str = "es") -> None:
        self._parser = TimerParser(lang=lang)

    def parse(self, text: str) -> CuquiCommand | ParseError:
        """Delegate to ``TimerParser.parse(text)``."""
        return self._parser.parse(text)
