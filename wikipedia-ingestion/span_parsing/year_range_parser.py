"""Parser for year ranges."""

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
        
        text = self.normalize_dashs(text)
        m = re.search(
            r"(?<!\d)(\d{1,4})\s*(BC|BCE|AD|CE)?\s*-\s*(\d{1,4})\s*(BC|BCE|AD|CE)?",
            text,
            flags=re.IGNORECASE,
        )
        if m:
            s_y = int(m.group(1))
            s_era = (m.group(2) or "").upper()
            e_y = int(m.group(3))
            e_era = (m.group(4) or "").upper()

            is_bc = ("BC" in s_era) or ("BC" in e_era) or ("BCE" in s_era) or ("BCE" in e_era)
            is_ad = ("AD" in s_era) or ("AD" in e_era) or ("BCE" not in s_era and "CE" in s_era) or ("BCE" not in e_era and "CE" in e_era)
            if is_bc and is_ad:
                return None

            if not is_bc and not is_ad:
                is_bc = page_bc


            start_year = s_y
            end_year = e_y

            span = Span(
                start_year=start_year,
                start_month=1,
                start_day=1,
                end_year=end_year,
                end_month=12,
                end_day=31,
                is_bc=bool(is_bc and not is_ad),
                precision=SpanPrecision.YEAR_ONLY,
                match_type="Range. EG: ### BC - ####"
            )
            return self._return_none_if_invalid(span)

        return None
    
    def compute_weight_days(self, span: Span) -> int | None:
        base_weight = super().compute_weight_days(span)
        if base_weight is None:
            return None
        return int(base_weight * span.precision)
