"""Span parsing module for parsing date spans from Wikipedia text.

This module provides a comprehensive set of parsers for extracting date spans
from various text formats, including single dates, date ranges, and dates with
varying levels of precision (year, month, day).
"""

from span_parsing.span import Span
from span_parsing.strategy import SpanParserStrategy
from span_parsing.factory import SpanParsers, SpanParserFactory
from span_parsing.span_parser import SpanParser

# Export main classes for backward compatibility
__all__ = [
    "Span",
    "SpanParser",
    "SpanParserStrategy",
    "SpanParsers",
    "SpanParserFactory",
]
