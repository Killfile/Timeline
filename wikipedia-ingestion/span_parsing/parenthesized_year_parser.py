"""Parser for a single year enclosed in parentheses at the end of a string.

Example: "Hashemite Arab Federation(1958)"
"""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class ParenthesizedYearParser(SpanParserStrategy):
    """Parses a single year (optionally with circa or era marker) inside
    parentheses at the end of a string.

    Matches patterns like:
    - (1958)
    - (490 BC)
    - (c. 1600)
    - (ca. 1600 BC)
    """

    _CIRCA_RE = r"(?:c\s*\.|ca\s*\.|circa)\s*"

    _RE = re.compile(
        rf"\(\s*(?P<circa>{_CIRCA_RE})?(?P<y>\d{{1,4}})\s*(?P<era>BC|BCE|AD|CE)?\s*\)\s*$",
        flags=re.IGNORECASE,
    )

    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        m = self._RE.search(text)
        if not m:
            return None

        circa_raw = m.group("circa") or ""
        y = int(m.group("y"))
        era = (m.group("era") or "").upper()

        # Determine era marker, fall back to page context when missing
        bc_markers = ["BC", "BCE"]
        ad_markers = ["AD", "CE"]

        is_bc = any(marker in era for marker in bc_markers)
        is_ad = any(marker in era for marker in ad_markers) or (("BCE" not in era) and ("CE" in era))

        # If both BC and AD are marked (shouldn't happen for single year), reject
        if is_bc and is_ad:
            return None

        if not is_bc and not is_ad:
            is_bc = page_bc

        is_circa = bool(circa_raw.strip())

        span = Span(
            start_year=y,
            start_month=1,
            start_day=1,
            end_year=y,
            end_month=12,
            end_day=31,
            start_year_is_bc=is_bc,
            end_year_is_bc=is_bc,
            precision=(SpanPrecision.CIRCA if is_circa else SpanPrecision.YEAR_ONLY),
            match_type=(f"Parenthesized year: {'c. ' if is_circa else ''}{y}"),
        )

        return self._return_none_if_invalid(span)
