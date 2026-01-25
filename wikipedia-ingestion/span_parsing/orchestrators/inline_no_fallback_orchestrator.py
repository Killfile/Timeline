from span_parsing.factory import SpanParsers
from span_parsing.orchestrators.parse_orchestrator import ParseOrchestrator

class InlineNoFallbackOrchestrator(ParseOrchestrator):
    """Orchestrator that tries inline parsers without a fallback option."""
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
        ]