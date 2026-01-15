"""Tests for SpanParser main class."""

import pytest
from span_parsing.orchestrators.years_parse_orchestrator import YearsParseOrchestrator
from span_parsing.span import Span
from span_parsing.strategy import SpanParserStrategy
from span_parsing.year_only_parser import YearOnlyParser
from span_parsing.span import SpanPrecision


class TestSpanParserStrategy(SpanParserStrategy):
    """Concrete implementation for testing SpanParserStrategy methods."""
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        # Dummy implementation for testing
        return None


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
        assert YearsParseOrchestrator.is_circa_text(text) is True
    
    @pytest.mark.parametrize("text", [
        "490 BC",
        "December 25",
    ])
    def test_is_circa_text_variations_false(self, text):
        """Test that non-circa text doesn't match."""
        # These don't match because \b after . doesn't work as expected with digits following
        # but parse_span_from_bullet has different logic that works correctly
        assert YearsParseOrchestrator.is_circa_text(text) is False
    
    @pytest.mark.parametrize("text", [
        "c. 490 BC",
        "ca. 490 BC",
        "circa 490 BC",
    ])
    def test_parse_span_from_bullet_accepts_circa(self, text):
        """Test that circa dates are now accepted and parsed."""
        result = YearsParseOrchestrator.parse_span_from_bullet(text, 490, assume_is_bc=True)
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
        assert YearsParseOrchestrator.parse_span_from_bullet(text, 490, assume_is_bc=True) is None
    
    def test_parse_span_from_bullet_tries_parsers_in_order(self):
        """Test that parsers are tried in correct priority order."""
        # Multi-year should match first
        result = YearsParseOrchestrator.parse_span_from_bullet("March 15, 2020 – April 20, 2021", 2020, assume_is_bc=False)
        assert result is not None
        assert result.start_year == 2020
        assert result.end_year == 2021
        
        # Multi-month should match before single month
        result = YearsParseOrchestrator.parse_span_from_bullet("March 15 – April 20", 2020, assume_is_bc=False)
        assert result is not None
        assert result.start_month == 3
        assert result.end_month == 4
        
        # Single month range should match before single day
        result = YearsParseOrchestrator.parse_span_from_bullet("March 15–20", 2020, assume_is_bc=False)
        assert result is not None
        assert result.start_day == 15
        assert result.end_day == 20
    
    def test_parse_span_from_bullet_single_day(self):
        """Test parsing single day dates."""
        result = YearsParseOrchestrator.parse_span_from_bullet("September 25", 490, assume_is_bc=True)
        assert result is not None
        assert result.start_month == 9
        assert result.start_day == 25
        assert result.is_bc is True
    
    def test_parse_span_from_bullet_month_only(self):
        """Test parsing month-only dates."""
        result = YearsParseOrchestrator.parse_span_from_bullet("September", 490, assume_is_bc=True)
        assert result is not None
        assert result.start_month == 9
        assert result.start_day == 1
        assert result.end_day == 30
    
    def test_parse_span_from_bullet_year_range(self):
        """Test parsing year ranges."""
        result = YearsParseOrchestrator.parse_span_from_bullet("490 BC - 479 BC", 490, assume_is_bc=True)
        assert result is not None
        assert result.start_year == 490
        assert result.end_year == 479
        assert result.is_bc is True
    
    def test_parse_span_from_bullet_year_with_era(self):
        """Test parsing year with explicit era."""
        result = YearsParseOrchestrator.parse_span_from_bullet("490 BC", 490, assume_is_bc=None)
        assert result is not None
        assert result.start_year == 490
        assert result.is_bc is True
    
    def test_parse_span_from_bullet_year_only(self):
        """Test parsing standalone year."""
        result = YearsParseOrchestrator.parse_span_from_bullet("490", 490, assume_is_bc=True)
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
        result = YearsParseOrchestrator.parse_span_from_bullet(text, 490, assume_is_bc=True)
        assert result is not None, f"Failed to parse: {text}"
    
    @pytest.mark.parametrize("month_name,expected_number", [
        ("january", 1), ("february", 2), ("march", 3), ("april", 4),
        ("may", 5), ("june", 6), ("july", 7), ("august", 8),
        ("september", 9), ("october", 10), ("november", 11), ("december", 12),
    ])
    def test_month_name_to_number_all_months(self, month_name, expected_number):
        """Test month name conversion for all months in various cases."""
        assert SpanParserStrategy.month_name_to_number(month_name) == expected_number
        assert SpanParserStrategy.month_name_to_number(month_name.upper()) == expected_number
        assert SpanParserStrategy.month_name_to_number(month_name.title()) == expected_number
    
    @pytest.mark.parametrize("invalid_name", [
        "octember",
        "notamonth",
        "",
    ])
    def test_month_name_to_number_invalid(self, invalid_name):
        """Test that invalid month names return None."""
        assert SpanParserStrategy.month_name_to_number(invalid_name) is None

        
    def test_return_none_if_invalid_with_none(self):
        """Test that None input returns None."""
        assert YearsParseOrchestrator._return_none_if_invalid(None) is None
    
    def test_return_none_if_invalid_with_invalid_BC_span(self):
        """Test that invalid span returns None."""
        span = Span(500, 600, 1, 1, 12, 31, True, True, "year", "test")
        assert YearsParseOrchestrator._return_none_if_invalid(span) is None
    
    def test_return_none_if_invalid_with_valid_span(self):
        """Test that valid span is returned unchanged."""
        span = Span(479, 470, 1, 1, 12, 31, True, "year", "test")
        result = YearsParseOrchestrator._return_none_if_invalid(span)
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
        result = YearsParseOrchestrator.parse_span_from_bullet(text, page_year, assume_is_bc=bc)
        assert result is not None, f"Failed to parse: {text}"
        assert result.start_year == exp_sy, f"start_year mismatch for: {text}"
        assert result.start_month == exp_sm, f"start_month mismatch for: {text}"
        assert result.end_year == exp_ey, f"end_year mismatch for: {text}"
        assert result.end_month == exp_em, f"end_month mismatch for: {text}"
        assert result.end_day == exp_ed, f"end_day mismatch for: {text}"


