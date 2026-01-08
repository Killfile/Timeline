"""Tests for ParenthesizedDecadeParser."""

from span_parsing.parenthesized_decade_parser import ParenthesizedDecadeParser


def test_parenthesized_decade_matches_end():
    p = ParenthesizedDecadeParser()
    result = p.parse("Jet Age (1940s)", 1940, False)
    assert result is not None
    assert result.start_year == 1940
    assert result.end_year == 1949
    assert result.start_year_is_bc is False
    assert "1940s" in result.match_type


def test_parenthesized_decade_with_marker_bc():
    p = ParenthesizedDecadeParser()
    result = p.parse("Event (1940s BC)", 1940, False)
    assert result is not None
    assert result.start_year == 1949
    assert result.end_year == 1940
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True


def test_parenthesized_decade_infers_page_bc_when_no_marker():
    p = ParenthesizedDecadeParser()
    result = p.parse("Event (1940s)", 1940, True)
    assert result is not None
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True


def test_parenthesized_decade_not_match_if_not_at_end():
    p = ParenthesizedDecadeParser()
    result = p.parse("Jet Age (1940s) extra", 1940, False)
    assert result is None


def test_parenthesized_decade_with_location():
    p = ParenthesizedDecadeParser()
    result = p.parse("Jazz Era (American, 1940s)", 1940, False)
    assert result is not None
    assert "American" in result.match_type
