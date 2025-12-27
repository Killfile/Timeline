"""Tests for YearRangeParser."""

import pytest
from span_parsing.year_range_parser import YearRangeParser
from span_parsing.span import Span


class TestYearRangeParser:
    """Test cases for parsing year ranges."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = YearRangeParser()
    
    def test_valid_bc_range_explicit(self):
        """Test parsing a valid BC year range with explicit markers."""
        result = self.parser.parse("490 BC - 479 BC", 490, True)
        assert result is not None
        assert result.start_year == 490
        assert result.end_year == 479
        assert result.is_bc is True
        assert result.precision == "year"
        assert result.start_month == 1
        assert result.start_day == 1
        assert result.end_month == 12
        assert result.end_day == 31
    
    def test_valid_ad_range_explicit(self):
        """Test parsing a valid AD year range with explicit markers."""
        result = self.parser.parse("2019 AD - 2021 AD", 2020, False)
        assert result is not None
        assert result.start_year == 2019
        assert result.end_year == 2021
        assert result.is_bc is False
    
    def test_range_with_bce_markers(self):
        """Test parsing with BCE markers."""
        result = self.parser.parse("490 BCE - 479 BCE", 490, True)
        assert result is not None
        assert result.is_bc is True
    
    def test_range_with_ce_markers(self):
        """Test parsing with CE markers."""
        result = self.parser.parse("2019 CE - 2021 CE", 2020, False)
        assert result is not None
        assert result.is_bc is False
    
    def test_range_no_era_uses_page_bc(self):
        """Test that range without era markers uses page BC setting."""
        result = self.parser.parse("490 - 479", 490, True)
        assert result is not None
        assert result.is_bc is True
        
        result = self.parser.parse("2019 - 2021", 2020, False)
        assert result is not None
        assert result.is_bc is False
    
    @pytest.mark.parametrize("dash_char", [
        "–",  # en dash
        "—",  # em dash
        "−",  # minus sign
        "-",  # hyphen-minus
    ])
    def test_various_dash_styles(self, dash_char):
        """Test parsing with different dash characters."""
        text = f"490 BC {dash_char} 479 BC"
        result = self.parser.parse(text, 490, True)
        assert result is not None, f"Failed to parse with dash: {dash_char}"
    
    def test_mixed_bc_ad_invalid(self):
        """Test that mixing BC and AD is rejected."""
        result = self.parser.parse("490 BC - 479 AD", 490, False)
        assert result is None
    
    def test_era_case_insensitive(self):
        """Test that era markers are case-insensitive."""
        test_cases = [
            "490 bc - 479 bc",
            "490 BC - 479 BC",
            "490 Bc - 479 bC",
        ]
        for text in test_cases:
            result = self.parser.parse(text, 490, True)
            assert result is not None, f"Failed to parse: {text}"
    
    def test_one_digit_years(self):
        """Test parsing with one-digit years."""
        result = self.parser.parse("9 BC - 5 BC", 5, True)
        assert result is not None
        assert result.start_year == 9
        assert result.end_year == 5
    
    def test_two_digit_years(self):
        """Test parsing with two-digit years."""
        result = self.parser.parse("50 BC - 45 BC", 45, True)
        assert result is not None
        assert result.start_year == 50
        assert result.end_year == 45
    
    def test_three_digit_years(self):
        """Test parsing with three-digit years."""
        result = self.parser.parse("490 BC - 479 BC", 490, True)
        assert result is not None
        assert result.start_year == 490
        assert result.end_year == 479
    
    def test_four_digit_years(self):
        """Test parsing with four-digit years."""
        result = self.parser.parse("2019 AD - 2021 AD", 2020, False)
        assert result is not None
        assert result.start_year == 2019
        assert result.end_year == 2021
    
    def test_year_zero_invalid(self):
        """Test that year 0 is rejected."""
        result = self.parser.parse("1 BC - 0 AD", 1, True)
        assert result is None
    
    def test_whitespace_variations(self):
        """Test parsing with various whitespace patterns."""
        test_cases = [
            "490  BC  -  479  BC",
            "490 BC- 479 BC",
            "490 BC -479 BC",
        ]
        for text in test_cases:
            result = self.parser.parse(text, 490, True)
            assert result is not None, f"Failed to parse: {text}"
    
    def test_embedded_in_longer_text(self):
        """Test parsing when range is embedded in longer text."""
        result = self.parser.parse("War from 490 BC - 479 BC ended", 490, True)
        assert result is not None
    
    def test_era_on_first_year_only(self):
        """Test parsing with era marker on first year only."""
        result = self.parser.parse("490 BC - 479", 490, True)
        assert result is not None
        assert result.is_bc is True
    
    def test_era_on_second_year_only(self):
        """Test parsing with era marker on second year only."""
        result = self.parser.parse("490 - 479 BC", 490, True)
        assert result is not None
        assert result.is_bc is True
    
    def test_same_year_range(self):
        """Test parsing range where start and end are the same year."""
        result = self.parser.parse("490 BC - 490 BC", 490, True)
        assert result is not None
        assert result.start_year == 490
        assert result.end_year == 490
