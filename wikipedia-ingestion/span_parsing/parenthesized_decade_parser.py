"""Parser for parenthesized decades at the end of a string.

Example: "Jet Age (1940s)" or "Movement (Region, 1940s)" or "Event (1940s BC)"
"""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class ParenthesizedDecadeParser(SpanParserStrategy):
    """Parses a single decade in parentheses at the end of a line.

    Supports an optional location before the decade separated by a comma,
    and an optional era marker (BC/BCE/AD/CE) after the decade.
    """

    _RE = re.compile(
        r"\(\s*(?:(?P<location>.+?)\s*,\s*)?(?P<decade>\d{3}0)s\s*(?P<era>BC|BCE|AD|CE)?\s*\)\s*$",
        flags=re.IGNORECASE,
    )

    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        m = self._RE.search(text)
        if not m:
            return None

        location = (m.group("location") or "").strip()
        decade = int(m.group("decade"))
        era = (m.group("era") or "").upper()

        bc_markers = ["BC", "BCE"]
        ad_markers = ["AD", "CE"]

        is_bc = any(marker in era for marker in bc_markers)
        is_ad = any(marker in era for marker in ad_markers)

        if is_bc and is_ad:
            return None

        if not is_bc and not is_ad:
            # No explicit era marker: infer from page context
            is_bc = page_bc

        if is_bc:
            # For BC decades the span goes from (decade+9) down to decade
            start_year = decade + 9
            end_year = decade
        else:
            start_year = decade
            end_year = decade + 9

        span = Span(
            start_year=start_year,
            start_month=1,
            start_day=1,
            end_year=end_year,
            end_month=12,
            end_day=31,
            start_year_is_bc=is_bc,
            end_year_is_bc=is_bc,
            precision=SpanPrecision.APPROXIMATE,
            match_type=(f"Decade: {decade}s" + (f" (location: {location})" if location else "")),
        )

        return self._return_none_if_invalid(span)
