"""Main span parser class with validation and utility methods."""

from __future__ import annotations

import re
from span_parsing.span import Span
from span_parsing.factory import SpanParsers, SpanParserFactory
from span_parsing.orchestrators.parse_orchestrator import ParseOrchestrator

class YearsParseOrchestrator(ParseOrchestrator):
    """Module for parsing date spans from text."""


    def get_parser_steps(self) -> list[SpanParsers]:
        """Get the ordered list of parser strategies for time periods.

        Prioritizes broader time ranges and periods over specific dates,
        which is more appropriate for parsing historical time periods.

        Returns:
            Ordered list of SpanParsers to try in sequence
        """
        return [
            # Prioritize broader time ranges first
            SpanParsers.PARENTHESIZED_SHORT_YEAR_RANGE,
            SpanParsers.MONTH_AND_DAY_RANGE_WITHIN_PAGE_SPAN_ACROSS_YEARS,
            SpanParsers.MONTH_AND_DAY_RANGE_WITHIN_PAGE_SPAN_ACROSS_MONTHS,
            SpanParsers.MONTH_AND_DAY_RANGE_WITHIN_PAGE_SPAN,
            SpanParsers.MONTH_AND_DAY_WITHIN_PAGE_SPAN,
            SpanParsers.MONTH_ONLY_WITHIN_PAGE_SPAN,
            SpanParsers.YEAR_RANGE,
            SpanParsers.PARENTHESIZED_YEAR,
            SpanParsers.YEAR_WITH_EXPLICIT_ERA,
            SpanParsers.YEAR_ONLY,
            SpanParsers.CIRCA_YEAR,
            SpanParsers.FALLBACK,
        ]

    @classmethod
    def parse_span_from_bullet(cls, text: str, span_year: int, *, assume_is_bc: bool | None = None) -> Span | None:
        """Classmethod wrapper to provide backward compatibility with old code that
        called this method on the class rather than an instance.
        """
        # Call the base class instance implementation directly to avoid
        # accidentally invoking the classmethod again on the instance.
        return ParseOrchestrator.parse_span_from_bullet(cls(), text, span_year, assume_is_bc=assume_is_bc)

