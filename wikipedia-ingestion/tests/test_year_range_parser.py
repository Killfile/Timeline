"""Tests for YearRangeParser."""

import pytest
from span_parsing.year_range_parser import YearRangeParser
from span_parsing.span import Span, SpanPrecision


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
        assert result.precision == SpanPrecision.YEAR_ONLY
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
    
    @pytest.mark.parametrize("era", [
        "BCE",
        "CE",
    ])
    def test_range_with_era_markers(self, era):
        """Test parsing with BCE and CE markers."""
        is_bc = era in ("BC", "BCE")
        year = 490 if is_bc else 2020
        result = self.parser.parse(f"{year} {era} - {year-1 if is_bc else year+1} {era}", year, is_bc)
        assert result is not None
        assert result.is_bc is is_bc
    
    @pytest.mark.parametrize("page_bc,expected_bc", [
        (True, True),
        (False, False),
    ])
    def test_range_no_era_uses_page_bc(self, page_bc, expected_bc):
        """Test that range without era markers uses page BC setting."""
        year = 490 if page_bc else 2020
        result = self.parser.parse(f"{year} - {year-1 if page_bc else year+1}", year, page_bc)
        assert result is not None
        assert result.is_bc is expected_bc
    
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
    
    @pytest.mark.parametrize("text", [
        "490 bc - 479 bc",
        "490 BC - 479 BC",
        "490 Bc - 479 bC",
    ])
    def test_era_case_insensitive(self, text):
        """Test that era markers are case-insensitive."""
        result = self.parser.parse(text, 490, True)
        assert result is not None, f"Failed to parse: {text}"
    
    @pytest.mark.parametrize("text,expected_start,expected_end", [
        ("9 BC - 5 BC", 9, 5),
        ("50 BC - 45 BC", 50, 45),
        ("490 BC - 479 BC", 490, 479),
        ("2019 AD - 2021 AD", 2019, 2021),
    ])
    def test_various_digit_year_ranges(self, text, expected_start, expected_end):
        """Test parsing with one, two, three, and four-digit years."""
        is_bc = "BC" in text
        year = expected_start if is_bc else expected_start
        result = self.parser.parse(text, year, is_bc)
        assert result is not None
        assert result.start_year == expected_start
        assert result.end_year == expected_end
    
    def test_year_zero_invalid(self):
        """Test that year 0 is rejected."""
        result = self.parser.parse("1 BC - 0 AD", 1, True)
        assert result is None
    
    @pytest.mark.parametrize("text", [
        "490  BC  -  479  BC",
        "490 BC- 479 BC",
        "490 BC -479 BC",
    ])
    def test_whitespace_variations(self, text):
        """Test parsing with various whitespace patterns."""
        result = self.parser.parse(text, 490, True)
        assert result is not None, f"Failed to parse: {text}"
    
    def test_embedded_in_longer_text(self):
        """Test parsing when range is embedded in longer text."""
        result = self.parser.parse("War from 490 BC - 479 BC ended", 490, True)
        assert result is not None
    
    @pytest.mark.parametrize("text,expected_bc", [
        ("490 BC - 479", True),
        ("490 - 479 BC", True),
    ])
    def test_era_on_one_year_only(self, text, expected_bc):
        """Test parsing with era marker on only one year."""
        result = self.parser.parse(text, 490, True)
        assert result is not None
        assert result.is_bc is expected_bc
    
    def test_same_year_range(self):
        """Test parsing range where start and end are the same year."""
        result = self.parser.parse("490 BC - 490 BC", 490, True)
        assert result is not None
        assert result.start_year == 490
        assert result.end_year == 490
