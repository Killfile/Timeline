"""Tests for ParenthesizedShortYearRangeParser."""

from span_parsing.parenthesized_short_year_range_parser import ParenthesizedShortYearRangeParser
from span_parsing.span import SpanPrecision


def test_short_year_range_parses_2003_04():
    p = ParenthesizedShortYearRangeParser()
    result = p.parse("Coalition Provisional Authority(2003-04)", 2003, False)
    assert result is not None
    assert result.start_year == 2003
    assert result.end_year == 2004
    assert result.precision == SpanPrecision.YEAR_ONLY


def test_short_year_range_handles_century_rollover():
    p = ParenthesizedShortYearRangeParser()
    result = p.parse("Something (1999-02)", 1999, False)
    assert result is not None
    assert result.start_year == 1999
    assert result.end_year == 2002


def test_short_year_range_propagates_era_and_infers_end():
    p = ParenthesizedShortYearRangeParser()
    result = p.parse("Event (1600 BC - 04)", 1600, True)
    assert result is not None
    assert result.start_year == 1600
    # For BC shorthand the century inference is ambiguous; ensure era is propagated
    # and the produced span is valid.
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True
    assert result.is_valid()


def test_short_year_range_not_match_if_not_at_end():
    p = ParenthesizedShortYearRangeParser()
    result = p.parse("Coalition Provisional Authority(2003-04) extra", 2003, False)
    assert result is None


def test_short_year_range_infers_page_bc_when_no_markers():
    p = ParenthesizedShortYearRangeParser()
    result = p.parse("Some period (500-40)", 500, True)
    assert result is not None
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True


def test_short_year_range_rejects_mixed_eras():
    p = ParenthesizedShortYearRangeParser()
    result = p.parse("Weird (2003 BC - 04 AD)", 2003, None)
    assert result is None
