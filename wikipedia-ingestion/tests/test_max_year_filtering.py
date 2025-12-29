"""Tests for max year filtering logic."""

from __future__ import annotations

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion_list_of_years import _parse_year, _should_include_page


class TestParseYear:
    """Test parsing of year strings in format '#### AD/BC'."""

    @pytest.mark.parametrize("input_str,expected", [
        # Valid BC formats
        ("150 BC", {"year": 150, "is_bc": True}),
        ("150 bc", {"year": 150, "is_bc": True}),
        ("150BC", {"year": 150, "is_bc": True}),
        ("150 BCE", {"year": 150, "is_bc": True}),
        ("1 BC", {"year": 1, "is_bc": True}),
        ("9999 BC", {"year": 9999, "is_bc": True}),
        
        # Valid AD formats
        ("1962 AD", {"year": 1962, "is_bc": False}),
        ("1962 ad", {"year": 1962, "is_bc": False}),
        ("1962AD", {"year": 1962, "is_bc": False}),
        ("1962 CE", {"year": 1962, "is_bc": False}),
        ("1 AD", {"year": 1, "is_bc": False}),
        
        # No era marker (defaults to AD)
        ("1962", {"year": 1962, "is_bc": False}),
        ("1", {"year": 1, "is_bc": False}),
        ("2024", {"year": 2024, "is_bc": False}),
        
        # Empty/None inputs
        (None, None),
        ("", None),
        ("   ", None),
        
        # Invalid formats
        ("invalid", None),
        ("BC 150", None),
        ("150 XY", None),
        ("12345 BC", None),  # Too many digits
        ("-150 BC", None),  # Negative not supported
        ("1.5 BC", None),  # Decimal not supported
    ])
    def test_parse_year(self, input_str: str | None, expected: dict | None) -> None:
        """Test parsing various year string formats."""
        result = _parse_year(input_str)
        assert result == expected


