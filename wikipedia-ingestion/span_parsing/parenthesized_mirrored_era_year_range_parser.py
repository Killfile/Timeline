"""Parser for parenthesized year ranges where both sides include era markers (mirrored BC/AD).

Example: "Xiongnu(Mongolia, 220 BC – AD 200)"

This parser accepts an optional location at the start of the parentheses
followed by a year range where both sides include explicit era markers.
It specifically looks for one side in BC/BCE and the other in AD/CE and
returns a span that crosses the era boundary.
"""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class ParenthesizedMirroredEraYearRangeParser(SpanParserStrategy):
    """Parses parenthesized year ranges where each endpoint includes an era marker.

    Accepts forms like:
      - (Mongolia, 220 BC – AD 200)
      - (220 BC – AD 200)
      - (BC 220 – 200 AD)  # era before or after year is accepted
    """

    _ERA = r"BC|BCE|AD|CE"

    _RE = re.compile(
        rf"\(\s*(?:(?P<location>.+)\s*,\s*)?"
        rf"(?P<s_era1>{_ERA})?\s*(?P<s_y>\d{{1,4}})\s*(?P<s_era2>{_ERA})?\s*[–—−-]\s*"
        rf"(?P<e_era1>{_ERA})?\s*(?P<e_y>\d{{1,4}})\s*(?P<e_era2>{_ERA})?\s*\)\s*$",
        flags=re.IGNORECASE,
    )

    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        m = self._RE.search(text)
        if not m:
            return None

        location = (m.group("location") or "").strip()
        s_y = int(m.group("s_y"))
        e_y = int(m.group("e_y"))

        # Era markers may appear before or after the year in the text; pick whichever matched
        s_era = (m.group("s_era1") or m.group("s_era2") or "").upper()
        e_era = (m.group("e_era1") or m.group("e_era2") or "").upper()

        bc_markers = {"BC", "BCE"}
        ad_markers = {"AD", "CE"}

        # Require both endpoints to include an era and for them to be mirrored (one BC, one AD)
        if not s_era or not e_era:
            return None

        s_is_bc = s_era in bc_markers
        e_is_bc = e_era in bc_markers
        s_is_ad = s_era in ad_markers
        e_is_ad = e_era in ad_markers

        # Require that eras are mirrored (one BC and one AD)
        if not ((s_is_bc and e_is_ad) or (s_is_ad and e_is_bc)):
            return None

        # Determine start/end BC flags
        start_year_is_bc = s_is_bc
        end_year_is_bc = e_is_bc

        span = Span(
            start_year=s_y,
            start_month=1,
            start_day=1,
            end_year=e_y,
            end_month=12,
            end_day=31,
            start_year_is_bc=start_year_is_bc,
            end_year_is_bc=end_year_is_bc,
            precision=SpanPrecision.YEAR_ONLY,
            match_type=(
                f"Mirrored era range: {s_y} {s_era} - {e_era} {e_y}"
                + (f" (location: {location})" if location else "")
            ),
        )

        return self._return_none_if_invalid(span)
