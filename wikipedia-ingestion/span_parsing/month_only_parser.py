"""Parser for month-only dates."""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span


class MonthOnlyParser(SpanParserStrategy):
    """Parses dates with only month specified.
    
    Example: September
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse month-only date.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Lazy import to avoid circular dependency
        from span_parsing.span_parser import SpanParser
        
        # EG: September
        m = re.search(r"(?<!\d)(\w+)(?!\d)", text)
        if m:
            month_name = m.group(1)
            month = SpanParser.month_name_to_number(month_name)
            if month is not None:
                # Calculate actual days in month (simplified - doesn't handle leap years)
                days_in_month = {
                    1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
                }
                span = Span(
                    start_year=page_year,
                    start_month=month,
                    start_day=1,
                    end_year=page_year,
                    end_month=month,
                    end_day=days_in_month.get(month, 31),
                    is_bc=page_bc,
                    precision="month",
                    match_type="Month only within page span. EG: Month"
                )
                return SpanParser._return_none_if_invalid(span)
        return None
