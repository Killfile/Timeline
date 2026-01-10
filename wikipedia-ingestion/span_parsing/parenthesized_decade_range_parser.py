"""Parser for parenthesized decade ranges at the end of a string.

Example: "Jeffersonian democracy(1790s–1820s)" which should map to
1790 - 1829.
"""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class ParenthesizedDecadeRangeParser(SpanParserStrategy):
    """Parse ranges composed of two decade expressions in parentheses.

    Supports an optional location prefix inside the parentheses and optional
    era markers (BC/BCE/AD/CE) after either decade. When era markers are
    missing on both sides, the parser falls back to page context.
    """

    _ERA = r"BC|BCE|AD|CE"

    _RE = re.compile(
        rf"\(\s*(?:(?P<location>.+?)\s*,\s*)?"
        rf"(?P<s_decade>\d{{1,3}}0)s\s*(?P<s_era>{_ERA})?\s*[–—−-]\s*"
        rf"(?P<e_decade>\d{{1,3}}0)s\s*(?P<e_era>{_ERA})?\s*\)\s*$",
        flags=re.IGNORECASE,
    )

    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        m = self._RE.search(text)
        if not m:
            return None

        location = (m.group("location") or "").strip()
        s_decade = int(m.group("s_decade"))
        e_decade = int(m.group("e_decade"))
        s_era = (m.group("s_era") or "").upper()
        e_era = (m.group("e_era") or "").upper()

        bc_markers = {"BC", "BCE"}
        ad_markers = {"AD", "CE"}

        # Determine era markers and propagate if necessary
        is_bc = any(marker in s_era for marker in bc_markers) or any(marker in e_era for marker in bc_markers)
        is_ad = any(marker in s_era for marker in ad_markers) or any(marker in e_era for marker in ad_markers)

        # Reject mixed-era explicit markers (mirrored-era parser should be used for BC/AD crossings)
        if is_bc and is_ad:
            return None

        if not is_bc and not is_ad:
            # No explicit markers - use page context
            start_is_bc = page_bc
            end_is_bc = page_bc
        else:
            # Propagate single-side markers
            if s_era and not e_era:
                start_is_bc = s_era in bc_markers
                end_is_bc = start_is_bc
            elif e_era and not s_era:
                end_is_bc = e_era in bc_markers
                start_is_bc = end_is_bc
            else:
                start_is_bc = s_era in bc_markers
                end_is_bc = e_era in bc_markers

        # Compute numeric years
        if start_is_bc:
            # Start of BC decade is decade+9, end of BC decade is decade
            start_year = s_decade + 9
        else:
            start_year = s_decade

        if end_is_bc:
            end_year = e_decade
        else:
            end_year = e_decade + 9

        span = Span(
            start_year=start_year,
            start_month=1,
            start_day=1,
            end_year=end_year,
            end_month=12,
            end_day=31,
            start_year_is_bc=start_is_bc,
            end_year_is_bc=end_is_bc,
            precision=SpanPrecision.APPROXIMATE,
            match_type=(
                f"Decade range: {s_decade}s - {e_decade}s"
                + (f" (location: {location})" if location else "")
            ),
        )

        return self._return_none_if_invalid(span)
