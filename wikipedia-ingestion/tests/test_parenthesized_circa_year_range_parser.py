"""Tests for ParenthesizedCircaYearRangeParser."""

from span_parsing.parenthesized_circa_year_range_parser import ParenthesizedCircaYearRangeParser
from span_parsing.span import SpanPrecision


def test_parenthesized_circa_matches_end():
    p = ParenthesizedCircaYearRangeParser()
    result = p.parse("Bronze Age (c. 3000 BC - c. 1050 BC)", 3000, False)
    assert result is not None
    assert result.start_year == 3000
    assert result.end_year == 1050
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True
    assert result.precision == SpanPrecision.CIRCA


def test_parenthesized_circa_propagates_right_marker():
    p = ParenthesizedCircaYearRangeParser()
    result = p.parse("Event (c. 1600 - 1046)", 1600, True)
    assert result is not None
    assert result.start_year == 1600
    assert result.end_year == 1046
    assert result.precision == SpanPrecision.CIRCA


def test_parenthesized_circa_propagates_left_marker():
    p = ParenthesizedCircaYearRangeParser()
    result = p.parse("Event (1600 - c. 1046)", 1600, True)
    assert result is not None
    assert result.start_year == 1600
    assert result.end_year == 1046
    assert result.precision == SpanPrecision.CIRCA


def test_parenthesized_circa_infers_page_bc_when_no_markers():
    p = ParenthesizedCircaYearRangeParser()
    result = p.parse("Some period (500 - 400)", 500, True)
    assert result is not None
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True


def test_parenthesized_circa_not_match_if_not_at_end():
    p = ParenthesizedCircaYearRangeParser()
    result = p.parse("Bronze Age (c. 3000 - c. 1050) extra", 3000, False)
    assert result is None
