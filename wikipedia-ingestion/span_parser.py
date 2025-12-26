from dataclasses import dataclass
import re

@dataclass
class Span:
    start_year: int
    start_month: int
    start_day: int
    end_year: int
    end_month: int
    end_day: int
    is_bc: bool
    precision: str
    match_type: str

class SpanParser:
    """Module for parsing date spans from text."""

    _DASH_RE = re.compile(r"\s*[–—−-]\s*")

    @staticmethod
    def is_circa_text(text: str) -> bool:
        """Check if the text indicates an approximate date (circa)."""
        return bool(re.match(r"^\s*(c\.|ca\.|circa)\b", text.strip(), flags=re.IGNORECASE))

    @staticmethod
    def parse_span_from_bullet(text: str, span_year: int, *, assume_is_bc: bool | None = None) -> Span | None:
        if not text:
            return None
        t = text.strip()

        lead = re.sub(r"^\s+", "", t)
        if re.match(r"^(c\s*\.|ca\s*\.|circa)(\s|$)", lead, flags=re.IGNORECASE):
            return None

        t_norm = SpanParser._DASH_RE.sub("-", t)

        return_value = SpanParser._parse_month_and_day_range_within_page_span_across_years(t_norm, span_year, bool(assume_is_bc))
        if return_value is not None:
            return return_value

        return_value = SpanParser._parse_month_and_day_range_within_page_span_across_months(t_norm, span_year, bool(assume_is_bc))
        if return_value is not None:
            return return_value

        return_value = SpanParser._parse_month_and_day_range_within_page_span(t_norm, span_year, bool(assume_is_bc))
        if return_value is not None:
            return return_value
        
        return_value = SpanParser._parse_month_and_day_within_page_span(t_norm, span_year, page_bc=bool(assume_is_bc))
        if return_value is not None:
            return return_value
        
        return_value = SpanParser._parse_month_only_within_page_span(t_norm, span_year, bool(assume_is_bc))
        if return_value is not None:
            return return_value
        

        return_value = SpanParser._parse_year_range(t_norm, assume_is_bc)
        if return_value is not None:
            return return_value
        

        return_value = SpanParser._parse_year_with_explicit_era(t_norm)
        if return_value is not None:
            return return_value
        
        return_value = SpanParser._parse_year_only(t_norm, assume_is_bc)
        if return_value is not None:
            return return_value
        
        return None

    @staticmethod
    def month_name_to_number(month_name: str) -> int | None:
        month_name = month_name.lower()
        months = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }
        return months.get(month_name)
    
    @staticmethod
    def _parse_month_and_day_within_page_span(text_to_search: str, page_year: int, page_bc: bool = False) -> Span | None:
        # EG: September 25
        # EG: August 29 – Christian Cross Asterism (astronomy) at Zenith of Lima, Peru. 

        # Implementation should match the month-name and day pattern and create a single-day Span using the provided year
        m = re.search(r"(?<!\d)(\w+)\s+(\d{1,2})", text_to_search)
        if m:
            month_name = m.group(1)
            day = int(m.group(2))
            month = SpanParser.month_name_to_number(month_name)
            if month is not None:
                return Span(start_year=page_year, start_month=month, start_day=day, end_year=page_year, end_month=month, end_day=day, is_bc=page_bc, precision="day", match_type="Single day within page span. EG: Month DD")
        return None

    @staticmethod
    def _parse_month_and_day_range_within_page_span(text_to_search: str, page_year: int, page_bc: bool) -> Span | None:
        # EG: September 25–28
        m = re.search(r"(?<!\d)(\w+)\s+(\d{1,2})\s*[–—−-]\s*(\d{1,2})", text_to_search)
        if m:
            month_name = m.group(1)
            day = int(m.group(2))
            month = SpanParser.month_name_to_number(month_name)
            if month is not None:
                return Span(start_year=page_year, start_month=month, start_day=day, end_year=page_year, end_month=month, end_day=int(m.group(3)), is_bc=page_bc, precision="day", match_type="Day range within page span (same month). EG: Month DD-DD")
        return None
    
    @staticmethod
    def _parse_month_only_within_page_span(text_to_search: str, page_year: int, page_bc: bool) -> Span | None:
        # EG: September
        m = re.search(r"(?<!\d)(\w+)(?!\d)", text_to_search)
        if m:
            month_name = m.group(1)
            month = SpanParser.month_name_to_number(month_name)
            if month is not None:
                # Calculate actual days in month (simplified - doesn't handle leap years)
                days_in_month = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 
                                 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
                return Span(start_year=page_year, start_month=month, start_day=1, end_year=page_year, end_month=month, end_day=days_in_month.get(month, 31), is_bc=page_bc, precision="month", match_type="Month only within page span. EG: Month")
        return None
    
    @staticmethod
    def _parse_month_and_day_range_within_page_span_across_months(text_to_search: str, page_year: int, page_bc: bool) -> Span | None:
        # EG: September 28 – October 2
        m = re.search(r"(?<!\d)(\w+)\s+(\d{1,2})\s*[–—−-]\s*(\w+)\s+(\d{1,2})", text_to_search)
        if m:
            start_month_name = m.group(1)
            start_day = int(m.group(2))
            end_month_name = m.group(3)
            end_day = int(m.group(4))
            start_month = SpanParser.month_name_to_number(start_month_name)
            end_month = SpanParser.month_name_to_number(end_month_name)
            if start_month is not None and end_month is not None:
                return Span(start_year=page_year, start_month=start_month, start_day=start_day, end_year=page_year, end_month=end_month, end_day=end_day, is_bc=page_bc, precision="day", match_type="Day range across months within page span. EG: Month DD - Month DD")
        return None

    @staticmethod
    def _parse_month_and_day_range_within_page_span_across_years(text_to_search: str, page_year: int, page_bc: bool) -> Span | None:
        # EG: September 28, 2020 – October 2, 2020
        # Note: When explicit years are provided, use those to determine BC/AD status
        m = re.search(r"(?<!\d)(\w+)\s+(\d{1,2}),\s*(\d{4})\s*[–—−-]\s*(\w+)\s+(\d{1,2}),\s*(\d{4})", text_to_search)
        if m:
            start_month_name = m.group(1)
            start_day = int(m.group(2))
            start_year = int(m.group(3))
            end_month_name = m.group(4)
            end_day = int(m.group(5))
            end_year = int(m.group(6))
            start_month = SpanParser.month_name_to_number(start_month_name)
            end_month = SpanParser.month_name_to_number(end_month_name)
            if start_month is not None and end_month is not None:
                # Explicit year in text typically means AD unless page context is BC
                return Span(start_year=start_year, start_month=start_month, start_day=start_day, end_year=end_year, end_month=end_month, end_day=end_day, is_bc=page_bc, precision="day", match_type="Day range across years within page span. EG: Month DD, YYYY - Month DD, YYYY")
        return None 

    @staticmethod
    def _parse_year_range(text_to_search: str, assume_is_bc: bool | None) -> Span | None:
        
        m = re.search(
            r"(?<!\d)(\d{1,4})\s*(BC|BCE|AD|CE)?\s*-\s*(\d{1,4})\s*(BC|BCE|AD|CE)?",
            text_to_search,
            flags=re.IGNORECASE,
        )
        if m:
            s_y = int(m.group(1))
            s_era = (m.group(2) or "").upper()
            e_y = int(m.group(3))
            e_era = (m.group(4) or "").upper()

            is_bc = ("BC" in s_era) or ("BC" in e_era) or ("BCE" in s_era) or ("BCE" in e_era)
            is_ad = ("AD" in s_era) or ("AD" in e_era) or ("CE" in s_era) or ("CE" in e_era)
            if is_bc and is_ad:
                return None

            if not is_bc and not is_ad and assume_is_bc is not None:
                is_bc = bool(assume_is_bc)

            start_year = min(s_y, e_y)
            end_year = max(s_y, e_y)
            return Span(start_year=start_year, start_month=1, start_day=1, end_year=end_year, end_month=12, end_day=31, is_bc=bool(is_bc and not is_ad), precision="year", match_type="Range. EG: ### BC - ####")

        return None
    
    @staticmethod
    def _parse_year_with_explicit_era(text_to_search: str) -> Span | None:

        m = re.search(r"(?<!\d)(\d{1,4})\s*(BC|BCE|AD|CE)\b", text_to_search, flags=re.IGNORECASE)
        if m:
            y = int(m.group(1))
            era = (m.group(2) or "").upper()
            is_bc = era in {"BC", "BCE"}
            return Span(start_year=y, end_year=y, start_month=1, start_day=1, end_month=12, end_day=31, is_bc=is_bc, precision="year", match_type=f"Year with explicit era. EG: #### {era}")
        return None
    
    @staticmethod
    def _parse_year_only(text_to_search: str, assume_is_bc: bool | None) -> Span | None:

        m = re.search(r"(?<!\d)(\d{3,4})(?!\d)", text_to_search)
        if m:
            y = int(m.group(1))
            if assume_is_bc is not None:
                bc = bool(assume_is_bc)
            else:
                bc = False
            return Span(start_year=y, end_year=y, start_month=1, start_day=1, end_month=12, end_day=31, is_bc=bc, precision="year", match_type="3-4 digit year only. EG: ####")
        return None