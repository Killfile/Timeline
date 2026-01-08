"""Parser for year ranges enclosed in parentheses at the end of a string.

Example: "Shang dynasty (1600–1046 BC)"
"""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class ParenthesizedYearRangeParser(SpanParserStrategy):
    """Parses year ranges that appear inside parentheses at the end of a string.

    This is a convenience parser that extracts the parenthesized content at the
    end of a string and delegates the actual range parsing to
    `YearRangeParser` so that era propagation and validation logic are reused.
    """

    _RE = re.compile(r"\(\s*(?<![\d#])(\d{1,4})\s*(BC|BCE|AD|CE)?\s*[–—−-]\s*(\d{1,4})\s*(BC|BCE|AD|CE)?\s*\)\s*$", flags=re.IGNORECASE)

    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse a parenthesized year range at the end of `text`.

        Args:
            text: The text to parse (full line)
            page_year: The year from the page context
            page_bc: Whether the page context is BC/BCE

        Returns:
            A Span if the parenthesized range is valid, otherwise None
        """
        # Lazy import to avoid circular dependency
        from span_parsing.year_range_parser import YearRangeParser

        m = self._RE.search(text)
        if not m:
            return None

        # Build a canonical inner string without parentheses so YearRangeParser
        # sees a clean range like "1600 - 1046 BC" and can apply its era
        # propagation and validation logic reliably.
        s_y = m.group(1)
        s_era = (m.group(2) or "").upper()
        e_y = m.group(3)
        e_era = (m.group(4) or "").upper()

        if s_era and e_era:
            inner = f"{s_y} {s_era} - {e_y} {e_era}"
        elif e_era:
            inner = f"{s_y} - {e_y} {e_era}"
        elif s_era:
            inner = f"{s_y} {s_era} - {e_y}"
        else:
            inner = f"{s_y} - {e_y}"

        return YearRangeParser().parse(inner, page_year, page_bc)
