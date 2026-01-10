"""Parser for parenthesized century or range of centuries with a location.

Examples:
- "Protestant Reformation (Europe, 16th century)"
- "Classicism (Europe, 16th – 18th centuries)"
"""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class ParenthesizedCenturyWithLocationParser(SpanParserStrategy):
    """Parses parenthesized single century or century ranges with a location.

    Supports both single centuries ("16th century") and ranges
    ("16th – 18th centuries") with optional era markers (BC/BCE/AD/CE).
    """

    # Range: location, 16th - 18th centuries [BC]
    _RANGE_RE = re.compile(
        r"\(\s*(?P<location>.+)\s*,\s*(?P<s_ord>\d{1,2})(?:st|nd|rd|th)?\s*(?P<s_era>BC|BCE|AD|CE)?\s*[–—−-]\s*(?P<e_ord>\d{1,2})(?:st|nd|rd|th)?\s*(?:centuries|century)?\s*(?P<e_era>BC|BCE|AD|CE)?\s*\)\s*$",
        flags=re.IGNORECASE,
    )

    # Single: location, 16th century [BC]
    _SINGLE_RE = re.compile(
        r"\(\s*(?P<location>.+)\s*,\s*(?P<ord>\d{1,2})(?:st|nd|rd|th)\s+century\s*(?P<era>BC|BCE|AD|CE)?\s*\)\s*$",
        flags=re.IGNORECASE,
    )

    def _century_to_years(self, n: int, is_bc: bool) -> tuple[int, int]:
        """Convert century ordinal to start/end years inclusive.

        For AD: 16th -> 1501-1600
        For BC: 16th BC -> 1600-1501
        """
        if is_bc:
            start = n * 100
            end = (n - 1) * 100 + 1
        else:
            start = (n - 1) * 100 + 1
            end = n * 100
        return start, end

    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        # Try range first
        m = self._RANGE_RE.search(text)
        if m:
            location = m.group("location").strip()
            s_ord = int(m.group("s_ord"))
            e_ord = int(m.group("e_ord"))
            s_era = (m.group("s_era") or "").upper()
            e_era = (m.group("e_era") or "").upper()

            bc_markers = ["BC", "BCE"]
            ad_markers = ["AD", "CE"]

            is_bc = any(marker in s_era for marker in bc_markers) or any(marker in e_era for marker in bc_markers)
            is_ad = any(marker in s_era for marker in ad_markers) or any(marker in e_era for marker in ad_markers)
            if is_bc and is_ad:
                return None

            if not is_bc and not is_ad:
                is_bc = page_bc

            # Compute start/end centuries depending on era
            if is_bc:
                start_ord = max(s_ord, e_ord)
                end_ord = min(s_ord, e_ord)
            else:
                start_ord = min(s_ord, e_ord)
                end_ord = max(s_ord, e_ord)

            start_year, _ = self._century_to_years(start_ord, is_bc)
            _, end_year = self._century_to_years(end_ord, is_bc)

            span = Span(
                start_year=start_year,
                start_month=1,
                start_day=1,
                end_year=end_year,
                end_month=12,
                end_day=31,
                start_year_is_bc=is_bc,
                end_year_is_bc=is_bc,
                precision=SpanPrecision.YEAR_ONLY,
                match_type=f"Century range: {s_ord}th - {e_ord}th centuries (location: {location})",
            )
            return self._return_none_if_invalid(span)

        # Try single
        m2 = self._SINGLE_RE.search(text)
        if m2:
            location = m2.group("location").strip()
            ordn = int(m2.group("ord"))
            era = (m2.group("era") or "").upper()

            bc_markers = ["BC", "BCE"]
            ad_markers = ["AD", "CE"]

            is_bc = False
            is_ad = False
            if era:
                is_bc = era in bc_markers
                is_ad = era in ad_markers
            if is_bc and is_ad:
                return None
            if not is_bc and not is_ad:
                is_bc = page_bc

            start_year, end_year = self._century_to_years(ordn, is_bc)

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
                match_type=f"Century: {ordn}th century (location: {location})",
            )
            return self._return_none_if_invalid(span)

        return None
