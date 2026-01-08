"""Tests for ParenthesizedYearRangeParser."""

from span_parsing.parenthesized_year_range_parser import ParenthesizedYearRangeParser


def test_parenthesized_matches_end():
    parser = ParenthesizedYearRangeParser()
    result = parser.parse("Shang dynasty (1600–1046 BC)", 1600, True)
    assert result is not None
    assert result.start_year == 1600
    assert result.end_year == 1046
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True


def test_parenthesized_not_match_if_not_at_end():
    parser = ParenthesizedYearRangeParser()
    result = parser.parse("Shang dynasty (1600–1046 BC) extra", 1600, True)
    assert result is None


def test_parenthesized_infers_page_bc_when_no_markers():
    parser = ParenthesizedYearRangeParser()
    result = parser.parse("Some period (500 - 400)", 500, True)
    assert result is not None
    assert result.start_year == 500
    assert result.end_year == 400
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True


def test_parenthesized_propagates_right_marker():
    parser = ParenthesizedYearRangeParser()
    result = parser.parse("Period (1600–1046 BC)", 1600, False)
    assert result is not None
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True


def test_parenthesized_propagates_left_marker():
    parser = ParenthesizedYearRangeParser()
    result = parser.parse("Period (1600 BC – 1046)", 1600, False)
    assert result is not None
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is False
