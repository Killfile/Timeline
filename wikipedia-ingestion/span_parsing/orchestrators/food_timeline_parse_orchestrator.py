"""Food Timeline parse orchestrator combining all date parsing strategies."""

from typing import List
from span_parsing.orchestrators.parse_orchestrator import ParseOrchestrator
from span_parsing.factory import SpanParsers


class FoodTimelineParseOrchestrator(ParseOrchestrator):
    """Parse orchestrator optimized for the Timeline of Food Wikipedia article.
    
    Combines standard year parsers with new century/years-ago parsers in
    optimal priority order for food history date formats.
    
    Priority order (highest to lowest):
    1. Exact dates (year with era, year only)
    2. Circa dates (circa year, tilde circa)
    3. Year ranges
    4. Century formats (ranges, modifiers, plain centuries)
    5. Years ago (prehistoric)
    6. Decades
    7. Fallback
    """
    
    def get_parser_steps(self) -> List[SpanParsers]:
        """Return the ordered list of parser strategies to try.
        
        Returns:
            List of SpanParsers in priority order for food history dates
        """
        return [
            # Exact dates (highest priority)
            SpanParsers.YEAR_WITH_EXPLICIT_ERA,
            SpanParsers.YEAR_ONLY,
            
            # Circa dates
            SpanParsers.CIRCA_YEAR,
            SpanParsers.TILDE_CIRCA_YEAR,  # NEW: ~1450
            SpanParsers.PARENTHESIZED_CIRCA_YEAR_RANGE,
            
            # Year ranges
            SpanParsers.YEAR_RANGE,
            SpanParsers.PARENTHESIZED_YEAR_RANGE,
            SpanParsers.PARENTHESIZED_SHORT_YEAR_RANGE,
            
            # Century formats (NEW)
            SpanParsers.CENTURY_RANGE,  # NEW: 11th-14th centuries
            SpanParsers.CENTURY_WITH_MODIFIER,  # NEW: Early 1700s, Late 16th century
            SpanParsers.CENTURY,  # NEW: 5th century BCE
            
            # Years ago (NEW - for prehistoric dates)
            SpanParsers.YEARS_AGO,  # NEW: 250,000 years ago
            
            # Decades
            SpanParsers.PARENTHESIZED_DECADE_RANGE,
            SpanParsers.PARENTHESIZED_DECADE,
            
            # Parenthesized formats
            SpanParsers.PARENTHESIZED_YEAR,
            
            # Fallback (lowest priority)
            SpanParsers.FALLBACK,
        ]
