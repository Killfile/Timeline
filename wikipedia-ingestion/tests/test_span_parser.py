"""Tests for SpanParser main class."""

import pytest
from span_parsing import SpanParser, Span


class TestSpanParser:
    """Test cases for the main SpanParser class."""
    
    @pytest.mark.parametrize("text", [
        "c. 500 BC",
        "ca. 500 BC",
        "circa 500 BC",
        "  c. 500 BC",
        "C. 500 BC",
        "CIRCA 500 BC",
    ])
    def test_is_circa_text_variations_true(self, text):
        """Test detection of circa text in various formats that should match."""
        assert SpanParser.is_circa_text(text) is True
    
    @pytest.mark.parametrize("text", [
        "490 BC",
        "December 25",
    ])
    def test_is_circa_text_variations_false(self, text):
        """Test that non-circa text doesn't match."""
        # These don't match because \b after . doesn't work as expected with digits following
        # but parse_span_from_bullet has different logic that works correctly
        assert SpanParser.is_circa_text(text) is False
    
    @pytest.mark.parametrize("text", [
        "c. 490 BC",
        "ca. 490 BC",
        "circa 490 BC",
    ])
    def test_parse_span_from_bullet_accepts_circa(self, text):
        """Test that circa dates are now accepted and parsed."""
        result = SpanParser.parse_span_from_bullet(text, 490, assume_is_bc=True)
        assert result is not None
        assert result.start_year == 490
        assert result.is_bc is True
        assert "circa" in result.match_type.lower()
    
    @pytest.mark.parametrize("text", [
        "",
        None,
    ])
    def test_parse_span_from_bullet_empty_text(self, text):
        """Test that empty text returns None."""
        assert SpanParser.parse_span_from_bullet(text, 490, assume_is_bc=True) is None
    
    def test_parse_span_from_bullet_tries_parsers_in_order(self):
        """Test that parsers are tried in correct priority order."""
        # Multi-year should match first
        result = SpanParser.parse_span_from_bullet("March 15, 2020 – April 20, 2021", 2020, assume_is_bc=False)
        assert result is not None
        assert result.start_year == 2020
        assert result.end_year == 2021
        
        # Multi-month should match before single month
        result = SpanParser.parse_span_from_bullet("March 15 – April 20", 2020, assume_is_bc=False)
        assert result is not None
        assert result.start_month == 3
        assert result.end_month == 4
        
        # Single month range should match before single day
        result = SpanParser.parse_span_from_bullet("March 15–20", 2020, assume_is_bc=False)
        assert result is not None
        assert result.start_day == 15
        assert result.end_day == 20
    
    def test_parse_span_from_bullet_single_day(self):
        """Test parsing single day dates."""
        result = SpanParser.parse_span_from_bullet("September 25", 490, assume_is_bc=True)
        assert result is not None
        assert result.start_month == 9
        assert result.start_day == 25
        assert result.is_bc is True
    
    def test_parse_span_from_bullet_month_only(self):
        """Test parsing month-only dates."""
        result = SpanParser.parse_span_from_bullet("September", 490, assume_is_bc=True)
        assert result is not None
        assert result.start_month == 9
        assert result.start_day == 1
        assert result.end_day == 30
    
    def test_parse_span_from_bullet_year_range(self):
        """Test parsing year ranges."""
        result = SpanParser.parse_span_from_bullet("490 BC - 479 BC", 490, assume_is_bc=True)
        assert result is not None
        assert result.start_year == 490
        assert result.end_year == 479
        assert result.is_bc is True
    
    def test_parse_span_from_bullet_year_with_era(self):
        """Test parsing year with explicit era."""
        result = SpanParser.parse_span_from_bullet("490 BC", 490, assume_is_bc=None)
        assert result is not None
        assert result.start_year == 490
        assert result.is_bc is True
    
    def test_parse_span_from_bullet_year_only(self):
        """Test parsing standalone year."""
        result = SpanParser.parse_span_from_bullet("490", 490, assume_is_bc=True)
        assert result is not None
        assert result.start_year == 490
        assert result.is_bc is True
    
    @pytest.mark.parametrize("text", [
        "490 – 479 BC",  # en dash
        "490 — 479 BC",  # em dash
        "490 − 479 BC",  # minus
        "490 - 479 BC",  # hyphen
    ])
    def test_dash_normalization(self, text):
        """Test that various dash characters are normalized."""
        result = SpanParser.parse_span_from_bullet(text, 490, assume_is_bc=True)
        assert result is not None, f"Failed to parse: {text}"
    
    @pytest.mark.parametrize("month_name,expected_number", [
        ("january", 1), ("february", 2), ("march", 3), ("april", 4),
        ("may", 5), ("june", 6), ("july", 7), ("august", 8),
        ("september", 9), ("october", 10), ("november", 11), ("december", 12),
    ])
    def test_month_name_to_number_all_months(self, month_name, expected_number):
        """Test month name conversion for all months in various cases."""
        assert SpanParser.month_name_to_number(month_name) == expected_number
        assert SpanParser.month_name_to_number(month_name.upper()) == expected_number
        assert SpanParser.month_name_to_number(month_name.title()) == expected_number
    
    @pytest.mark.parametrize("invalid_name", [
        "octember",
        "notamonth",
        "",
    ])
    def test_month_name_to_number_invalid(self, invalid_name):
        """Test that invalid month names return None."""
        assert SpanParser.month_name_to_number(invalid_name) is None
    
    @pytest.mark.parametrize("span_kwargs,expected_valid", [
        ({"start_year": 490, "end_year": 490, "start_month": 9, "start_day": 25, "end_month": 9, "end_day": 25, "is_bc": True, "precision": "day", "match_type": "test"}, True),
        ({"start_year": 490, "end_year": 490, "start_month": 9, "start_day": 25, "end_month": 9, "end_day": 28, "is_bc": True, "precision": "day", "match_type": "test"}, True),
        ({"start_year": 490, "end_year": 490, "start_month": 9, "start_day": 1, "end_month": 10, "end_day": 31, "is_bc": True, "precision": "month", "match_type": "test"}, True),
        ({"start_year": 490, "end_year": 479, "start_month": 1, "start_day": 1, "end_month": 12, "end_day": 31, "is_bc": True, "precision": "year", "match_type": "test"}, True),
    ])
    def test_validate_span_normal_BC_dates(self, span_kwargs, expected_valid):
        """Test validation of normal date spans."""
        span = Span(**span_kwargs)
        assert SpanParser._validate_span(span) is expected_valid
    
    @pytest.mark.parametrize("span_kwargs,is_bc", [
        ({"start_year": 479, "end_year": 490, "start_month": 1, "start_day": 1, "end_month": 12, "end_day": 31, "precision": "year", "match_type": "test"}, True),
        ({"start_year": 490, "end_year": 479, "start_month": 1, "start_day": 1, "end_month": 12, "end_day": 31, "precision": "year", "match_type": "test"}, False),
    ])
    def test_validate_span_reversed_years(self, span_kwargs, is_bc):
        """Test that reversed years are invalid in both BC and AD."""
        span = Span(**span_kwargs, is_bc=is_bc)
        assert SpanParser._validate_span(span) is False
    
    def test_validate_span_reversed_months(self):
        """Test that reversed months in same year are invalid."""
        span = Span(490, 490, 10, 1, 9, 30, True, "month", "test")
        assert SpanParser._validate_span(span) is False
    
    def test_validate_span_reversed_days(self):
        """Test that reversed days in same month are invalid."""
        span = Span(490, 490, 9, 28, 9, 25, True, "day", "test")
        assert SpanParser._validate_span(span) is False
    
    @pytest.mark.parametrize("span_kwargs", [
        {"start_year": 0, "end_year": 0, "start_month": 1, "start_day": 1, "end_month": 12, "end_day": 31, "is_bc": True, "precision": "year", "match_type": "test"},
        {"start_year": 1, "end_year": 0, "start_month": 1, "start_day": 1, "end_month": 12, "end_day": 31, "is_bc": True, "precision": "year", "match_type": "test"},
        {"start_year": 0, "end_year": 1, "start_month": 1, "start_day": 1, "end_month": 12, "end_day": 31, "is_bc": True, "precision": "year", "match_type": "test"},
    ])
    def test_validate_span_year_zero(self, span_kwargs):
        """Test that year 0 is invalid."""
        span = Span(**span_kwargs)
        assert SpanParser._validate_span(span) is False
    
    def test_return_none_if_invalid_with_none(self):
        """Test that None input returns None."""
        assert SpanParser._return_none_if_invalid(None) is None
    
    def test_return_none_if_invalid_with_invalid_BC_span(self):
        """Test that invalid span returns None."""
        span = Span(500, 600, 1, 1, 12, 31, True, "year", "test")
        assert SpanParser._return_none_if_invalid(span) is None
    
    def test_return_none_if_invalid_with_valid_span(self):
        """Test that valid span is returned unchanged."""
        span = Span(479, 470, 1, 1, 12, 31, True, "year", "test")
        result = SpanParser._return_none_if_invalid(span)
        assert result is span
        assert result.start_year == 479
    
    @pytest.mark.parametrize("text,page_year,bc,exp_sy,exp_sm,exp_ey,exp_em,exp_ed", [
        ("September 25, 490 BC", 490, True, 490, 9, 490, 9, 25),
        ("September 25–28", 490, True, 490, 9, 490, 9, 28),
        ("September 28 – October 2", 490, True, 490, 9, 490, 10, 2),
        ("September", 490, True, 490, 9, 490, 9, 30),
        ("490 BC - 479 BC", 490, True, 490, 1, 479, 12, 31),
        ("490 BC", 490, None, 490, 1, 490, 12, 31),
        ("490", 490, True, 490, 1, 490, 12, 31),
    ])
    def test_integration_complex_dates(self, text, page_year, bc, exp_sy, exp_sm, exp_ey, exp_em, exp_ed):
        """Test integration with various complex date formats."""
        result = SpanParser.parse_span_from_bullet(text, page_year, assume_is_bc=bc)
        assert result is not None, f"Failed to parse: {text}"
        assert result.start_year == exp_sy, f"start_year mismatch for: {text}"
        assert result.start_month == exp_sm, f"start_month mismatch for: {text}"
        assert result.end_year == exp_ey, f"end_year mismatch for: {text}"
        assert result.end_month == exp_em, f"end_month mismatch for: {text}"
        assert result.end_day == exp_ed, f"end_day mismatch for: {text}"
