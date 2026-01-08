"""Parser for date ranges within a single year spanning multiple months."""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class SingleYearMultiMonthDayRangeParser(SpanParserStrategy):
    """Parses date ranges that span multiple months within a single year.
    
    Example: September 28 – October 2
    """
    
    
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse date range across multiple months in the same year.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Lazy import to avoid circular dependency
        from strategies.list_of_years.list_of_years_span_parser import YearsParseOrchestrator
        MONTH_NAMES = "(january|february|march|april|may|june|july|august|september|october|november|december)"
        # EG: September 28 – October 2
        m = re.search(rf"^\s*(?<!\d)\b{MONTH_NAMES}\b\s+(\d{{1,2}})\s*[–—−-]\s*\b{MONTH_NAMES}\b\s+(\d{{1,2}})", text, re.IGNORECASE)
        if m:
            start_month_name = m.group(1)
            start_day = int(m.group(2))
            end_month_name = m.group(3)
            end_day = int(m.group(4))
            start_month = YearsParseOrchestrator.month_name_to_number(start_month_name)
            end_month = YearsParseOrchestrator.month_name_to_number(end_month_name)
            if start_month is not None and end_month is not None:
                span = Span(
                    start_year=page_year,
                    start_month=start_month,
                    start_day=start_day,
                    end_year=page_year,
                    end_month=end_month,
                    end_day=end_day,
                    start_year_is_bc=page_bc,
                    end_year_is_bc=page_bc,
                    precision=SpanPrecision.EXACT,
                    match_type="Day range across months within page span. EG: Month DD - Month DD"
                )
                return YearsParseOrchestrator._return_none_if_invalid(span)
        return None
