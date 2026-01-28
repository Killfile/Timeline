"""Parser for tilde circa formats like '~1450' or '~450 BCE'."""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class TildeCircaYearParser(SpanParserStrategy):
    """Parses tilde circa year formats at the start of text.
    
    Matches patterns like:
    - ~1450
    - ~450 BCE
    - ~9300 BCE
    - ~ 1200 (with space after tilde)
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse tilde circa year at the start of text.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Match tilde patterns at the start of text
        # Pattern: tilde, optional space, year (3-4 digits), optional era marker
        m = re.match(
            r"^\s*~\s*(\d{3,4})\s*(BC|BCE|AD|CE)?\b",
            text,
            flags=re.IGNORECASE
        )
        
        if not m:
            return None
        
        year = int(m.group(1))
        era_marker = m.group(2)
        
        # Determine BC/AD based on explicit marker or page context
        if era_marker:
            is_bc = era_marker.upper() in ("BC", "BCE")
        else:
            is_bc = page_bc
        
        span = Span(
            start_year=year,
            end_year=year,
            start_month=1,
            start_day=1,
            end_month=12,
            end_day=31,
            start_year_is_bc=is_bc,
            end_year_is_bc=is_bc,
            precision=SpanPrecision.CIRCA,
            match_type="Tilde circa year (~####)"
        )
        
        return self._return_none_if_invalid(span)
