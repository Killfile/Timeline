"""Parser for parenthesized circa year ranges at the end of a string with a location specifier.

Example: "The Renaissance (Europe, c. 1300 – c. 1601)"
"""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class ParenthesizedCircaYearRangeWithLocationParser(SpanParserStrategy):
    """Parses parenthesized circa year ranges with a location at the end.

    The parser recognizes circa markers (c., ca., circa) before either or both
    years and preserves the location string on the returned Span.match_type.
    """

    _CIRCA_RE = r"(?:c\s*\.|ca\s*\.|circa)\s*"

    _RE = re.compile(
        rf"\(\s*(?P<location>.+)\s*,\s*(?P<s_circa>{_CIRCA_RE})?(?P<s_y>\d{{1,4}})\s*(?P<s_era>BC|BCE|AD|CE)?\s*[–—−-]\s*(?P<e_circa>{_CIRCA_RE})?(?P<e_y>\d{{1,4}})\s*(?P<e_era>BC|BCE|AD|CE)?\s*\)\s*$",
        flags=re.IGNORECASE,
    )

    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse a parenthesized circa year range with location at the end.

        Args:
            text: Full line text to parse
            page_year: Page year context
            page_bc: Page BC/AD context

        Returns:
            A Span or None
        """
        m = self._RE.search(text)
        if not m:
            return None

        location = m.group("location").strip()
        s_circa_raw = m.group("s_circa") or ""
        e_circa_raw = m.group("e_circa") or ""
        s_y = int(m.group("s_y"))
        e_y = int(m.group("e_y"))
        s_era = (m.group("s_era") or "").upper()
        e_era = (m.group("e_era") or "").upper()

        # Determine era markers and propagate if necessary (reuse YearRangeParser logic)
        bc_markers = ["BC", "BCE"]
        ad_markers = ["AD", "CE"]

        is_bc = any(marker in s_era for marker in bc_markers) or any(marker in e_era for marker in bc_markers)
        is_ad = any(marker in s_era for marker in ad_markers) or any(marker in e_era for marker in ad_markers) or (
            ("BCE" not in s_era and "CE" in s_era) or ("BCE" not in e_era and "CE" in e_era)
        )
        if is_bc and is_ad:
            return None

        if not is_bc and not is_ad:
            start_year_is_bc = page_bc
            end_year_is_bc = page_bc
        else:
            if s_era and not e_era:
                start_year_is_bc = s_era in bc_markers
                end_year_is_bc = start_year_is_bc
            elif e_era and not s_era:
                end_year_is_bc = e_era in bc_markers
                start_year_is_bc = end_year_is_bc
            else:
                start_year_is_bc = s_era in bc_markers
                end_year_is_bc = e_era in bc_markers

        # Determine if either side is circa
        s_circa = bool(s_circa_raw.strip())
        e_circa = bool(e_circa_raw.strip())

        # Build the span with CIRCA precision
        span = Span(
            start_year=s_y,
            start_month=1,
            start_day=1,
            end_year=e_y,
            end_month=12,
            end_day=31,
            start_year_is_bc=start_year_is_bc,
            end_year_is_bc=end_year_is_bc,
            precision=SpanPrecision.CIRCA,
            match_type=(
                f"Circa range: {'c. ' if s_circa else ''}{s_y} - {'c. ' if e_circa else ''}{e_y} "
                f"(location: {location})"
            ),
        )

        return self._return_none_if_invalid(span)
