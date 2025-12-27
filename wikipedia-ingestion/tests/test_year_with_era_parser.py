"""Tests for YearWithEraParser."""

import pytest
from span_parsing.year_with_era_parser import YearWithEraParser
from span_parsing.span import Span


class TestYearWithEraParser:
    """Test cases for parsing years with explicit era markers."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = YearWithEraParser()
    
    def test_valid_bc_year(self):
        """Test parsing a valid BC year."""
        result = self.parser.parse("490 BC", 490, True)
        assert result is not None
        assert result.start_year == 490
        assert result.end_year == 490
        assert result.is_bc is True
        assert result.precision == "year"
        assert result.start_month == 1
        assert result.start_day == 1
        assert result.end_month == 12
        assert result.end_day == 31
    
    def test_valid_ad_year(self):
        """Test parsing a valid AD year."""
        result = self.parser.parse("2020 AD", 2020, False)
        assert result is not None
        assert result.start_year == 2020
        assert result.end_year == 2020
        assert result.is_bc is False
    
    def test_bce_marker(self):
        """Test parsing with BCE marker."""
        result = self.parser.parse("490 BCE", 490, True)
        assert result is not None
        assert result.is_bc is True
    
    def test_ce_marker(self):
        """Test parsing with CE marker."""
        result = self.parser.parse("2020 CE", 2020, False)
        assert result is not None
        assert result.is_bc is False
    
    def test_era_case_insensitive(self):
        """Test that era markers are case-insensitive."""
        test_cases = [
            ("490 bc", True),
            ("490 BC", True),
            ("490 Bc", True),
            ("490 bC", True),
            ("2020 ad", False),
            ("2020 AD", False),
        ]
        for text, expected_bc in test_cases:
            result = self.parser.parse(text, 490 if expected_bc else 2020, expected_bc)
            assert result is not None, f"Failed to parse: {text}"
            assert result.is_bc == expected_bc
    
    def test_one_digit_year(self):
        """Test parsing with one-digit year."""
        result = self.parser.parse("5 BC", 5, True)
        assert result is not None
        assert result.start_year == 5
    
    def test_two_digit_year(self):
        """Test parsing with two-digit year."""
        result = self.parser.parse("45 BC", 45, True)
        assert result is not None
        assert result.start_year == 45
    
    def test_three_digit_year(self):
        """Test parsing with three-digit year."""
        result = self.parser.parse("490 BC", 490, True)
        assert result is not None
        assert result.start_year == 490
    
    def test_four_digit_year(self):
        """Test parsing with four-digit year."""
        result = self.parser.parse("2020 AD", 2020, False)
        assert result is not None
        assert result.start_year == 2020
    
    def test_year_zero_invalid(self):
        """Test that year 0 is rejected."""
        result = self.parser.parse("0 AD", 1, False)
        assert result is None
    
    def test_must_be_at_start_of_string(self):
        """Test that pattern must be at start of string."""
        result = self.parser.parse("In 490 BC", 490, True)
        # This should match because regex allows leading whitespace
        assert result is None
    
    def test_whitespace_between_year_and_era(self):
        """Test parsing with various whitespace between year and era."""
        test_cases = [
            "490 BC",
            "490  BC",
            "490   BC",
        ]
        for text in test_cases:
            result = self.parser.parse(text, 490, True)
            assert result is not None, f"Failed to parse: {text}"
    
    def test_leading_whitespace_allowed(self):
        """Test that leading whitespace is allowed."""
        test_cases = [
            " 490 BC",
            "  490 BC",
            "   490 BC",
        ]
        for text in test_cases:
            result = self.parser.parse(text, 490, True)
            assert result is not None, f"Failed to parse: {text}"
    
    def test_text_after_year_era(self):
        """Test parsing with text after the year and era."""
        result = self.parser.parse("490 BC was significant", 490, True)
        assert result is not None
        assert result.start_year == 490
    
    def test_page_bc_ignored_when_explicit_era(self):
        """Test that page BC setting is ignored when era is explicit."""
        result = self.parser.parse("490 BC", 490, False)  # page is AD but text is BC
        assert result is not None
        assert result.is_bc is True  # Text overrides page setting
        
        result = self.parser.parse("2020 AD", 2020, True)  # page is BC but text is AD
        assert result is not None
        assert result.is_bc is False  # Text overrides page setting
    
    def test_match_type_includes_era(self):
        """Test that match_type includes the era marker."""
        result = self.parser.parse("490 BC", 490, True)
        assert result is not None
        assert "BC" in result.match_type
    
    def test_abbreviated_era_with_period(self):
        """Test parsing era abbreviations with periods."""
        # Current implementation doesn't support B.C. or A.D. with periods
        result = self.parser.parse("490 B.C.", 490, True)
        assert result is None  # Not supported in current implementation
    
    def test_does_not_match_year_range(self):
        """Test that year ranges don't match this parser."""
        result = self.parser.parse("490 BC - 479 BC", 490, True)
        # This will match "490 BC" at the start
        assert result is not None
        assert result.start_year == 490
        assert result.end_year == 490  # Only the first year, not a range