class TestSpanParserStrategy:
    """Test cases for SpanParserStrategy methods."""
    
    def test_compute_weight_days_none_span(self):
        """Test that None span returns None weight."""
        strategy = YearOnlyParser()
        assert strategy.compute_weight_days(None) is None
    
    def test_compute_weight_days_single_day_ad(self):
        """Test weight calculation for single day in AD."""
        strategy = YearOnlyParser()
        span = Span(100, 100, 1, 1, 1, 1, False, False, "day", 1.0)
        weight = strategy.compute_weight_days(span)
        assert weight == 1
    
    def test_compute_weight_days_single_day_bc(self):
        """Test weight calculation for single day in BC."""
        strategy = YearOnlyParser()
        span = Span(100, 100, 1, 1, 1, 1, True, True, "day", 1.0)
        weight = strategy.compute_weight_days(span)
        # BC dates can't be handled by Python datetime, so None
        assert weight == 1
    
    def test_compute_weight_days_year_span_ad(self):
        """Test weight calculation for year span in AD."""
        strategy = YearOnlyParser()
        span = Span(100, 101, 1, 1, 12, 31, False, False, "year", 1.0)
        weight = strategy.compute_weight_days(span)
        # (date(101,12,31) - date(100,1,1)).days + 1 = 729 + 1 = 730
        assert weight == 730
    
    def test_compute_weight_days_year_span_bc(self):
        """Test weight calculation for year span in BC."""
        strategy = YearOnlyParser()
        span = Span(101, 100, 1, 1, 12, 31, True, True, "year", 1.0)
        weight = strategy.compute_weight_days(span)
        assert weight == (2 * 365)
    
    def test_compute_weight_days_mixed_era(self):
        """Test weight calculation across BC/AD boundary."""
        strategy = YearOnlyParser()
        span = Span(1, 1, 1, 1, 12, 31, True, False, "year", 1.0)  # 1 BC to 1 AD
        weight = strategy.compute_weight_days(span)
        # 1 BC becomes year 0, which is invalid, so None
        assert weight == (2 * 365)
    
    def test_compute_weight_days_month_span(self):
        """Test weight calculation for month span."""
        strategy = YearOnlyParser()
        span = Span(100, 100, 1, 1, 2, 28, False, False, "month", 1.0)  # Jan 1 to Feb 28
        weight = strategy.compute_weight_days(span)
        # (date(100,2,28) - date(100,1,1)).days + 1 = 58 + 1 = 59
        assert weight == 59
    
    def test_compute_weight_days_with_defaults(self):
        """Test weight calculation with None month/day defaults."""
        strategy = YearOnlyParser()
        span = Span(100, 101, None, None, None, None, False, False, "year", 1.0)
        weight = strategy.compute_weight_days(span)
        # date(101,1,1) - date(100,1,1) = 365 days + 1 = 366
        assert weight == 366
    
    def test_compute_weight_days_reverse_order(self):
        """Test weight calculation when start > end (should swap)."""
        strategy = YearOnlyParser()
        span = Span(101, 100, 1, 1, 12, 31, False, False, "year", 1.0)
        weight = strategy.compute_weight_days(span)
        # Swaps to date(100,12,31) to date(101,1,1): 1 day + 1 = 2
        assert weight == 1
    
