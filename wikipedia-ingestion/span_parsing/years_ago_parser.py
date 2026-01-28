"""Parser for 'years ago' formats like '250,000 years ago'."""

import re
from datetime import datetime
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class YearsAgoParser(SpanParserStrategy):
    """Parses 'years ago' formats at the start of text.
    
    Matches patterns like:
    - 250,000 years ago
    - 5-2 million years ago
    - 170,000 years ago
    - 2.5 million years ago
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse 'years ago' at the start of text.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context (unused)
            page_bc: Whether the page context is BC/BCE (unused)
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Use page_year as the anchor when provided (otherwise fallback to current year)
        anchor_year = page_year if page_year and page_year > 0 else datetime.utcnow().year

        # Match range pattern: "5-2 million years ago"
        m_range = re.match(
            r"^\s*([\d,\.]+)\s*-\s*([\d,\.]+)\s+(million|thousand)?\s*years?\s+ago\b",
            text,
            flags=re.IGNORECASE
        )
        
        if m_range:
            start_num_str = m_range.group(1).replace(',', '')
            end_num_str = m_range.group(2).replace(',', '')
            multiplier_str = m_range.group(3)
            
            try:
                start_num = float(start_num_str)
                end_num = float(end_num_str)
            except ValueError:
                return None
            
            # Apply multiplier
            if multiplier_str and multiplier_str.lower() == 'million':
                start_years_ago = int(start_num * 1_000_000)
                end_years_ago = int(end_num * 1_000_000)
            elif multiplier_str and multiplier_str.lower() == 'thousand':
                start_years_ago = int(start_num * 1_000)
                end_years_ago = int(end_num * 1_000)
            else:
                start_years_ago = int(start_num)
                end_years_ago = int(end_num)
            
            # Convert to BCE (anchor to provided year)
            # Larger number of years ago = earlier date (larger BC year)
            start_year = anchor_year - start_years_ago
            end_year = anchor_year - end_years_ago
            
            span = Span(
                start_year=abs(start_year),
                end_year=abs(end_year),
                start_month=1,
                start_day=1,
                end_month=12,
                end_day=31,
                start_year_is_bc=True,  # Always BC for prehistoric dates
                end_year_is_bc=True,
                precision=SpanPrecision.CIRCA,  # Inherently approximate
                match_type=f"{start_num_str}-{end_num_str} {multiplier_str or ''} years ago"
            )
            
            return self._return_none_if_invalid(span)
        
        # Match single value pattern: "250,000 years ago"
        m_single = re.match(
            r"^\s*([\d,\.]+)\s+(million|thousand)?\s*years?\s+ago\b",
            text,
            flags=re.IGNORECASE
        )
        
        if m_single:
            num_str = m_single.group(1).replace(',', '')
            multiplier_str = m_single.group(2)
            
            try:
                num = float(num_str)
            except ValueError:
                return None
            
            # Apply multiplier
            if multiplier_str and multiplier_str.lower() == 'million':
                years_ago = int(num * 1_000_000)
            elif multiplier_str and multiplier_str.lower() == 'thousand':
                years_ago = int(num * 1_000)
            else:
                years_ago = int(num)
            
            # Convert to BCE (anchor to provided year)
            year = anchor_year - years_ago
            
            span = Span(
                start_year=abs(year),
                end_year=abs(year),
                start_month=1,
                start_day=1,
                end_month=12,
                end_day=31,
                start_year_is_bc=True,  # Always BC for prehistoric dates
                end_year_is_bc=True,
                precision=SpanPrecision.CIRCA,  # Inherently approximate
                match_type=f"{num_str} {multiplier_str or ''} years ago"
            )
            
            return self._return_none_if_invalid(span)
        
        return None
