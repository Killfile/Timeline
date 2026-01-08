"""Parser for parenthesized year ranges at the end of a string with a location specifier.

Example: "British Interregnum (British Isles, 1649–1660)"
"""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class ParenthesizedYearRangeWithLocationParser(SpanParserStrategy):
    """Parses parenthesized year ranges that include a location before the years.

    The location can include commas (e.g., "City, Region, 1900–1910") and is
    preserved on the returned Span.match_type so downstream consumers can see
    the geographic context.
    """

    _RE = re.compile(
        r"\(\s*(?P<location>.+)\s*,\s*(?<![\d#])(?P<s_y>\d{1,4})\s*(?P<s_era>BC|BCE|AD|CE)?\s*[–—−-]\s*(?P<e_y>\d{1,4})\s*(?P<e_era>BC|BCE|AD|CE)?\s*\)\s*$",
        flags=re.IGNORECASE,
    )

    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse a parenthesized year range with a location at the end of the text.

        Args:
            text: The text to parse (full line)
            page_year: The year from the page context
            page_bc: Whether the page context is BC/BCE

        Returns:
            A Span if the parenthesized location+range is valid, otherwise None
        """
        # Lazy import to avoid circular dependency
        from span_parsing.year_range_parser import YearRangeParser

        m = self._RE.search(text)
        if not m:
            return None

        location = m.group("location").strip()
        s_y = m.group("s_y")
        s_era = (m.group("s_era") or "").upper()
        e_y = m.group("e_y")
        e_era = (m.group("e_era") or "").upper()

        # Build canonical inner string without the location so YearRangeParser
        # can process it the same way as other inputs.
        if s_era and e_era:
            inner = f"{s_y} {s_era} - {e_y} {e_era}"
        elif e_era:
            inner = f"{s_y} - {e_y} {e_era}"
        elif s_era:
            inner = f"{s_y} {s_era} - {e_y}"
        else:
            inner = f"{s_y} - {e_y}"

        span = YearRangeParser().parse(inner, page_year, page_bc)
        if span is None:
            return None

        # Annotate the match_type with the location for clarity
        span.match_type = f"{span.match_type} (location: {location})"
        return span
