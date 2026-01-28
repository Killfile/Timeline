"""Parser for century with modifiers like 'Early 1700s', 'Late 16th century', 'Before 17th century'."""

import re
from span_parsing.strategy import SpanParserStrategy
from span_parsing.span import Span, SpanPrecision


class CenturyWithModifierParser(SpanParserStrategy):
    """Parses century formats with temporal modifiers.
    
    Matches patterns like:
    - Early 1700s
    - Mid 16th century
    - Late 16th century
    - Before 17th century
    - Late 5th century BCE
    - Early 16th century-17th century (hybrid range)
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse century with modifier at the start of text.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        # Normalize dashes first
        text = self.normalize_dashs(text)
        
        # Match hybrid range pattern first: "Late 16th century-17th century"
        m_hybrid = re.match(
            r"^\s*(Early|Mid|Late)\s+(\d{1,2})(00s|(?:st|nd|rd|th)\s+century)\s*-\s*(\d{1,2})(00s|(?:st|nd|rd|th)\s+century)?\s*(BCE|BC|AD|CE)?\b",
            text,
            flags=re.IGNORECASE
        )
        
        if m_hybrid:
            modifier = m_hybrid.group(1).lower()
            start_century = int(m_hybrid.group(2))
            start_format = m_hybrid.group(3).lower()
            end_century = int(m_hybrid.group(4))
            end_format = m_hybrid.group(5).lower() if m_hybrid.group(5) else ""
            era_marker = m_hybrid.group(6)
            
            # Determine BC/AD
            if era_marker:
                is_bc = era_marker.upper() in ("BC", "BCE")
            else:
                is_bc = page_bc
            
            # Calculate start century range
            if is_bc:
                century_start = start_century * 100
                century_end = (start_century - 1) * 100 + 1
            else:
                if "00s" in start_format:
                    century_start = start_century * 100
                    century_end = start_century * 100 + 99
                else:
                    century_start = (start_century - 1) * 100 + 1
                    century_end = start_century * 100
            
            # Apply modifier to get start year
            century_length = abs(century_start - century_end) + 1
            third = century_length // 3
            
            if modifier == 'early':
                start_year = century_start
            elif modifier == 'mid':
                if is_bc:
                    start_year = century_start - third
                else:
                    start_year = century_start + third
            else:  # late
                if is_bc:
                    start_year = century_start - (2 * third)
                else:
                    start_year = century_start + (2 * third)
            
            # Calculate end year from end century
            if is_bc:
                end_year = (end_century - 1) * 100 + 1
            else:
                if "00s" in end_format:
                    end_year = end_century * 100 + 99
                else:
                    end_year = end_century * 100
            
            span = Span(
                start_year=start_year,
                end_year=end_year,
                start_month=1,
                start_day=1,
                end_month=12,
                end_day=31,
                start_year_is_bc=is_bc,
                end_year_is_bc=is_bc,
                precision=SpanPrecision.APPROXIMATE,
                match_type=f"{modifier.capitalize()} {start_century}th century-{end_century}th century"
            )
            
            return self._return_none_if_invalid(span)
        
        # Match "Before Nth century" pattern
        m_before = re.match(
            r"^\s*Before\s+(\d{1,2})(00s|(?:st|nd|rd|th)\s+century)\s*(BCE|BC|AD|CE)?\b",
            text,
            flags=re.IGNORECASE
        )
        
        if m_before:
            target_century = int(m_before.group(1))
            era_marker = m_before.group(2)
            
            # Determine BC/AD
            if era_marker:
                is_bc = era_marker.upper() in ("BC", "BCE")
            else:
                is_bc = page_bc
            
            # "Before Nth century" = Late (N+1)th century for BC, Late (N-1)th century for AD
            if is_bc:
                # For BC, "Before 5th century BCE" means before 500-401 BCE
                # So we want Late 6th century BCE
                prev_century = target_century + 1
            else:
                # For AD, "Before 17th century" means before 1601-1700
                # So we want Late 16th century
                prev_century = target_century - 1
            
            if is_bc:
                # BC: late portion of previous century
                century_start = prev_century * 100
                century_end = (prev_century - 1) * 100 + 1
                century_length = century_start - century_end + 1
                # Late = last third (67% through to end)
                start_year = century_start - int(century_length * 2 / 3)
                end_year = century_end
            else:
                # AD: late portion of previous century
                century_start = (prev_century - 1) * 100 + 1
                century_end = prev_century * 100
                century_length = century_end - century_start + 1
                # Late = last third
                start_year = century_start + int(century_length * 2 / 3)
                end_year = century_end
            
            span = Span(
                start_year=start_year,
                end_year=end_year,
                start_month=1,
                start_day=1,
                end_month=12,
                end_day=31,
                start_year_is_bc=is_bc,
                end_year_is_bc=is_bc,
                precision=SpanPrecision.APPROXIMATE,
                match_type=f"Before {target_century}th century"
            )
            
            return self._return_none_if_invalid(span)
        
        # Match standard modifier patterns: "Early 1700s" or "Late 16th century"
        # Pattern captures the format type to distinguish "00s" from "th century"
        m = re.match(
            r"^\s*(Early|Mid|Late)\s+(\d{1,2})(00s|(?:st|nd|rd|th)\s+century)\s*(BCE|BC|AD|CE)?\b",
            text,
            flags=re.IGNORECASE
        )
        
        if not m:
            return None
        
        modifier = m.group(1).lower()
        century_digits = int(m.group(2))
        format_type = m.group(3).lower()  # "00s" or "th century"
        era_marker = m.group(4)
        
        # Determine BC/AD based on explicit marker or page context
        if era_marker:
            is_bc = era_marker.upper() in ("BC", "BCE")
        else:
            is_bc = page_bc
        
        # Calculate base century range
        # For "1700s" format, century_digits is 17 (representing 1700s)
        # For "16th century", century_digits is 16
        if is_bc:
            century_start = century_digits * 100
            century_end = (century_digits - 1) * 100 + 1
        else:
            # For AD centuries
            if "00s" in format_type:
                # "1700s" format: means years 1700-1799
                century_start = century_digits * 100
                century_end = century_digits * 100 + 99
            else:
                # "16th century" format: means years 1501-1600
                century_start = (century_digits - 1) * 100 + 1
                century_end = century_digits * 100
        
        # Apply modifier to divide century into thirds
        # Early = 0-33%, Mid = 34-66%, Late = 67-100%
        century_length = abs(century_start - century_end) + 1
        third = century_length // 3
        
        if modifier == 'early':
            if is_bc:
                start_year = century_start
                end_year = century_start - third + 1
            else:
                start_year = century_start
                end_year = century_start + third - 1
        elif modifier == 'mid':
            if is_bc:
                start_year = century_start - third
                end_year = century_start - (2 * third) + 1
            else:
                start_year = century_start + third
                end_year = century_start + (2 * third) - 1
        else:  # late
            if is_bc:
                start_year = century_start - (2 * third)
                end_year = century_end
            else:
                start_year = century_start + (2 * third)
                end_year = century_end
        
        span = Span(
            start_year=start_year,
            end_year=end_year,
            start_month=1,
            start_day=1,
            end_month=12,
            end_day=31,
            start_year_is_bc=is_bc,
            end_year_is_bc=is_bc,
            precision=SpanPrecision.APPROXIMATE,
            match_type=f"{modifier.capitalize()} {century_digits}th century"
        )
        
        return self._return_none_if_invalid(span)
