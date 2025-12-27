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
    
    @pytest.mark.parametrize("era,expected_bc", [
        ("BC", True),
        ("BCE", True),
        ("AD", False),
        ("CE", False),
    ])
    def test_era_markers(self, era, expected_bc):
        """Test parsing with different era markers."""
        year = 490 if expected_bc else 2020
        result = self.parser.parse(f"{year} {era}", year, expected_bc)
        assert result is not None
        assert result.is_bc is expected_bc
    
    @pytest.mark.parametrize("text,expected_bc", [
        ("490 bc", True),
        ("490 BC", True),
        ("490 Bc", True),
        ("490 bC", True),
        ("2020 ad", False),
        ("2020 AD", False),
    ])
    def test_era_case_insensitive(self, text, expected_bc):
        """Test that era markers are case-insensitive."""
        result = self.parser.parse(text, 490 if expected_bc else 2020, expected_bc)
        assert result is not None, f"Failed to parse: {text}"
        assert result.is_bc == expected_bc
    
    @pytest.mark.parametrize("text,expected_year", [
        ("5 BC", 5),
        ("45 BC", 45),
        ("490 BC", 490),
        ("2020 AD", 2020),
    ])
    def test_various_digit_years(self, text, expected_year):
        """Test parsing with one, two, three, and four-digit years."""
        is_bc = "BC" in text
        result = self.parser.parse(text, expected_year, is_bc)
        assert result is not None
        assert result.start_year == expected_year
    
    def test_year_zero_invalid(self):
        """Test that year 0 is rejected."""
        result = self.parser.parse("0 AD", 1, False)
        assert result is None
    
    def test_must_be_at_start_of_string(self):
        """Test that pattern must be at start of string."""
        result = self.parser.parse("In 490 BC", 490, True)
        assert result is None
    
    @pytest.mark.parametrize("text", [
        "490 BC",
        "490  BC",
        "490   BC",
    ])
    def test_whitespace_between_year_and_era(self, text):
        """Test parsing with various whitespace between year and era."""
        result = self.parser.parse(text, 490, True)
        assert result is not None, f"Failed to parse: {text}"
    
    @pytest.mark.parametrize("text", [
        " 490 BC",
        "  490 BC",
        "   490 BC",
    ])
    def test_leading_whitespace_allowed(self, text):
        """Test that leading whitespace is allowed."""
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
