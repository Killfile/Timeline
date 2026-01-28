"""Unit tests for CenturyRangeParser."""

import pytest
from span_parsing.century_range_parser import CenturyRangeParser
from span_parsing.span import SpanPrecision


class TestCenturyRangeParser:
    """Test cases for CenturyRangeParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CenturyRangeParser()
    
    # AD century ranges
    def test_11th_14th_centuries(self):
        """Test '11th-14th centuries' parses correctly."""
        span = self.parser.parse("11th-14th centuries", 2000, False)
        assert span is not None
        assert span.start_year == 1001
        assert span.end_year == 1400
        assert span.start_year_is_bc is False
        assert span.end_year_is_bc is False
    
    def test_15th_16th_centuries(self):
        """Test '15th-16th centuries' parses correctly."""
        span = self.parser.parse("15th-16th centuries", 2000, False)
        assert span is not None
        assert span.start_year == 1401
        assert span.end_year == 1600
        assert span.start_year_is_bc is False
    
    def test_1st_3rd_centuries_ad(self):
        """Test '1st-3rd centuries AD' parses correctly."""
        span = self.parser.parse("1st-3rd centuries AD", 2000, False)
        assert span is not None
        assert span.start_year == 1
        assert span.end_year == 300
        assert span.start_year_is_bc is False
    
    # BC century ranges
    def test_5th_3rd_centuries_bce(self):
        """Test '5th-3rd centuries BCE' (BC ranges go backwards)."""
        span = self.parser.parse("5th-3rd centuries BCE", 2000, False)
        assert span is not None
        assert span.start_year == 500
        assert span.end_year == 201
        assert span.start_year_is_bc is True
        assert span.end_year_is_bc is True
    
    def test_10th_5th_centuries_bc(self):
        """Test '10th-5th centuries BC' parses correctly."""
        span = self.parser.parse("10th-5th centuries BC", 2000, False)
        assert span is not None
        assert span.start_year == 1000
        assert span.end_year == 401
        assert span.start_year_is_bc is True
    
    # En-dash normalization
    def test_en_dash_centuries(self):
        """Test century range with en-dash is normalized."""
        span = self.parser.parse("11th–14th centuries", 2000, False)
        assert span is not None
        assert span.start_year == 1001
        assert span.end_year == 1400
    
    # No era marker (context-dependent)
    def test_no_era_marker_ad_context(self):
        """Test century range with no era marker in AD context."""
        span = self.parser.parse("5th-7th centuries", 2000, False)
        assert span is not None
        assert span.start_year == 401
        assert span.end_year == 700
        assert span.start_year_is_bc is False
    
    def test_no_era_marker_bc_context(self):
        """Test century range with no era marker in BC context."""
        span = self.parser.parse("5th-3rd centuries", 2000, True)
        assert span is not None
        assert span.start_year == 500
        assert span.end_year == 201
        assert span.start_year_is_bc is True
    
    # Edge cases and non-matches
    def test_non_range_text(self):
        """Test that non-range text returns None."""
        span = self.parser.parse("5th century BCE", 2000, False)
        assert span is None
    
    def test_empty_string(self):
        """Test empty string returns None."""
        span = self.parser.parse("", 2000, False)
        assert span is None
    
    def test_century_range_not_at_start(self):
        """Test that century range not at start returns None."""
        span = self.parser.parse("From the 11th-14th centuries", 2000, False)
        assert span is None
