"""Food Timeline parse orchestrator combining all date parsing strategies."""

from typing import List
from span_parsing.orchestrators.parse_orchestrator import ParseOrchestrator
from span_parsing.factory import SpanParsers


class FoodTimelineParseOrchestrator(ParseOrchestrator):
    """Parse orchestrator optimized for the Timeline of Food Wikipedia article.
    
    Combines standard year parsers with new century/years-ago parsers in
    optimal priority order for food history date formats.
    
    Priority order (highest to lowest):
    1. Exact dates (year with era)
    2. Years-ago patterns (prehistoric) → must run before plain 3-4 digit year detection
    3. Exact years without era
    4. Circa dates (circa year, tilde circa)
    5. Year ranges
    6. Century formats (ranges, modifiers, plain centuries)
    7. Decades
    8. Fallback
    """
    
    def get_parser_steps(self) -> List[SpanParsers]:
        """Return the ordered list of parser strategies to try.
        
        Returns:
            List of SpanParsers in priority order for food history dates
        """
        return [
            # Exact dates (highest priority)
            SpanParsers.YEAR_WITH_EXPLICIT_ERA,

            # Year ranges MUST come before YEAR_ONLY to avoid matching just the first digit
            # E.g., "327–324 BCE" must match as a range, not parse "327" as a standalone year
            SpanParsers.YEAR_RANGE,
            SpanParsers.PARENTHESIZED_YEAR_RANGE,
            SpanParsers.PARENTHESIZED_SHORT_YEAR_RANGE,

            # Years-ago (run before YEAR_ONLY to avoid greedy 3-4 digit match on "250,000 years ago")
            SpanParsers.YEARS_AGO,

            # Exact years without era
            SpanParsers.YEAR_ONLY,
            
            # Circa dates
            SpanParsers.CIRCA_YEAR,
            SpanParsers.TILDE_CIRCA_YEAR,  # NEW: ~1450
            SpanParsers.PARENTHESIZED_CIRCA_YEAR_RANGE,
            
            # Century formats (NEW)
            SpanParsers.CENTURY_RANGE,  # NEW: 11th-14th centuries
            SpanParsers.CENTURY_WITH_MODIFIER,  # NEW: Early 1700s, Late 16th century
            SpanParsers.CENTURY,  # NEW: 5th century BCE
            
            # Decades (NEW)
            SpanParsers.DECADE,  # NEW: 1990s → 1990-1999
            SpanParsers.PARENTHESIZED_DECADE_RANGE,
            SpanParsers.PARENTHESIZED_DECADE,
            
            # Parenthesized formats
            SpanParsers.PARENTHESIZED_YEAR,
            
            # Fallback (lowest priority)
            SpanParsers.FALLBACK,
        ]
