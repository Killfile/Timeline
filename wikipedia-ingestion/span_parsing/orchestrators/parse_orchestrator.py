"""Base class for span parsers that orchestrate multiple parsing strategies."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List

from span_parsing.factory import SpanParsers
from span_parsing.span import Span


class ParseOrchestrator(ABC):
    """Base class for span parsers that try multiple parsing strategies in order.

    Subclasses should define the order and selection of parsers to try.
    """

    _DASH_RE = re.compile(r"\s*[–—−-]\s*")

    @abstractmethod
    def get_parser_steps(self) -> List[SpanParsers]:
        """Return the ordered list of parser strategies to try.

        Returns:
            List of SpanParsers enum values in the order they should be attempted.
        """
        pass

    @staticmethod
    def is_circa_text(text: str) -> bool:
        """Check if the text indicates an approximate date (circa)."""
        return bool(re.match(r"^\s*(c\.|ca\.|circa)\s?\d{1,4}\s?(BC|AD)?", text.strip(), flags=re.IGNORECASE))

    def parse_span_from_bullet(self, text: str, span_year: int, *, assume_is_bc: bool | None = None) -> Span | None:
        """Parse a date span from bullet point text.

        Args:
            text: The text to parse
            span_year: The year from the Wikipedia page context
            assume_is_bc: Whether to assume BC/BCE if not explicitly stated

        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        if not text:
            return None

        t = text.strip()

        # Normalize dash characters
        text_to_parse = self._DASH_RE.sub("-", t)

        # Try each parser strategy in the order defined by subclass
        for step in self.get_parser_steps():
            from span_parsing.factory import SpanParserFactory
            parser = SpanParserFactory.get_parser(step)
            return_value = parser.parse(text_to_parse, span_year, bool(assume_is_bc))
            if return_value is not None:
                # Compute and set weight for the span
                if return_value.weight is None:
                    return_value.weight = parser.compute_weight_days(return_value)
                return return_value

        return None

    @staticmethod
    def _return_none_if_invalid(span: Span) -> Span | None:
        """Return None if the span is invalid, otherwise return the span.

        Args:
            span: The span to validate

        Returns:
            The span if valid, None otherwise
        """
        if span is None:
            return None
        if not span.is_valid():
            return None
        return span

    