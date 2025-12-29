"""Abstract base class for span parsing strategies."""

from abc import ABC, abstractmethod
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
        
        Uses year-level granularity only (no months/days yet).
        1 year => 365 days.
        
        Args:
            span: The span to compute weight for
            
        Returns:
            Weight in days, or None if computation fails
        """
        if span is None:
            return None
        
        try:
            # Helper to convert span fields to a date object
            def to_date(year: int, month: int, day: int, is_bc: bool) -> date:
                # There is no year 0 in the proleptic Gregorian calendar.
                # Python's datetime does not support BC dates, so for BC, we use 1 - year and treat as AD for diff.
                # This is only for span calculation, not for display.
                if is_bc:
                    # 1 BC => year 0, 2 BC => -1, etc.
                    year = -year + 1
                # Default month/day to 1 if missing/None/0
                month = month or 1
                day = day or 1
                return date(year, month, day)

            start = to_date(int(span.start_year), span.start_month, span.start_day, span.is_bc)
            end = to_date(int(span.end_year), span.end_month, span.end_day, span.is_bc)

            # If start > end, swap (shouldn't happen if validated, but for safety)
            if start > end:
                start, end = end, start

            # The span includes both endpoints, so add 1 day
            delta_days = (end - start).days + 1
            return delta_days
        except Exception:
            return None
    
    def _validate_span(self, span: Span) -> bool:
        """Validate that a span has logical date values.
        
        Args:
            span: The span to validate
            
        Returns:
            True if the span is valid, False otherwise
        """
        # Start must be before or equal to end
        if span.is_bc == False and span.start_year > span.end_year:
            return False
        if span.is_bc == True and span.start_year < span.end_year:
            return False
        if span.start_year == span.end_year:
            if span.start_month > span.end_month:
                return False
            if span.start_month == span.end_month:
                if span.start_day > span.end_day:
                    return False
        
        # Year 0 doesn't exist historically (1 BC → 1 AD)
        if int(span.start_year) == 0 or int(span.end_year) == 0:
            return False
        
        return True
    
    def _return_none_if_invalid(self, span: Span) -> Span | None:
        """Return None if the span is invalid, otherwise return the span.
        
        Args:
            span: The span to validate
            
        Returns:
            The span if valid, None otherwise
        """
        if span is None:
            return None
        if self._validate_span(span) is False:
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
