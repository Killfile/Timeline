"""Parser for standalone year values."""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span


class YearOnlyParser(SpanParserStrategy):
    """Parses standalone year values without era markers.
    
    Example: 490
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse standalone year.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Lazy import to avoid circular dependency
        from span_parsing.span_parser import SpanParser
        
        # Parse year but only at the start of the string
        m = re.search(r"^\s*(\d{3,4})\b", text)
        if m:
            y = int(m.group(1))
            bc = page_bc
            span = Span(
                start_year=y,
                end_year=y,
                start_month=1,
                start_day=1,
                end_month=12,
                end_day=31,
                is_bc=bc,
                precision="year",
                match_type="3-4 digit year only. EG: ####"
            )
            return SpanParser._return_none_if_invalid(span)
        return None
