"""Factory for creating span parser strategies."""

from enum import Enum, auto
from span_parsing.strategy import SpanParserStrategy


class SpanParsers(Enum):
    """Enumeration of available span parsing strategies."""
    MONTH_AND_DAY_RANGE_WITHIN_PAGE_SPAN_ACROSS_YEARS = auto()
    MONTH_AND_DAY_RANGE_WITHIN_PAGE_SPAN_ACROSS_MONTHS = auto()
    MONTH_AND_DAY_RANGE_WITHIN_PAGE_SPAN = auto()
    MONTH_AND_DAY_WITHIN_PAGE_SPAN = auto()
    MONTH_ONLY_WITHIN_PAGE_SPAN = auto()
    YEAR_RANGE = auto()
    YEAR_WITH_EXPLICIT_ERA = auto()
    YEAR_ONLY = auto()
    FALLBACK = auto()
    CIRCA_YEAR = auto()


class SpanParserFactory:
    """Factory for creating SpanParserStrategy instances."""
    
    @staticmethod
    def get_parser(strategy: SpanParsers) -> SpanParserStrategy:
        """Get a parser instance for the specified strategy.
        
        Args:
            strategy: The type of parser to create
            
        Returns:
            An instance of the requested parser strategy
            
        Raises:
            ValueError: If the strategy is unknown
        """
        # Import here to avoid circular dependencies
        from span_parsing.multi_year_parser import MultiYearMonthAndDayRangeParser
        from span_parsing.single_year_multi_month_parser import SingleYearMultiMonthDayRangeParser
        from span_parsing.single_month_range_parser import SingleMonthDayRangeParser
        from span_parsing.single_day_parser import SingleDayParser
        from span_parsing.month_only_parser import MonthOnlyParser
        from span_parsing.year_range_parser import YearRangeParser
        from span_parsing.year_with_era_parser import YearWithEraParser
        from span_parsing.year_only_parser import YearOnlyParser
        from span_parsing.fallback_parser import FallbackSpanParser
        from span_parsing.circa_year_parser import CircaYearParser
        
        if strategy == SpanParsers.MONTH_AND_DAY_RANGE_WITHIN_PAGE_SPAN_ACROSS_YEARS:
            return MultiYearMonthAndDayRangeParser()
        elif strategy == SpanParsers.MONTH_AND_DAY_RANGE_WITHIN_PAGE_SPAN_ACROSS_MONTHS:
            return SingleYearMultiMonthDayRangeParser()
        elif strategy == SpanParsers.MONTH_AND_DAY_RANGE_WITHIN_PAGE_SPAN:
            return SingleMonthDayRangeParser()
        elif strategy == SpanParsers.MONTH_AND_DAY_WITHIN_PAGE_SPAN:
            return SingleDayParser()
        elif strategy == SpanParsers.MONTH_ONLY_WITHIN_PAGE_SPAN:
            return MonthOnlyParser()
        elif strategy == SpanParsers.YEAR_RANGE:
            return YearRangeParser()
        elif strategy == SpanParsers.YEAR_WITH_EXPLICIT_ERA:
            return YearWithEraParser()
        elif strategy == SpanParsers.YEAR_ONLY:
            return YearOnlyParser()
        elif strategy == SpanParsers.FALLBACK:
            return FallbackSpanParser()
        elif strategy == SpanParsers.CIRCA_YEAR:
            return CircaYearParser()
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