class TestShouldIncludePage:
    """Test page filtering logic based on min/max year thresholds."""

    @pytest.mark.parametrize("page_year,page_is_bc,min_year,max_year,expected", [
        # No constraints - include everything
        (150, True, None, None, True),
        (1962, False, None, None, True),
        (1, True, None, None, True),
        (1, False, None, None, True),
        
        # Max year only (original behavior) - BC max year, BC pages
        (150, True, None, {"year": 150, "is_bc": True}, True),   # Exactly at max (include)
        (151, True, None, {"year": 150, "is_bc": True}, True),   # Before 150 BC chronologically (include)
        (149, True, None, {"year": 150, "is_bc": True}, False),  # After 150 BC chronologically (exclude)
        (100, True, None, {"year": 150, "is_bc": True}, False),  # After 150 BC chronologically (exclude)
        (200, True, None, {"year": 150, "is_bc": True}, True),   # Before 150 BC chronologically (include)
        (1, True, None, {"year": 150, "is_bc": True}, False),    # After 150 BC chronologically (exclude)
        
        # Max year only - BC max year, AD pages
        (1, False, None, {"year": 150, "is_bc": True}, False),   # AD pages excluded when max is BC
        (1962, False, None, {"year": 150, "is_bc": True}, False),
        
        # Max year only - AD max year, AD pages
        (1962, False, None, {"year": 1962, "is_bc": False}, True),   # Exactly at max
        (1961, False, None, {"year": 1962, "is_bc": False}, True),   # Earlier
        (1963, False, None, {"year": 1962, "is_bc": False}, False),  # Later
        (1, False, None, {"year": 1962, "is_bc": False}, True),      # Much earlier
        (2024, False, None, {"year": 1962, "is_bc": False}, False),  # Much later
        
        # Max year only - AD max year, BC pages
        (150, True, None, {"year": 1962, "is_bc": False}, True),  # All BC included when max is AD
        (1, True, None, {"year": 1962, "is_bc": False}, True),
        (9999, True, None, {"year": 1962, "is_bc": False}, True),
        
        # Min year only - BC min year, BC pages
        (100, True, {"year": 100, "is_bc": True}, None, True),    # At min (include)
        (99, True, {"year": 100, "is_bc": True}, None, True),     # After 100 BC chronologically (include)
        (50, True, {"year": 100, "is_bc": True}, None, True),     # After 100 BC chronologically (include)
        (101, True, {"year": 100, "is_bc": True}, None, False),   # Before 100 BC chronologically (exclude)
        (200, True, {"year": 100, "is_bc": True}, None, False),   # Before 100 BC chronologically (exclude)
        
        # Min year only - BC min year, AD pages
        (1, False, {"year": 100, "is_bc": True}, None, True),     # All AD included when min is BC
        (1962, False, {"year": 100, "is_bc": True}, None, True),
        
        # Min year only - AD min year, AD pages
        (10, False, {"year": 10, "is_bc": False}, None, True),    # At min (include)
        (11, False, {"year": 10, "is_bc": False}, None, True),    # After min (include)
        (50, False, {"year": 10, "is_bc": False}, None, True),    # After min (include)
        (9, False, {"year": 10, "is_bc": False}, None, False),    # Before min (exclude)
        (1, False, {"year": 10, "is_bc": False}, None, False),    # Before min (exclude)
        
        # Min year only - AD min year, BC pages
        (100, True, {"year": 10, "is_bc": False}, None, False),   # All BC excluded when min is AD
        (1, True, {"year": 10, "is_bc": False}, None, False),
        
        # Both min and max - BC range
        (100, True, {"year": 100, "is_bc": True}, {"year": 50, "is_bc": True}, True),   # At min
        (99, True, {"year": 100, "is_bc": True}, {"year": 50, "is_bc": True}, True),    # In range
        (50, True, {"year": 100, "is_bc": True}, {"year": 50, "is_bc": True}, True),    # At max
        (101, True, {"year": 100, "is_bc": True}, {"year": 50, "is_bc": True}, False),  # Before min
        (49, True, {"year": 100, "is_bc": True}, {"year": 50, "is_bc": True}, False),   # After max
        
        # Both min and max - AD range
        (10, False, {"year": 10, "is_bc": False}, {"year": 50, "is_bc": False}, True),   # At min
        (25, False, {"year": 10, "is_bc": False}, {"year": 50, "is_bc": False}, True),   # In range
        (50, False, {"year": 10, "is_bc": False}, {"year": 50, "is_bc": False}, True),   # At max
        (9, False, {"year": 10, "is_bc": False}, {"year": 50, "is_bc": False}, False),   # Before min
        (51, False, {"year": 10, "is_bc": False}, {"year": 50, "is_bc": False}, False),  # After max
        
        # Both min and max - BC to AD range
        (50, True, {"year": 50, "is_bc": True}, {"year": 50, "is_bc": False}, True),    # At BC min
        (1, True, {"year": 50, "is_bc": True}, {"year": 50, "is_bc": False}, True),     # BC in range
        (1, False, {"year": 50, "is_bc": True}, {"year": 50, "is_bc": False}, True),    # AD in range
        (50, False, {"year": 50, "is_bc": True}, {"year": 50, "is_bc": False}, True),   # At AD max
        (51, True, {"year": 50, "is_bc": True}, {"year": 50, "is_bc": False}, False),   # Before BC min
        (51, False, {"year": 50, "is_bc": True}, {"year": 50, "is_bc": False}, False),  # After AD max
        
        # Edge cases around year 1
        (1, True, None, {"year": 1, "is_bc": True}, True),     # 1 BC with max 1 BC (include)
        (2, True, None, {"year": 1, "is_bc": True}, True),     # 2 BC comes before 1 BC (include)
        (1, False, None, {"year": 1, "is_bc": False}, True),   # 1 AD with max 1 AD (include)
        (2, False, None, {"year": 1, "is_bc": False}, False),  # 2 AD comes after 1 AD (exclude)
    ])
    def test_should_include_page(
        self, 
        page_year: int, 
        page_is_bc: bool,
        min_year: dict | None,
        max_year: dict | None, 
        expected: bool
    ) -> None:
        """Test page inclusion logic for various year combinations."""
        result = _should_include_page(page_year, page_is_bc, min_year, max_year)
        assert result == expected


