"""Tests for DecadeParser."""

import pytest
from span_parsing.decade_parser import DecadeParser
from span_parsing.span import SpanPrecision


class TestDecadeParser:
    """Test cases for parsing decade notations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DecadeParser()
    
    # Basic decade patternsP
    
    def test_parse_1990s(self):
        """Test parsing 1990s → 1990-1999."""
        result = self.parser.parse("1990s", 1990, False)
        assert result is not None
        assert result.start_year == 1990
        assert result.end_year == 1999
        assert result.start_year_is_bc is False
        assert result.end_year_is_bc is False
        assert result.precision == SpanPrecision.YEAR_ONLY

    def test_parse_1990s_bc(self):
        """Test parsing 1990s on a BC page → 1990-1999 AD."""
        result = self.parser.parse("1990s", 1990, True)
        assert result is not None
        assert result.start_year == 1999
        assert result.end_year == 1990
        assert result.start_year_is_bc is True
        assert result.end_year_is_bc is True
        assert result.precision == SpanPrecision.YEAR_ONLY
    
    def test_parse_1800s(self):
        """Test parsing 1800s → 1800-1809."""
        result = self.parser.parse("1800s", 1800, False)
        assert result is not None
        assert result.start_year == 1800
        assert result.end_year == 1809
        assert result.start_year_is_bc is False
        assert result.end_year_is_bc is False
    
    def test_parse_2000s(self):
        """Test parsing 2000s → 2000-2009."""
        result = self.parser.parse("2000s", 2000, False)
        assert result is not None
        assert result.start_year == 2000
        assert result.end_year == 2009
    
    def test_parse_1950s(self):
        """Test parsing 1950s → 1950-1959."""
        result = self.parser.parse("1950s", 1950, False)
        assert result is not None
        assert result.start_year == 1950
        assert result.end_year == 1959
    
    def test_parse_2010s(self):
        """Test parsing 2010s → 2010-2019."""
        result = self.parser.parse("2010s", 2010, False)
        assert result is not None
        assert result.start_year == 2010
        assert result.end_year == 2019
    
    def test_parse_1920s(self):
        """Test parsing 1920s → 1920-1929."""
        result = self.parser.parse("1920s", 1920, False)
        assert result is not None
        assert result.start_year == 1920
        assert result.end_year == 1929
    
    # Whitespace handling
    
    def test_parse_with_leading_whitespace(self):
        """Test parsing with leading whitespace."""
        result = self.parser.parse("  1990s", 1990, False)
        assert result is not None
        assert result.start_year == 1990
        assert result.end_year == 1999
    
    def test_parse_with_trailing_text(self):
        """Test that decade is at start (not embedded)."""
        result = self.parser.parse("1990s were great", 1990, False)
        assert result is not None
        assert result.start_year == 1990
        assert result.end_year == 1999
    
    def test_parse_embedded_not_at_start(self):
        """Test that embedded decade (not at start) is rejected."""
        result = self.parser.parse("During the 1990s, things changed", 1990, False)
        assert result is None
    
    # Case handling
    
    def test_parse_lowercase_s(self):
        """Test parsing with lowercase 's'."""
        result = self.parser.parse("1990s", 1990, False)
        assert result is not None
        assert result.start_year == 1990
    
    def test_parse_uppercase_s(self):
        """Test parsing with uppercase 'S'."""
        result = self.parser.parse("1990S", 1990, False)
        assert result is not None
        assert result.start_year == 1990
    
    # Page context handling
    
    def test_parse_with_page_bc_context(self):
        """Decade notation inherits BC context from the page."""
        result = self.parser.parse("1500s", 1500, True)
        assert result is not None
        assert result.start_year_is_bc is True
        assert result.end_year_is_bc is True
    
    def test_parse_with_page_ad_context(self):
        """Test that page AD context does not affect decade parsing."""
        result = self.parser.parse("1990s", 1990, False)
        assert result is not None
        assert result.start_year_is_bc is False
    
    # Invalid patterns
    
    def test_invalid_year_ending_in_1(self):
        """Test that year ending in 1 (e.g., 1991s) is rejected."""
        result = self.parser.parse("1991s", 1991, False)
        assert result is None
    
    def test_invalid_year_ending_in_5(self):
        """Test that year ending in 5 (e.g., 1995s) is rejected."""
        result = self.parser.parse("1995s", 1995, False)
        assert result is None
    
    def test_invalid_two_digit_year(self):
        """Test that 2-digit year (e.g., 90s) is rejected."""
        result = self.parser.parse("90s", 1990, False)
        assert result is None
    
    def test_invalid_single_digit_year(self):
        """Test that 1-digit year is rejected."""
        result = self.parser.parse("5s", 5, False)
        assert result is None
    
    def test_invalid_just_s(self):
        """Test that just 's' is rejected."""
        result = self.parser.parse("s", 1990, False)
        assert result is None
    
    def test_invalid_year_with_apostrophe(self):
        """Test that apostrophe format ('90s) is rejected (requires 4-digit year)."""
        result = self.parser.parse("'90s", 1990, False)
        assert result is None
    
    def test_invalid_decade_marker_without_s(self):
        """Test that decade without 's' suffix is rejected."""
        result = self.parser.parse("1990", 1990, False)
        assert result is None
    
    def test_invalid_non_decade_ending(self):
        """Test that year not ending in 0 is rejected."""
        result = self.parser.parse("1985s", 1985, False)
        assert result is None
    
    # Span properties
    
    def test_span_month_day_ranges(self):
        """Test that span covers full year range (Jan 1 - Dec 31)."""
        result = self.parser.parse("1990s", 1990, False)
        assert result is not None
        assert result.start_month == 1
        assert result.start_day == 1
        assert result.end_month == 12
        assert result.end_day == 31
    
    def test_span_precision(self):
        """Test that span precision is YEAR_ONLY."""
        result = self.parser.parse("1990s", 1990, False)
        assert result is not None
        assert result.precision == SpanPrecision.YEAR_ONLY
    
    def test_span_match_type(self):
        """Test that match_type is set correctly."""
        result = self.parser.parse("1990s", 1990, False)
        assert result is not None
        assert "Decade notation" in result.match_type
    
    # Edge cases with different centuries
    
    def test_parse_1000s(self):
        """Test parsing 1000s → 1000-1009."""
        result = self.parser.parse("1000s", 1000, False)
        assert result is not None
        assert result.start_year == 1000
        assert result.end_year == 1009
    
    def test_parse_2020s(self):
        """Test parsing 2020s → 2020-2029."""
        result = self.parser.parse("2020s", 2020, False)
        assert result is not None
        assert result.start_year == 2020
        assert result.end_year == 2029
    
    def test_parse_1700s(self):
        """Test parsing 1700s → 1700-1709."""
        result = self.parser.parse("1700s", 1700, False)
        assert result is not None
        assert result.start_year == 1700
        assert result.end_year == 1709
    
    # Boundary cases
    
    def test_parse_3000s(self):
        """Test parsing 3000s → 3000-3009 (future)."""
        result = self.parser.parse("3000s", 3000, False)
        assert result is not None
        assert result.start_year == 3000
        assert result.end_year == 3009
    
    @pytest.mark.parametrize("decade_text,expected_start,expected_end", [
        ("1000s", 1000, 1009),
        ("1100s", 1100, 1109),
        ("1200s", 1200, 1209),
        ("1300s", 1300, 1309),
        ("1400s", 1400, 1409),
        ("1500s", 1500, 1509),
        ("1600s", 1600, 1609),
        ("1700s", 1700, 1709),
        ("1800s", 1800, 1809),
        ("1900s", 1900, 1909),
        ("1990s", 1990, 1999),
        ("2000s", 2000, 2009),
        ("2010s", 2010, 2019),
        ("2020s", 2020, 2029),
    ])
    def test_all_decade_variations(self, decade_text, expected_start, expected_end):
        """Test parsing various decades across centuries."""
        result = self.parser.parse(decade_text, expected_start, False)
        assert result is not None
        assert result.start_year == expected_start
        assert result.end_year == expected_end
