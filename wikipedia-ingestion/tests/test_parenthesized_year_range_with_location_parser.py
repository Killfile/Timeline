"""Tests for ParenthesizedYearRangeWithLocationParser."""

from span_parsing.parenthesized_year_range_with_location_parser import ParenthesizedYearRangeWithLocationParser


def test_parenthesized_location_matches_end():
    p = ParenthesizedYearRangeWithLocationParser()
    result = p.parse("British Interregnum (British Isles, 1649–1660)", 1649, False)
    assert result is not None
    assert result.start_year == 1649
    assert result.end_year == 1660
    assert result.start_year_is_bc is False
    assert result.end_year_is_bc is False
    assert "British Isles" in result.match_type


def test_parenthesized_location_multiple_commas():
    p = ParenthesizedYearRangeWithLocationParser()
    result = p.parse("Period (City, Region, 1900–1910)", 1900, False)
    assert result is not None
    assert result.start_year == 1900
    assert result.end_year == 1910


def test_parenthesized_location_not_match_if_not_at_end():
    p = ParenthesizedYearRangeWithLocationParser()
    result = p.parse("Period (British Isles, 1649–1660) extra", 1649, False)
    assert result is None


def test_parenthesized_location_propagates_right_marker():
    p = ParenthesizedYearRangeWithLocationParser()
    result = p.parse("Event (British Isles, 1600–1046 BC)", 1600, False)
    assert result is not None
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True


def test_parenthesized_location_propagates_left_marker():
    p = ParenthesizedYearRangeWithLocationParser()
    result = p.parse("Event (British Isles, 1600 BC – 1046)", 1600, False)
    assert result is not None
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is False


def test_parenthesized_location_infers_page_bc_when_no_markers():
    p = ParenthesizedYearRangeWithLocationParser()
    result = p.parse("Some period (British Isles, 500 - 400)", 500, True)
    assert result is not None
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True