class TestYearRangeIntegration:
    """Integration tests combining parsing and filtering."""

    @pytest.mark.parametrize("max_year_str,page_year,page_is_bc,expected", [
        # "150 BC" - ingest from earliest (e.g. 1000 BC) through 150 BC, stop before 149 BC
        ("150 BC", 150, True, True),   # At cutoff (include)
        ("150 BC", 151, True, True),   # Before 150 BC chronologically (include)
        ("150 BC", 149, True, False),  # After 150 BC chronologically (exclude)
        ("150 BC", 100, True, False),  # After 150 BC chronologically (exclude)
        ("150 BC", 1, False, False),   # AD comes after all BC (exclude)
        
        # "1962 AD" - include 1962 AD and earlier, exclude 1963 AD and later
        ("1962 AD", 1962, False, True),
        ("1962 AD", 1961, False, True),
        ("1962 AD", 1963, False, False),
        ("1962 AD", 1, False, True),
        ("1962 AD", 150, True, True),  # BC included
        
        # "1962" (default AD) - same as "1962 AD"
        ("1962", 1962, False, True),
        ("1962", 1961, False, True),
        ("1962", 1963, False, False),
        ("1962", 150, True, True),  # BC included
    ])
    def test_parse_and_filter_max_year_integration(
        self,
        max_year_str: str,
        page_year: int,
        page_is_bc: bool,
        expected: bool
    ) -> None:
        """Test end-to-end parsing and filtering with max year only."""
        max_year = _parse_year(max_year_str)
        assert max_year is not None, f"Failed to parse: {max_year_str}"
        
        result = _should_include_page(page_year, page_is_bc, None, max_year)
        assert result == expected, (
            f"Page {page_year} {'BC' if page_is_bc else 'AD'} with max '{max_year_str}' "
            f"should be {'included' if expected else 'excluded'}"
        )
    
    @pytest.mark.parametrize("min_year_str,max_year_str,page_year,page_is_bc,expected", [
        # BC range: 100 BC to 50 BC
        ("100 BC", "50 BC", 100, True, True),   # At min
        ("100 BC", "50 BC", 75, True, True),    # In range
        ("100 BC", "50 BC", 50, True, True),    # At max
        ("100 BC", "50 BC", 101, True, False),  # Before min
        ("100 BC", "50 BC", 49, True, False),   # After max
        ("100 BC", "50 BC", 1, False, False),   # AD excluded (max is BC)
        
        # BC to AD range: 50 BC to 50 AD
        ("50 BC", "50 AD", 50, True, True),     # At BC min
        ("50 BC", "50 AD", 1, True, True),      # Late BC
        ("50 BC", "50 AD", 1, False, True),     # Early AD
        ("50 BC", "50 AD", 50, False, True),    # At AD max
        ("50 BC", "50 AD", 51, True, False),    # Before BC min
        ("50 BC", "50 AD", 51, False, False),   # After AD max
        
        # AD range: 10 AD to 50 AD
        ("10 AD", "50 AD", 10, False, True),    # At min
        ("10 AD", "50 AD", 30, False, True),    # In range
        ("10 AD", "50 AD", 50, False, True),    # At max
        ("10 AD", "50 AD", 9, False, False),    # Before min
        ("10 AD", "50 AD", 51, False, False),   # After max
        ("10 AD", "50 AD", 100, True, False),   # BC excluded (min is AD)
    ])
    def test_parse_and_filter_range_integration(
        self,
        min_year_str: str,
        max_year_str: str,
        page_year: int,
        page_is_bc: bool,
        expected: bool
    ) -> None:
        """Test end-to-end parsing and filtering with min and max years."""
        min_year = _parse_year(min_year_str)
        max_year = _parse_year(max_year_str)
        assert min_year is not None, f"Failed to parse min: {min_year_str}"
        assert max_year is not None, f"Failed to parse max: {max_year_str}"
        
        result = _should_include_page(page_year, page_is_bc, min_year, max_year)
        assert result == expected, (
            f"Page {page_year} {'BC' if page_is_bc else 'AD'} with range '{min_year_str}' to '{max_year_str}' "
            f"should be {'included' if expected else 'excluded'}"
        )


class TestMaxYearBoundaryConditions:
    """Test boundary conditions and edge cases."""

    def test_year_zero_handling(self) -> None:
        """There is no year 0 in historical calendar, but test handling."""
        max_year = _parse_year("1 BC")
        # Year 0 would be treated as AD by is_bc=False
        assert _should_include_page(0, False, None, max_year) is False
        assert _should_include_page(0, True, None, max_year) is False  # 0 BC doesn't exist

    def test_very_large_years(self) -> None:
        """Test handling of very large year numbers."""
        # Within 4-digit limit
        max_year = _parse_year("9999 BC")
        assert max_year == {"year": 9999, "is_bc": True}
        assert _should_include_page(9999, True, None, max_year) is True
        assert _should_include_page(9998, True, None, max_year) is False
        
        # Beyond 4-digit limit should fail parsing
        assert _parse_year("10000 BC") is None

    def test_case_insensitivity(self) -> None:
        """Test that era markers are case-insensitive."""
        for marker in ["BC", "bc", "Bc", "bC"]:
            max_year = _parse_year(f"150 {marker}")
            assert max_year == {"year": 150, "is_bc": True}
        
        for marker in ["AD", "ad", "Ad", "aD", "CE", "ce"]:
            max_year = _parse_year(f"1962 {marker}")
            assert max_year == {"year": 1962, "is_bc": False}

    def test_whitespace_variations(self) -> None:
        """Test various whitespace patterns."""
        test_cases = [
            "150 BC",
            "150  BC",   # Double space
            "150   BC",  # Triple space
            " 150 BC",   # Leading space
            "150 BC ",   # Trailing space
            " 150 BC ",  # Both
        ]
        for test_str in test_cases:
            max_year = _parse_year(test_str)
            assert max_year == {"year": 150, "is_bc": True}, f"Failed for: {test_str!r}"
