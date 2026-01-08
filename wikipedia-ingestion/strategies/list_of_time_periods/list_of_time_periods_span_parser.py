"""Span parser specifically optimized for parsing time periods from Wikipedia lists."""

from span_parsing.parse_orchestrator import ParseOrchestrator
from span_parsing.factory import SpanParsers


class TimePeriodParseOrchestrator(ParseOrchestrator):
    """Span parser optimized for parsing time periods rather than specific years.

    This parser prioritizes broader time ranges and periods over specific dates,
    making it suitable for parsing historical periods, eras, and time spans.
    """

    def get_parser_steps(self) -> list[SpanParsers]:
        """Get the ordered list of parser strategies for time periods.

        Prioritizes broader time ranges and periods over specific dates,
        which is more appropriate for parsing historical time periods.

        Returns:
            Ordered list of SpanParsers to try in sequence
        """
        return [
            # Prioritize broader time ranges first
            SpanParsers.PARENTHESIZED_YEAR_RANGE,
            SpanParsers.PARENTHESIZED_DECADE,
            SpanParsers.PARENTHESIZED_YEAR_RANGE_WITH_LOCATION,
            SpanParsers.PARENTHESIZED_CIRCA_YEAR_RANGE_WITH_LOCATION,
            SpanParsers.PARENTHESIZED_CENTURY_WITH_LOCATION,
        ]
