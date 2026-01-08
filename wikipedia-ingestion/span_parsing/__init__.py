"""Span parsing module for parsing date spans from Wikipedia text.

This module provides a comprehensive set of parsers for extracting date spans
from various text formats, including single dates, date ranges, and dates with
varying levels of precision (year, month, day).
"""

from .span import Span
from .strategy import SpanParserStrategy
from .factory import SpanParsers, SpanParserFactory
from .orchestrators.parse_orchestrator import ParseOrchestrator

# ListOfTimePeriodsSpanParser is now imported directly from strategies.list_of_time_periods.list_of_time_periods_span_parser

# Export main classes for backward compatibility
__all__ = [
    "Span",
    "ParseOrchestrator",
    "ListOfTimePeriodsSpanParser",
    "SpanParserStrategy",
    "SpanParsers",
    "SpanParserFactory",
]
