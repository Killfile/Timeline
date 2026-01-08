"""Tests for ParenthesizedYearParser."""

from span_parsing.parenthesized_year_parser import ParenthesizedYearParser
from span_parsing.span import SpanPrecision


def test_parenthesized_year_matches_end():
    p = ParenthesizedYearParser()
    result = p.parse("Hashemite Arab Federation(1958)", 1958, False)
    assert result is not None
    assert result.start_year == 1958
    assert result.end_year == 1958
    assert result.precision == SpanPrecision.YEAR_ONLY


def test_parenthesized_year_infers_page_bc_when_no_era_markers():
    p = ParenthesizedYearParser()
    result = p.parse("Some period (500)", 500, True)
    assert result is not None
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True


def test_parenthesized_year_accepts_era_marker():
    p = ParenthesizedYearParser()
    result = p.parse("Event (490 BC)", 490, None)
    assert result is not None
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True


def test_parenthesized_year_accepts_circa():
    p = ParenthesizedYearParser()
    result = p.parse("Event (c. 1600)", 1600, False)
    assert result is not None
    assert result.precision == SpanPrecision.CIRCA


def test_parenthesized_year_not_match_if_not_at_end():
    p = ParenthesizedYearParser()
    result = p.parse("Hashemite Arab Federation(1958) extra", 1958, False)
    assert result is None
