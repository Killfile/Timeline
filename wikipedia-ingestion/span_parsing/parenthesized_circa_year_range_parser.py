"""Parser for parenthesized circa year ranges at the end of a string without a location.

Example: "Bronze Age (c. 3000 BC – c. 1050 BC)"
"""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class ParenthesizedCircaYearRangeParser(SpanParserStrategy):
    """Parses parenthesized circa year ranges without a location at the end.

    This parser accepts optional circa markers (c., ca., circa) on either side
    and optional era markers (BC/BCE/AD/CE) after either year. It infers era
    from the page context when no explicit markers are present and rejects
    mixed-era ranges.
    """

    _CIRCA_RE = r"(?:c\s*\.|ca\s*\.|circa|≈)\s*"

    _RE = re.compile(
        rf"\(\s*(?P<s_circa>{_CIRCA_RE})?(?P<s_y>\d{{1,4}})\s*(?P<s_era>BC|BCE|AD|CE)?\s*[–—−-]\s*(?P<e_circa>{_CIRCA_RE})?(?P<e_y>\d{{1,4}})\s*(?P<e_era>BC|BCE|AD|CE)?\s*\)\s*$",
        flags=re.IGNORECASE,
    )

    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        m = self._RE.search(text)
        if not m:
            return None

        s_circa_raw = m.group("s_circa") or ""
        e_circa_raw = m.group("e_circa") or ""
        s_y = int(m.group("s_y"))
        e_y = int(m.group("e_y"))
        s_era = (m.group("s_era") or "").upper()
        e_era = (m.group("e_era") or "").upper()

        # Determine era markers and propagate if necessary
        bc_markers = ["BC", "BCE"]
        ad_markers = ["AD", "CE"]

        start_year_is_bc: bool
        end_year_is_bc: bool

        start_year_is_bc = s_era in bc_markers
        end_year_is_bc = e_era in bc_markers

        if not start_year_is_bc and not end_year_is_bc and page_bc:
            start_year_is_bc = end_year_is_bc = True

        if end_year_is_bc and not start_year_is_bc and s_era == "":
            start_year_is_bc = end_year_is_bc

        # Determine if either side is circa
        s_circa = bool(s_circa_raw.strip())
        e_circa = bool(e_circa_raw.strip())

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
                f"Circa range: {'c. ' if s_circa else ''}{s_y} - {'c. ' if e_circa else ''}{e_y}"
            ),
        )

        return self._return_none_if_invalid(span)
