"""Unit tests for YearsAgoParser."""

import pytest
from datetime import datetime
from span_parsing.years_ago_parser import YearsAgoParser
from span_parsing.span import SpanPrecision


class TestYearsAgoParser:
    """Test cases for YearsAgoParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = YearsAgoParser()
        # Anchor to a deterministic page year for reproducible tests
        self.anchor_year = 2000
    
    # Single value patterns
    def test_250000_years_ago(self):
        """Test '250,000 years ago' parses correctly."""
        span = self.parser.parse("250,000 years ago", self.anchor_year, False)
        assert span is not None
        expected_year = self.anchor_year - 250000
        assert span.start_year == abs(expected_year)
        assert span.end_year == abs(expected_year)
        assert span.start_year_is_bc is True
        assert span.end_year_is_bc is True
        assert span.precision == SpanPrecision.CIRCA
    
    def test_170000_years_ago(self):
        """Test '170,000 years ago' parses correctly."""
        span = self.parser.parse("170,000 years ago", self.anchor_year, False)
        assert span is not None
        expected_year = self.anchor_year - 170000
        assert span.start_year == abs(expected_year)
        assert span.start_year_is_bc is True
    
    def test_10000_years_ago_no_comma(self):
        """Test '10000 years ago' (no comma) parses correctly."""
        span = self.parser.parse("10000 years ago", self.anchor_year, False)
        assert span is not None
        expected_year = self.anchor_year - 10000
        assert span.start_year == abs(expected_year)
    
    # Million multiplier
    def test_2_million_years_ago(self):
        """Test '2 million years ago' parses correctly."""
        span = self.parser.parse("2 million years ago", self.anchor_year, False)
        assert span is not None
        expected_year = self.anchor_year - 2000000
        assert span.start_year == abs(expected_year)
        assert span.start_year_is_bc is True
    
    def test_2_5_million_years_ago(self):
        """Test '2.5 million years ago' parses correctly."""
        span = self.parser.parse("2.5 million years ago", self.anchor_year, False)
        assert span is not None
        expected_year = self.anchor_year - 2500000
        assert span.start_year == abs(expected_year)
    
    # Thousand multiplier
    def test_50_thousand_years_ago(self):
        """Test '50 thousand years ago' parses correctly."""
        span = self.parser.parse("50 thousand years ago", self.anchor_year, False)
        assert span is not None
        expected_year = self.anchor_year - 50000
        assert span.start_year == abs(expected_year)
    
    # Range patterns
    def test_5_2_million_years_ago_range(self):
        """Test '5-2 million years ago' range parses correctly."""
        span = self.parser.parse("5-2 million years ago", self.anchor_year, False)
        assert span is not None
        expected_start = self.anchor_year - 5000000
        expected_end = self.anchor_year - 2000000
        assert span.start_year == abs(expected_start)
        assert span.end_year == abs(expected_end)
        assert span.start_year_is_bc is True
    
    def test_300000_100000_years_ago_range(self):
        """Test '300,000-100,000 years ago' range parses correctly."""
        span = self.parser.parse("300,000-100,000 years ago", self.anchor_year, False)
        assert span is not None
        expected_start = self.anchor_year - 300000
        expected_end = self.anchor_year - 100000
        assert span.start_year == abs(expected_start)
        assert span.end_year == abs(expected_end)
    
    # Edge cases
    def test_singular_year(self):
        """Test '1000 year ago' (singular) parses correctly."""
        span = self.parser.parse("1000 year ago", self.anchor_year, False)
        assert span is not None
        expected_year = self.anchor_year - 1000
        assert span.start_year == abs(expected_year)
    
    def test_non_years_ago_text(self):
        """Test that non-'years ago' text returns None."""
        span = self.parser.parse("5th century BCE", self.anchor_year, False)
        assert span is None
    
    def test_empty_string(self):
        """Test empty string returns None."""
        span = self.parser.parse("", self.anchor_year, False)
        assert span is None
    
    def test_years_ago_not_at_start(self):
        """Test that 'years ago' not at start returns None."""
        span = self.parser.parse("About 250,000 years ago", self.anchor_year, False)
        assert span is None
