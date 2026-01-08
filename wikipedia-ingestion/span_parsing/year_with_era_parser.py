"""Parser for years with explicit era markers."""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class YearWithEraParser(SpanParserStrategy):
    """Parses years with explicit era markers (BC, BCE, AD, CE).
    
    Example: 490 BC
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse year with explicit era marker.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Lazy import to avoid circular dependency
        from strategies.list_of_years.list_of_years_span_parser import YearsParseOrchestrator
        
        # Parse year with an explicit era marker but only at the start of the string
        m = re.search(r"^\s*(\d{1,4})\s*(BC|BCE|AD|CE)\b", text, flags=re.IGNORECASE)
        if m:
            y = int(m.group(1))
            era = (m.group(2) or "").upper()
            is_bc = era in {"BC", "BCE"}
            span = Span(
                start_year=y,
                end_year=y,
                start_month=1,
                start_day=1,
                end_month=12,
                end_day=31,
                start_year_is_bc=is_bc,
                end_year_is_bc=is_bc,
                precision=SpanPrecision.YEAR_ONLY,
                match_type=f"Year with explicit era. EG: #### {era}"
            )
            return YearsParseOrchestrator._return_none_if_invalid(span)
        return None
    
    def compute_weight_days(self, span: Span) -> int | None:
        base_weight = super().compute_weight_days(span)
        if base_weight is None:
            return None
        return int(base_weight * span.precision)
