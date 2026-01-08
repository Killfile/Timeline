"""Tests for ParenthesizedCircaYearRangeWithLocationParser."""

from span_parsing.parenthesized_circa_year_range_with_location_parser import ParenthesizedCircaYearRangeWithLocationParser
from span_parsing.span import SpanPrecision


def test_parenthesized_circa_matches_end():
    p = ParenthesizedCircaYearRangeWithLocationParser()
    result = p.parse("The Renaissance (Europe, c. 1300 – c. 1601)", 1300, False)
    assert result is not None
    assert result.start_year == 1300
    assert result.end_year == 1601
    assert result.precision == SpanPrecision.CIRCA
    assert "Europe" in result.match_type


def test_parenthesized_circa_propagates_right_marker():
    p = ParenthesizedCircaYearRangeWithLocationParser()
    # Page BC context ensures the range is valid (1600 BC - 1046 BC)
    result = p.parse("Event (Region, c. 1600 – 1046)", 1600, True)
    assert result is not None
    assert result.start_year == 1600
    assert result.end_year == 1046
    assert result.precision == SpanPrecision.CIRCA


def test_parenthesized_circa_propagates_left_marker():
    p = ParenthesizedCircaYearRangeWithLocationParser()
    # Page BC context ensures the range is valid (1600 BC - 1046 BC)
    result = p.parse("Event (Region, 1600 – c. 1046)", 1600, True)
    assert result is not None
    assert result.start_year == 1600
    assert result.end_year == 1046
    assert result.precision == SpanPrecision.CIRCA


def test_parenthesized_circa_infers_page_bc_when_no_markers():
    p = ParenthesizedCircaYearRangeWithLocationParser()
    result = p.parse("Some period (Region, 500 - 400)", 500, True)
    assert result is not None
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True


def test_parenthesized_circa_not_match_if_not_at_end():
    p = ParenthesizedCircaYearRangeWithLocationParser()
    result = p.parse("Some (Region, c. 1300 – c. 1601) extra", 1300, False)
    assert result is None
