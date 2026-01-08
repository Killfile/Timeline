"""Tests for ParenthesizedCenturyWithLocationParser."""

from span_parsing.parenthesized_century_with_location_parser import ParenthesizedCenturyWithLocationParser


def test_parenthesized_century_single():
    p = ParenthesizedCenturyWithLocationParser()
    result = p.parse("Protestant Reformation (Europe, 16th century)", 1500, False)
    assert result is not None
    assert result.start_year == 1501
    assert result.end_year == 1600
    assert result.start_year_is_bc is False
    assert "Europe" in result.match_type


def test_parenthesized_century_range():
    p = ParenthesizedCenturyWithLocationParser()
    result = p.parse("Classicism (Europe, 16th – 18th centuries)", 1500, False)
    assert result is not None
    assert result.start_year == 1501
    assert result.end_year == 1800


def test_parenthesized_century_not_match_if_not_at_end():
    p = ParenthesizedCenturyWithLocationParser()
    result = p.parse("Classicism (Europe, 16th century) extra", 1500, False)
    assert result is None


def test_parenthesized_century_propagates_markers():
    p = ParenthesizedCenturyWithLocationParser()
    result = p.parse("Event (Region, 16th century BC)", 1500, False)
    assert result is not None
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True


def test_parenthesized_century_range_propagates_right_marker():
    p = ParenthesizedCenturyWithLocationParser()
    result = p.parse("Event (Region, 16th – 18th centuries BC)", 1500, False)
    assert result is not None
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True
