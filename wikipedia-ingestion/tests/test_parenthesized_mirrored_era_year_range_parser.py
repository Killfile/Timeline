"""Tests for ParenthesizedMirroredEraYearRangeParser."""

from span_parsing.parenthesized_mirrored_era_year_range_parser import ParenthesizedMirroredEraYearRangeParser


def test_mirrored_with_location_matches():
    p = ParenthesizedMirroredEraYearRangeParser()
    result = p.parse("Xiongnu(Mongolia, 220 BC – AD 200)", 220, None)
    assert result is not None
    assert result.start_year == 220
    assert result.end_year == 200
    assert result.start_year_is_bc is True
    assert result.end_year_is_bc is False


def test_mirrored_without_location_matches():
    p = ParenthesizedMirroredEraYearRangeParser()
    result = p.parse("Some period (220 BC - AD 200)", 220, None)
    assert result is not None
    assert result.start_year == 220
    assert result.end_year == 200


def test_mirrored_requires_both_eras():
    p = ParenthesizedMirroredEraYearRangeParser()
    assert p.parse("Odd one (220 - AD 200)", 220, None) is None


def test_mirrored_invalid_order_rejected():
    p = ParenthesizedMirroredEraYearRangeParser()
    # AD start and BC end yields invalid chronological ordering
    assert p.parse("Broken (AD 200 - 220 BC)", 200, None) is None
