"""Main span parser class with validation and utility methods."""

import re
from span_parsing.span import Span
from span_parsing.factory import SpanParsers, SpanParserFactory


class SpanParser:
    """Module for parsing date spans from text."""

    _DASH_RE = re.compile(r"\s*[–—−-]\s*")

    @staticmethod
    def is_circa_text(text: str) -> bool:
        """Check if the text indicates an approximate date (circa)."""
        return bool(re.match(r"^\s*(c\.|ca\.|circa)\s?\d{1,4}\s?(BC|AD)?", text.strip(), flags=re.IGNORECASE))

    @staticmethod
    def parse_span_from_bullet(text: str, span_year: int, *, assume_is_bc: bool | None = None) -> Span | None:
        """Parse a date span from bullet point text.
        
        Args:
            text: The text to parse
            span_year: The year from the Wikipedia page context
            assume_is_bc: Whether to assume BC/BCE if not explicitly stated
            
        Returns:
            A Span object if parsing succeeds, None otherwise
        """
        if not text:
            return None
        t = text.strip()

        # Skip circa dates
        lead = re.sub(r"^\s+", "", t)
        if re.match(r"^(c\s*\.|ca\s*\.|circa)(\s|$)", lead, flags=re.IGNORECASE):
            return None

        # Normalize dash characters
        text_to_parse = SpanParser._DASH_RE.sub("-", t)

        # Try each parser strategy in order
        parser_steps = [
            SpanParsers.MONTH_AND_DAY_RANGE_WITHIN_PAGE_SPAN_ACROSS_YEARS,
            SpanParsers.MONTH_AND_DAY_RANGE_WITHIN_PAGE_SPAN_ACROSS_MONTHS,
            SpanParsers.MONTH_AND_DAY_RANGE_WITHIN_PAGE_SPAN,
            SpanParsers.MONTH_AND_DAY_WITHIN_PAGE_SPAN,
            SpanParsers.MONTH_ONLY_WITHIN_PAGE_SPAN,
            SpanParsers.YEAR_RANGE,
            SpanParsers.YEAR_WITH_EXPLICIT_ERA,
            SpanParsers.YEAR_ONLY,
        ]

        for step in parser_steps:
            parser = SpanParserFactory.get_parser(step)
            return_value = parser.parse(text_to_parse, span_year, bool(assume_is_bc))
            if return_value is not None:
                return return_value

        return None

    @staticmethod
    def _validate_span(span: Span) -> bool:
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

    @staticmethod
    def _return_none_if_invalid(span: Span) -> Span | None:
        """Return None if the span is invalid, otherwise return the span.
        
        Args:
            span: The span to validate
            
        Returns:
            The span if valid, None otherwise
        """
        if span is None:
            return None
        if SpanParser._validate_span(span) is False:
            return None
        return span

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
