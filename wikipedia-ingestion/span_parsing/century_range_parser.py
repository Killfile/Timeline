"""Parser for century range formats like '11th-14th centuries'."""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class CenturyRangeParser(SpanParserStrategy):
    """Parses century range formats at the start of text.
    
    Matches patterns like:
    - 11th-14th centuries
    - 5th-3rd centuries BCE
    - 15th–16th centuries (with en-dash)
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse century range at the start of text.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Normalize dashes first
        text = self.normalize_dashs(text)
        
        # Match century range patterns at the start of text
        # Pattern: start century + dash + end century + "centuries" + optional era marker
        m = re.match(
            r"^\s*(\d{1,2})(st|nd|rd|th)\s*-\s*(\d{1,2})(st|nd|rd|th)\s+centuries\s*(BCE|BC|AD|CE)?\b",
            text,
            flags=re.IGNORECASE
        )
        
        if not m:
            return None
        
        start_century = int(m.group(1))
        end_century = int(m.group(3))
        era_marker = m.group(5)
        
        # Determine BC/AD based on explicit marker or page context
        if era_marker:
            is_bc = era_marker.upper() in ("BC", "BCE")
        else:
            is_bc = page_bc
        
        # Calculate year ranges
        # For BC: centuries go backwards, so start_century should be larger
        # Example: 5th-3rd centuries BCE = 500 BCE to 201 BCE
        if is_bc:
            # Start from the beginning of the higher numbered century
            start_year = start_century * 100
            # End at the end of the lower numbered century
            end_year = (end_century - 1) * 100 + 1
        else:
            # AD centuries go forwards
            # 11th-14th centuries = 1001 to 1400
            start_year = (start_century - 1) * 100 + 1
            end_year = end_century * 100
        
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
            match_type=f"{start_century}{m.group(2)}-{end_century}{m.group(4)} centuries"
        )
        
        return self._return_none_if_invalid(span)
