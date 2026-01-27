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
    PARENTHESIZED_SHORT_YEAR_RANGE = auto()
    PARENTHESIZED_YEAR_RANGE = auto()
    PARENTHESIZED_YEAR_RANGE_WITH_LOCATION = auto()
    PARENTHESIZED_CIRCA_YEAR_RANGE_WITH_LOCATION = auto()
    PARENTHESIZED_MIRRORED_ERA_YEAR_RANGE = auto()
    PARENTHESIZED_DECADE_RANGE = auto()
    PARENTHESIZED_YEAR = auto()
    PARENTHESIZED_CIRCA_YEAR_RANGE = auto()
    PARENTHESIZED_CENTURY_WITH_LOCATION = auto()
    PARENTHESIZED_DECADE = auto()
    YEAR_RANGE = auto()
    YEAR_WITH_EXPLICIT_ERA = auto()
    YEAR_ONLY = auto()
    FALLBACK = auto()
    CIRCA_YEAR = auto()
    # New parsers for Timeline of Food
    CENTURY = auto()
    CENTURY_RANGE = auto()
    CENTURY_WITH_MODIFIER = auto()
    YEARS_AGO = auto()
    TILDE_CIRCA_YEAR = auto()


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
        from span_parsing.parenthesized_year_range_parser import ParenthesizedYearRangeParser
        from span_parsing.parenthesized_decade_parser import ParenthesizedDecadeParser
        from span_parsing.parenthesized_year_range_with_location_parser import ParenthesizedYearRangeWithLocationParser
        from span_parsing.parenthesized_circa_year_range_with_location_parser import ParenthesizedCircaYearRangeWithLocationParser
        from span_parsing.parenthesized_century_with_location_parser import ParenthesizedCenturyWithLocationParser
        from span_parsing.parenthesized_circa_year_range_parser import ParenthesizedCircaYearRangeParser
        from span_parsing.parenthesized_year_parser import ParenthesizedYearParser
        from span_parsing.parenthesized_short_year_range_parser import ParenthesizedShortYearRangeParser
        from span_parsing.parenthesized_mirrored_era_year_range_parser import ParenthesizedMirroredEraYearRangeParser
        from span_parsing.parenthesized_decade_range_parser import ParenthesizedDecadeRangeParser
        # New parsers for Timeline of Food
        from span_parsing.century_parser import CenturyParser
        from span_parsing.century_range_parser import CenturyRangeParser
        from span_parsing.century_with_modifier_parser import CenturyWithModifierParser
        from span_parsing.years_ago_parser import YearsAgoParser
        from span_parsing.tilde_circa_year_parser import TildeCircaYearParser

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
        elif strategy == SpanParsers.PARENTHESIZED_YEAR_RANGE:
            return ParenthesizedYearRangeParser()
        elif strategy == SpanParsers.PARENTHESIZED_MIRRORED_ERA_YEAR_RANGE:
            return ParenthesizedMirroredEraYearRangeParser()
        elif strategy == SpanParsers.PARENTHESIZED_DECADE_RANGE:
            return ParenthesizedDecadeRangeParser()
        elif strategy == SpanParsers.PARENTHESIZED_SHORT_YEAR_RANGE:
            return ParenthesizedShortYearRangeParser()
        elif strategy == SpanParsers.PARENTHESIZED_YEAR:
            return ParenthesizedYearParser()
        elif strategy == SpanParsers.PARENTHESIZED_CIRCA_YEAR_RANGE:
            return ParenthesizedCircaYearRangeParser()
        elif strategy == SpanParsers.PARENTHESIZED_DECADE:
            return ParenthesizedDecadeParser()
        elif strategy == SpanParsers.PARENTHESIZED_YEAR_RANGE_WITH_LOCATION:
            return ParenthesizedYearRangeWithLocationParser()
        elif strategy == SpanParsers.PARENTHESIZED_CIRCA_YEAR_RANGE_WITH_LOCATION:
            return ParenthesizedCircaYearRangeWithLocationParser()
        elif strategy == SpanParsers.PARENTHESIZED_CENTURY_WITH_LOCATION:
            return ParenthesizedCenturyWithLocationParser()
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
        elif strategy == SpanParsers.CENTURY:
            return CenturyParser()
        elif strategy == SpanParsers.CENTURY_RANGE:
            return CenturyRangeParser()
        elif strategy == SpanParsers.CENTURY_WITH_MODIFIER:
            return CenturyWithModifierParser()
        elif strategy == SpanParsers.YEARS_AGO:
            return YearsAgoParser()
        elif strategy == SpanParsers.TILDE_CIRCA_YEAR:
            return TildeCircaYearParser()
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
