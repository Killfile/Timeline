"""Parser for day ranges within a single month."""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span


class SingleMonthDayRangeParser(SpanParserStrategy):
    """Parses date ranges within the same month.
    
    Example: September 25–28
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse day range within a single month.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Lazy import to avoid circular dependency
        from span_parsing.span_parser import SpanParser
        
        # EG: September 25–28
        m = re.search(r"(?<!\d)(\w+)\s+(\d{1,2})\s*[–—−-]\s*(\d{1,2})", text)
        if m:
            month_name = m.group(1)
            day = int(m.group(2))
            month = SpanParser.month_name_to_number(month_name)
            if month is not None:
                span = Span(
                    start_year=page_year,
                    start_month=month,
                    start_day=day,
                    end_year=page_year,
                    end_month=month,
                    end_day=int(m.group(3)),
                    is_bc=page_bc,
                    precision="day",
                    match_type="Day range within page span (same month). EG: Month DD-DD"
                )
                return SpanParser._return_none_if_invalid(span)
        return None
