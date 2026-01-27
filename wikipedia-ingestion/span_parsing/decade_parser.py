"""Parser for decade notations like '1990s' or '1800s'."""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class DecadeParser(SpanParserStrategy):
    """Parses decade notations.
    
    Matches patterns like:
    - 1990s
    - 1800s
    - 2000s
    - 1950s
    
    Converts to year ranges:
    - 1990s → 1990-1999
    - 1800s → 1800-1809
    - 2000s → 2000-2009
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse decade notation at the start of text.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Match decade patterns: 4-digit year ending in 0 followed by 's'
        # Must be at the start of text and not part of a larger word
        m = re.match(
            r"^\s*(\d{3}0)s\b",
            text,
            flags=re.IGNORECASE
        )
        
        if not m:
            return None
        
        decade_start = int(m.group(1))
        decade_end = decade_start + 9
        
        # Decades are always AD/CE (not BC)
        # Unless explicitly in a BC context page (which would be very rare)
        # Decades should not inherit page-level BC context; keep AD/CE by default
        is_bc = False
        
        span = Span(
            start_year=decade_start,
            end_year=decade_end,
            start_month=1,
            start_day=1,
            end_month=12,
            end_day=31,
            start_year_is_bc=is_bc,
            end_year_is_bc=is_bc,
            precision=SpanPrecision.YEAR_ONLY,
            match_type="Decade notation (e.g., 1990s)"
        )
        
        return self._return_none_if_invalid(span)
