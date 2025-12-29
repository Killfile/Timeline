"""Parser for circa (approximate) year values."""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span


class CircaYearParser(SpanParserStrategy):
    """Parses circa/approximate year values at the start of text.
    
    Matches patterns like:
    - c. 450 BC
    - ca. 1200
    - circa 500 BC
    - c.450 (no space)
    - c 500 BC (no period)
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse circa year at the start of text.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Match circa patterns at the start of text
        # Pattern: optional whitespace, circa marker (c./ca./circa), optional space/period, year (3-4 digits), optional BC/AD
        m = re.match(
            r"^\s*(c\s*\.|ca\s*\.|circa)\s*(\d{3,4})\s*(BC|BCE|AD|CE)?\b",
            text,
            flags=re.IGNORECASE
        )
        
        if not m:
            return None
        
        year = int(m.group(2))
        era_marker = m.group(3)
        
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
            is_bc=is_bc,
            precision="year",
            match_type="Circa year (c./ca./circa ####)"
        )
        
        return self._return_none_if_invalid(span)
