"""Parser for single day dates."""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class SingleDayParser(SpanParserStrategy):
    """Parses single day dates.
    
    Example: September 25
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse single day date.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Lazy import to avoid circular dependency
        from strategies.list_of_years.list_of_years_span_parser import YearsParseOrchestrator
        
        # EG: September 25
        # EG: August 29 – Christian Cross Asterism (astronomy) at Zenith of Lima, Peru.
        m = re.search(r"^\s*(?<!\d)\b(january|february|march|april|may|june|july|august|september|october|november|december)\b\s+(\d{1,2})", text, re.IGNORECASE)
        if m:
            month_name = m.group(1)
            day = int(m.group(2))
            month = YearsParseOrchestrator.month_name_to_number(month_name)
            if month is not None:
                span = Span(
                    start_year=page_year,
                    start_month=month,
                    start_day=day,
                    end_year=page_year,
                    end_month=month,
                    end_day=day,
                    start_year_is_bc=page_bc,
                    end_year_is_bc=page_bc,
                    precision=SpanPrecision.EXACT,
                    match_type="Single day within page span. EG: Month DD"
                )
                return YearsParseOrchestrator._return_none_if_invalid(span)
        return None
    
    def compute_weight_days(self, span: Span) -> int | None:
        return int(1 * span.precision)
