"""Parser for parenthesized year ranges where the end year is short (two digits).

Example: "Coalition Provisional Authority(2003-04)" -> 2003 - 2004
"""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class ParenthesizedShortYearRangeParser(SpanParserStrategy):
    """Parses parenthesized ranges where the start year is four digits and the end
    year is two digits, inferring the century.

    Behavior:
    - Matches: (YYYY-YY) with optional era markers (BC/BCE/AD/CE)
    - Infers end_year = (start_year // 100) * 100 + YY
    - If inferred end_year < start_year, we add 100 (roll into next century)
    - Propagates era markers if only one side has them; falls back to page context
    """

    _RE = re.compile(
        r"\(\s*(?P<s_y>\d{3,4})\s*(?P<s_era>BC|BCE|AD|CE)?\s*[–—−-]\s*(?P<e_yy>\d{2})\s*(?P<e_era>BC|BCE|AD|CE)?\s*\)\s*$",
        flags=re.IGNORECASE,
    )

    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        m = self._RE.search(text)
        if not m:
            return None

        s_y = int(m.group("s_y"))
        s_era = (m.group("s_era") or "").upper()
        e_yy = int(m.group("e_yy"))
        e_era = (m.group("e_era") or "").upper()

        # Infer full end year from start century (initial guess)
        century_base = (s_y // 100) * 100
        end_year = century_base + e_yy
        if end_year < s_y:
            end_year += 100

        # Determine BC/AD markers and propagate/fallback to page context
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

        # Adjust inferred end_year to ensure chronological validity based on era
        if start_year_is_bc:
            # In BC, years increase backwards; ensure end_year <= start_year
            if end_year > s_y:
                end_year -= 100
        else:
            # In AD, ensure end_year >= start_year (roll forward if necessary)
            if end_year < s_y:
                end_year += 100

        span = Span(
            start_year=s_y,
            start_month=1,
            start_day=1,
            end_year=end_year,
            end_month=12,
            end_day=31,
            start_year_is_bc=start_year_is_bc,
            end_year_is_bc=end_year_is_bc,
            precision=SpanPrecision.YEAR_ONLY,
            match_type=f"Short range: {s_y}-{e_yy:02d}",
        )

        return self._return_none_if_invalid(span)
