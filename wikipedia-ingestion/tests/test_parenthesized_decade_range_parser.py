"""Tests for ParenthesizedDecadeRangeParser."""

from span_parsing.parenthesized_decade_range_parser import ParenthesizedDecadeRangeParser


def test_decade_range_basic_ad():
    p = ParenthesizedDecadeRangeParser()
    result = p.parse("Jeffersonian democracy(1790s–1820s)", 1790, False)
    assert result is not None
    assert result.start_year == 1790
    assert result.end_year == 1829


def test_decade_range_with_location_and_bc():
    p = ParenthesizedDecadeRangeParser()
    result = p.parse("Dynasty (Region, 1790s BC – 1720s BC)", 1790, True)
    assert result is not None
    assert result.start_year == 1799
    assert result.end_year == 1720
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True


def test_decade_range_infers_page_bc_when_no_markers():
    p = ParenthesizedDecadeRangeParser()
    result = p.parse("Some period (500s–400s)", 500, True)
    assert result is not None
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is True


def test_decade_range_rejects_mixed_eras():
    p = ParenthesizedDecadeRangeParser()
    assert p.parse("Weird (1790s BC – 1820s AD)", 1790, None) is None


def test_decade_range_not_match_if_not_at_end():
    p = ParenthesizedDecadeRangeParser()
    assert p.parse("Jeffersonian democracy(1790s–1820s) extra", 1790, False) is None
