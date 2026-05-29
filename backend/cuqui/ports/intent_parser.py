"""Port — IntentParser protocol.

Defines the contract for parsing natural-language text into typed
``CuquiCommand`` objects.  Any adapter that satisfies this Protocol
can be swapped in without changing the application layer.

See ``cuqui/adapters/parser_rules/`` for the reference implementation.
"""

from __future__ import annotations

import typing

from cuqui.domain.commands import CuquiCommand
from cuqui.domain.parser import ParseError

__all__ = [
    "IntentParser",
]


class IntentParser(typing.Protocol):
    """Parse raw text into a ``CuquiCommand`` or ``ParseError``.

    Usage::

        parser: IntentParser = TimerParserAdapter()
        result = parser.parse("set 5 minute timer for pasta")
        if isinstance(result, ParseError):
            ...  # handle parse failure
        else:
            assert isinstance(result, CuquiCommand)
    """

    def parse(self, text: str) -> CuquiCommand | ParseError:
        """Parse *text* into a command or return a parse error."""
        ...
