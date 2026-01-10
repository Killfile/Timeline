"""Abstract base class for span parsing strategies."""

from abc import ABC, abstractmethod
from datetime import date
from span_parsing.span import Span


class SpanParserStrategy(ABC):
    """Interface for span parsing strategies."""
    
    def normalize_dashs(self, text: str) -> str:
        """Normalize various dash characters to a standard hyphen-minus."""
        dash_variants = ['–', '—', '―', '−']  # en dash, em dash, horizontal bar, minus sign
        for dash in dash_variants:
            text = text.replace(dash, '-')
        return text
    
    def compute_weight_days(self, span: Span) -> int | None:
        """Compute the weight (approximate span length in days) for a span.
        
        Uses manual date arithmetic to handle BC years since Python's datetime
        doesn't support years < 1.
        
        Args:
            span: The span to compute weight for
            
        Returns:
            Weight in days, or None if computation fails
        """
        if span is None:
            return None
        
        try:
            # Helper to convert BC/AD year to a continuous timeline number
            # BC: 100 BC = -99, 1 BC = 0
            # AD: 1 AD = 1, 100 AD = 100
            def to_timeline_year(year: int, is_bc: bool) -> int:
                if is_bc:
                    return -year + 1
                return year
            
            # Default month/day to 1 if missing/None/0
            start_month = span.start_month or 1
            start_day = span.start_day or 1
            end_month = span.end_month or 1
            end_day = span.end_day or 1
            
            start_year = to_timeline_year(int(span.start_year), span.start_year_is_bc)
            end_year = to_timeline_year(int(span.end_year), span.end_year_is_bc)
            
            # Calculate approximate days using year difference and month/day offsets
            # This is approximate since we don't account for leap years in BC era
            year_diff = end_year - start_year
            days_from_years = year_diff * 365
            
            # Month to approximate day offset (using 30.44 days/month average)
            month_to_days = [0, 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
            
            start_day_of_year = month_to_days[start_month] + start_day if start_month <= 12 else start_day
            end_day_of_year = month_to_days[end_month] + end_day if end_month <= 12 else end_day
            
            total_days = days_from_years + (end_day_of_year - start_day_of_year) + 1
            
            # Ensure minimum of 1 day
            return max(1, total_days)
        except Exception:
            return None
    
    def _validate_span(self, span: Span) -> bool:
        """Validate that a span has logical date values.
        
        Deprecated: Use span.is_valid() instead.
        
        Args:
            span: The span to validate
            
        Returns:
            True if the span is valid, False otherwise
        """
        return span.is_valid()
    
    def _return_none_if_invalid(self, span: Span) -> Span | None:
        """Return None if the span is invalid, otherwise return the span.
        
        Args:
            span: The span to validate
            
        Returns:
            The span if valid, None otherwise
        """
        if span is None:
            return None
        if not span.is_valid():
            return None
        return span

    @abstractmethod
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Parse text into a Span, or return None if not parseable.
        
        Args:
            text: The text to parse
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        pass

    @staticmethod
    def month_name_to_number(month_name: str) -> int | None:
        """Convert month name to month number.

        Args:
            month_name: The name of the month (case-insensitive)

        Returns:
            The month number (1-12) or None if not recognized
        """
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
