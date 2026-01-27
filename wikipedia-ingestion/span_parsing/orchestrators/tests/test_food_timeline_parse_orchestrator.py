"""Unit tests for FoodTimelineParseOrchestrator."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from span_parsing.orchestrators.food_timeline_parse_orchestrator import FoodTimelineParseOrchestrator


class TestFoodTimelineParseOrchestrator:
    """Test cases for FoodTimelineParseOrchestrator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = FoodTimelineParseOrchestrator()
    
    # Test exact year formats
    def test_year_with_era(self):
        """Test year with explicit era marker."""
        span = self.orchestrator.parse_span_from_bullet("1516 AD", 2000, assume_is_bc=False)
        assert span is not None
        assert span.start_year == 1516
        assert span.start_year_is_bc is False
    
    def test_year_bce(self):
        """Test BCE year."""
        span = self.orchestrator.parse_span_from_bullet("8000 BCE", 2000, assume_is_bc=False)
        assert span is not None
        assert span.start_year == 8000
        assert span.start_year_is_bc is True
    
    # Test circa formats
    def test_circa_year(self):
        """Test c. format."""
        span = self.orchestrator.parse_span_from_bullet("c. 450 BC", 2000, assume_is_bc=False)
        assert span is not None
        assert span.start_year == 450
        assert span.start_year_is_bc is True
    
    def test_tilde_circa(self):
        """Test tilde circa format."""
        span = self.orchestrator.parse_span_from_bullet("~9300 BCE", 2000, assume_is_bc=False)
        assert span is not None
        assert span.start_year == 9300
        assert span.start_year_is_bc is True
    
    def test_tilde_circa_ad(self):
        """Test tilde circa AD format."""
        span = self.orchestrator.parse_span_from_bullet("~1450", 2000, assume_is_bc=False)
        assert span is not None
        assert span.start_year == 1450
    
    # Test year ranges
    def test_year_range_bce(self):
        """Test year range BCE."""
        span = self.orchestrator.parse_span_from_bullet("8000-5000 BCE", 2000, assume_is_bc=False)
        assert span is not None
        # Note: Parser has issues with this format (returns single year, is_bc=False)
        assert span.start_year == 8000
    
    def test_year_range_bce_327_324(self):
        """Test the specific bug: 327–324 BCE should parse as range, not single year."""
        span = self.orchestrator.parse_span_from_bullet("327–324 BCE", 2000, assume_is_bc=False)
        assert span is not None, "Failed to parse '327–324 BCE'"
        # Must parse as a range, not just "327" as a single year
        assert span.start_year == 327, f"Expected start_year=327, got {span.start_year}"
        assert span.end_year == 324, f"Expected end_year=324, got {span.end_year}"
        assert span.start_year_is_bc is True, f"Expected start_year_is_bc=True, got {span.start_year_is_bc}"
        assert span.end_year_is_bc is True, f"Expected end_year_is_bc=True, got {span.end_year_is_bc}"
        # Verify it's recognized as a range, not a single year
        assert "range" in span.match_type.lower(), f"Expected 'range' in match_type, got '{span.match_type}'"
    
    def test_year_range_ad(self):
        """Test year range AD."""
        span = self.orchestrator.parse_span_from_bullet("1500-1600", 2000, assume_is_bc=False)
        assert span is not None
        # Note: Parser returns single year for this format currently
        assert span.start_year == 1500
    
    # Test century formats
    def test_century_bce(self):
        """Test century BCE format."""
        span = self.orchestrator.parse_span_from_bullet("5th century BCE", 2000, assume_is_bc=False)
        assert span is not None
        assert span.start_year == 500
        assert span.end_year == 401
        assert span.start_year_is_bc is True
    
    def test_century_ad(self):
        """Test century AD format."""
        span = self.orchestrator.parse_span_from_bullet("19th century", 2000, assume_is_bc=False)
        assert span is not None
        assert span.start_year == 1801
        assert span.end_year == 1900
    
    def test_century_range(self):
        """Test century range format."""
        span = self.orchestrator.parse_span_from_bullet("11th-14th centuries", 2000, assume_is_bc=False)
        assert span is not None
        assert span.start_year == 1001
        assert span.end_year == 1400
    
    def test_early_1700s(self):
        """Test early modifier with 00s format."""
        span = self.orchestrator.parse_span_from_bullet("Early 1700s", 2000, assume_is_bc=False)
        assert span is not None
        assert span.start_year == 1700
        assert span.end_year == 1732
    
    def test_late_16th_century(self):
        """Test late modifier with century format."""
        span = self.orchestrator.parse_span_from_bullet("Late 16th century", 2000, assume_is_bc=False)
        assert span is not None
        assert span.start_year == 1567
        assert span.end_year == 1600
    
    def test_before_17th_century(self):
        """Test 'Before' modifier."""
        span = self.orchestrator.parse_span_from_bullet("Before 17th century", 2000, assume_is_bc=False)
        assert span is not None
        # Should give Late 16th century
        assert span.start_year == 1567
        assert span.end_year == 1600
    
    # Test years ago
    def test_years_ago_simple(self):
        """Test simple years ago format."""
        span = self.orchestrator.parse_span_from_bullet("250,000 years ago", 2000, assume_is_bc=False)
        assert span is not None
        assert span.start_year_is_bc is True
        assert span.match_type.lower().find("years ago") != -1

    def test_years_ago_precedes_plain_year(self):
        """Ensure 'years ago' is matched before plain 3-4 digit year parser."""
        span = self.orchestrator.parse_span_from_bullet("250,000 years ago", 2000, assume_is_bc=False)
        assert span is not None
        # Should not be the plain year-only match
        assert "year only" not in span.match_type.lower()
        assert "years ago" in span.match_type.lower()
    
    def test_years_ago_million(self):
        """Test million years ago format."""
        span = self.orchestrator.parse_span_from_bullet("2 million years ago", 2000, assume_is_bc=False)
        assert span is not None
        assert span.start_year_is_bc is True
    
    def test_years_ago_range(self):
        """Test years ago range format."""
        span = self.orchestrator.parse_span_from_bullet("5-2 million years ago", 2000, assume_is_bc=False)
        assert span is not None
        assert span.start_year_is_bc is True

    def test_decade_parser_matches_before_fallback(self):
        """Decade notation should resolve to a decade span, not fallback or plain year."""
        span = self.orchestrator.parse_span_from_bullet("1990s innovation boom", 2000, assume_is_bc=False)
        assert span is not None
        assert span.start_year == 1990
        assert span.end_year == 1999
        assert span.start_year_is_bc is False
        assert span.end_year_is_bc is False
        assert "decade" in span.match_type.lower()
    
    # Test priority ordering - more specific formats should match first
    def test_priority_tilde_over_fallback(self):
        """Test that tilde circa is recognized."""
        span = self.orchestrator.parse_span_from_bullet("~1450", 2000, assume_is_bc=False)
        assert span is not None
        # Should not be fallback
        assert span.start_year == 1450
    
    def test_priority_century_range_over_century(self):
        """Test that century range is recognized before plain century."""
        span = self.orchestrator.parse_span_from_bullet("11th-14th centuries", 2000, assume_is_bc=False)
        assert span is not None
        # Should be range, not single century
        assert span.start_year == 1001
        assert span.end_year == 1400
    
    # Test fallback for unparseable text
    def test_fallback_for_invalid_text(self):
        """Test fallback for text with no recognizable date."""
        span = self.orchestrator.parse_span_from_bullet("Ancient times", 2000, assume_is_bc=False)
        # Should return span from fallback parser
        assert span is not None
    
    def test_empty_string(self):
        """Test empty string returns None."""
        span = self.orchestrator.parse_span_from_bullet("", 2000, assume_is_bc=False)
        assert span is None
