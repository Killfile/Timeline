"""Unit tests for CenturyParser."""

import pytest
from span_parsing.century_parser import CenturyParser
from span_parsing.span import SpanPrecision


class TestCenturyParser:
    """Test cases for CenturyParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CenturyParser()
    
    # BC/BCE centuries
    def test_5th_century_bce(self):
        """Test '5th century BCE' parses correctly."""
        span = self.parser.parse("5th century BCE", 2000, False)
        assert span is not None
        assert span.start_year == 500
        assert span.end_year == 401
        assert span.start_year_is_bc is True
        assert span.end_year_is_bc is True
        assert span.precision == SpanPrecision.APPROXIMATE
    
    def test_1st_century_bc(self):
        """Test '1st century BC' parses correctly."""
        span = self.parser.parse("1st century BC", 2000, False)
        assert span is not None
        assert span.start_year == 100
        assert span.end_year == 1
        assert span.start_year_is_bc is True
    
    def test_10th_century_bce(self):
        """Test '10th century BCE' parses correctly."""
        span = self.parser.parse("10th century BCE", 2000, False)
        assert span is not None
        assert span.start_year == 1000
        assert span.end_year == 901
        assert span.start_year_is_bc is True
    
    # AD/CE centuries
    def test_1st_century_ad(self):
        """Test '1st century AD' parses correctly."""
        span = self.parser.parse("1st century AD", 2000, False)
        assert span is not None
        assert span.start_year == 1
        assert span.end_year == 100
        assert span.start_year_is_bc is False
        assert span.end_year_is_bc is False
    
    def test_19th_century_ad(self):
        """Test '19th century' parses correctly."""
        span = self.parser.parse("19th century", 2000, False)
        assert span is not None
        assert span.start_year == 1801
        assert span.end_year == 1900
        assert span.start_year_is_bc is False
    
    def test_21st_century_ce(self):
        """Test '21st century CE' parses correctly."""
        span = self.parser.parse("21st century CE", 2000, False)
        assert span is not None
        assert span.start_year == 2001
        assert span.end_year == 2100
        assert span.start_year_is_bc is False
    
    def test_5th_century_ad(self):
        """Test '5th century AD' parses correctly."""
        span = self.parser.parse("5th century AD", 2000, False)
        assert span is not None
        assert span.start_year == 401
        assert span.end_year == 500
        assert span.start_year_is_bc is False
    
    # No era marker (context-dependent)
    def test_5th_century_no_marker_ad_context(self):
        """Test '5th century' with AD page context."""
        span = self.parser.parse("5th century", 500, False)
        assert span is not None
        assert span.start_year == 401
        assert span.end_year == 500
        assert span.start_year_is_bc is False
    
    def test_5th_century_no_marker_bc_context(self):
        """Test '5th century' with BC page context."""
        span = self.parser.parse("5th century", 500, True)
        assert span is not None
        assert span.start_year == 500
        assert span.end_year == 401
        assert span.start_year_is_bc is True
    
    # Ordinal suffix variations
    def test_2nd_century(self):
        """Test '2nd century' parses correctly."""
        span = self.parser.parse("2nd century AD", 2000, False)
        assert span is not None
        assert span.start_year == 101
        assert span.end_year == 200
    
    def test_3rd_century(self):
        """Test '3rd century' parses correctly."""
        span = self.parser.parse("3rd century AD", 2000, False)
        assert span is not None
        assert span.start_year == 201
        assert span.end_year == 300
    
    def test_11th_century(self):
        """Test '11th century' parses correctly."""
        span = self.parser.parse("11th century", 2000, False)
        assert span is not None
        assert span.start_year == 1001
        assert span.end_year == 1100
    
    # Case insensitivity
    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        span = self.parser.parse("5TH CENTURY BCE", 2000, False)
        assert span is not None
        assert span.start_year == 500
    
    # Edge cases and non-matches
    def test_non_century_text(self):
        """Test that non-century text returns None."""
        span = self.parser.parse("1516 AD", 2000, False)
        assert span is None
    
    def test_century_not_at_start(self):
        """Test that century not at start returns None."""
        span = self.parser.parse("In the 5th century BCE", 2000, False)
        assert span is None
    
    def test_empty_string(self):
        """Test empty string returns None."""
        span = self.parser.parse("", 2000, False)
        assert span is None
