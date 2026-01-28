"""Parser for year ranges."""

from __future__ import annotations

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class YearRangeParser(SpanParserStrategy):
    """Parses year range dates.
    
    Example: 490 BC - 479 BC
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse year range.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Lazy import to avoid circular dependency
        
        # Era markers for DRY principle
        ERA_MARKERS = ["BC", "BCE", "AD", "CE"]
        
        text = self.normalize_dashs(text)
        m = re.search(
            rf"^\s*(?<![\d#])(\d{{1,4}})\s*({'|'.join(ERA_MARKERS)})?\s*-\s*(\d{{1,4}})\s*({'|'.join(ERA_MARKERS)})?",
            text,
            flags=re.IGNORECASE,
        )
        if m:
            s_y = int(m.group(1))
            s_era = (m.group(2) or "").upper()
            e_y = int(m.group(3))
            e_era = (m.group(4) or "").upper()

            # Check for BC markers
            bc_markers = ["BC", "BCE"]
            ad_markers = ["AD", "CE"]

            start_year_is_bc: bool
            end_year_is_bc: bool

            start_year_is_bc = any(marker in s_era for marker in bc_markers)
            end_year_is_bc = any(marker in e_era for marker in bc_markers)
            start_year_is_ad = any(marker in s_era for marker in ad_markers)

            if not start_year_is_bc and not end_year_is_bc and page_bc:
                start_year_is_bc = end_year_is_bc = True

            # Formal logic: end_year_is_bc IMPLIES start_year_is_bc
            # If end is marked BC and start is not explicitly marked AD/CE, apply BC to start
            if end_year_is_bc and not start_year_is_bc and not start_year_is_ad:
                start_year_is_bc = True

            start_year = s_y
            end_year = e_y

            span = Span(
                start_year=start_year,
                start_month=1,
                start_day=1,
                end_year=end_year,
                end_month=12,
                end_day=31,
                start_year_is_bc=start_year_is_bc,
                end_year_is_bc=end_year_is_bc,
                precision=SpanPrecision.YEAR_ONLY,
                match_type="Range. EG: ### BC - ####"
            )
            return self._return_none_if_invalid(span)

        return None
    
    def compute_weight_days(self, span: Span) -> int | None:
        """Compute weight for year range spans.
        
        Returns the actual duration without scaling by precision.
        Precision represents uncertainty, not duration.
        """
        return super().compute_weight_days(span)
