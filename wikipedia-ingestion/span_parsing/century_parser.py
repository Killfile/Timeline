"""Parser for century formats like '5th century BCE' or '19th century'."""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class CenturyParser(SpanParserStrategy):
    """Parses century formats at the start of text.
    
    Matches patterns like:
    - 5th century BCE
    - 1st century AD
    - 21st century
    - 19th century
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse century at the start of text.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Match century patterns at the start of text
        # Pattern: century number (1-2 digits) + ordinal suffix + "century" + optional era marker
        m = re.match(
            r"^\s*(\d{1,2})(st|nd|rd|th)\s+century\s*(BCE|BC|AD|CE)?\b",
            text,
            flags=re.IGNORECASE
        )
        
        if not m:
            return None
        
        century_num = int(m.group(1))
        era_marker = m.group(3)
        
        # Determine BC/AD based on explicit marker or page context
        if era_marker:
            is_bc = era_marker.upper() in ("BC", "BCE")
        else:
            # For centuries 1-20 assume AD/CE, for 21+ assume current era (CE)
            # If page context is BC, respect that
            if page_bc:
                is_bc = True
            else:
                is_bc = False
        
        # Calculate year range for century
        # Century N BCE: start = -(N*100), end = -((N-1)*100 + 1)
        # Century N AD/CE: start = (N-1)*100 + 1, end = N*100
        if is_bc:
            # BC centuries go backwards: 5th century BCE = 500-401 BCE
            start_year = century_num * 100
            end_year = (century_num - 1) * 100 + 1
        else:
            # AD centuries go forwards: 5th century AD = 401-500 AD
            start_year = (century_num - 1) * 100 + 1
            end_year = century_num * 100
        
        span = Span(
            start_year=start_year,
            end_year=end_year,
            start_month=1,
            start_day=1,
            end_month=12,
            end_day=31,
            start_year_is_bc=is_bc,
            end_year_is_bc=is_bc,
            precision=SpanPrecision.APPROXIMATE,
            match_type=f"{century_num}{m.group(2)} century"
        )
        
        return self._return_none_if_invalid(span)
