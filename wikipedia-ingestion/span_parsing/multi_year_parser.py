"""Parser for date ranges spanning multiple years with explicit months and days."""

from datetime import date
import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class MultiYearMonthAndDayRangeParser(SpanParserStrategy):
    """Parses date ranges that span multiple years with explicit month and day.
    
    Example: September 28, 2020 – October 2, 2021
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse multi-year date range with months and days.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Lazy import to avoid circular dependency
        from span_parsing.orchestrators.years_parse_orchestrator import YearsParseOrchestrator
        
        # EG: September 28, 2020 – October 2, 2021
        # Note: When explicit years are provided, use those to determine BC/AD status
        m = re.search(
            r"^\s*(?<!\d)(\w+)\s+(\d{1,2}),\s*(\d{1,4})\s*[–—−-]\s*(\w+)\s+(\d{1,2}),\s*(\d{1,4})",
            text
        )
        if m:
            start_month_name = m.group(1)
            start_day = int(m.group(2))
            start_year = int(m.group(3))
            end_month_name = m.group(4)
            end_day = int(m.group(5))
            end_year = int(m.group(6))
            start_month = SpanParserStrategy.month_name_to_number(start_month_name)
            end_month = SpanParserStrategy.month_name_to_number(end_month_name)
            if start_month is not None and end_month is not None:
                # Explicit year in text typically means AD unless page context is BC
                span = Span(
                    start_year=start_year,
                    start_month=start_month,
                    start_day=start_day,
                    end_year=end_year,
                    end_month=end_month,
                    end_day=end_day,
                    start_year_is_bc=page_bc,
                    end_year_is_bc=page_bc,
                    precision=SpanPrecision.EXACT,
                    match_type="Day range across years within page span. EG: Month DD, YYYY - Month DD, YYYY"
                )
                return YearsParseOrchestrator._return_none_if_invalid(span)
        return None
    
    def compute_weight_days(self, span: Span) -> int | None:
        """Compute weight for multi-year spans.
        
        Uses the base class implementation which handles BC years correctly.
        """
        return super().compute_weight_days(span)
