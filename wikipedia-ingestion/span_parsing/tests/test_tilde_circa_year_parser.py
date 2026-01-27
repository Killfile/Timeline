"""Unit tests for TildeCircaYearParser."""

import pytest
from span_parsing.tilde_circa_year_parser import TildeCircaYearParser
from span_parsing.span import SpanPrecision


class TestTildeCircaYearParser:
    """Test cases for TildeCircaYearParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = TildeCircaYearParser()
    
    # Basic tilde circa patterns
    def test_tilde_1450(self):
        """Test '~1450' parses correctly."""
        span = self.parser.parse("~1450", 2000, False)
        assert span is not None
        assert span.start_year == 1450
        assert span.end_year == 1450
        assert span.start_year_is_bc is False
        assert span.precision == SpanPrecision.CIRCA
    
    def test_tilde_450_bce(self):
        """Test '~450 BCE' parses correctly."""
        span = self.parser.parse("~450 BCE", 2000, False)
        assert span is not None
        assert span.start_year == 450
        assert span.end_year == 450
        assert span.start_year_is_bc is True
    
    def test_tilde_9300_bce(self):
        """Test '~9300 BCE' parses correctly."""
        span = self.parser.parse("~9300 BCE", 2000, False)
        assert span is not None
        assert span.start_year == 9300
        assert span.start_year_is_bc is True
    
    # With space after tilde
    def test_tilde_space_1200(self):
        """Test '~ 1200' (space after tilde) parses correctly."""
        span = self.parser.parse("~ 1200", 2000, False)
        assert span is not None
        assert span.start_year == 1200
        assert span.start_year_is_bc is False
    
    # Era markers
    def test_tilde_1200_ad(self):
        """Test '~1200 AD' parses correctly."""
        span = self.parser.parse("~1200 AD", 2000, False)
        assert span is not None
        assert span.start_year == 1200
        assert span.start_year_is_bc is False
    
    def test_tilde_100_bc(self):
        """Test '~100 BC' parses correctly."""
        span = self.parser.parse("~100 BC", 2000, False)
        assert span is not None
        assert span.start_year == 100
        assert span.start_year_is_bc is True
    
    # Context-dependent (no era marker)
    def test_tilde_no_marker_bc_context(self):
        """Test '~450' with BC page context."""
        span = self.parser.parse("~450", 500, True)
        assert span is not None
        assert span.start_year == 450
        assert span.start_year_is_bc is True
    
    def test_tilde_no_marker_ad_context(self):
        """Test '~1516' with AD page context."""
        span = self.parser.parse("~1516", 2000, False)
        assert span is not None
        assert span.start_year == 1516
        assert span.start_year_is_bc is False
    
    # Edge cases and non-matches
    def test_non_tilde_text(self):
        """Test that non-tilde text returns None."""
        span = self.parser.parse("1450", 2000, False)
        assert span is None
    
    def test_empty_string(self):
        """Test empty string returns None."""
        span = self.parser.parse("", 2000, False)
        assert span is None
    
    def test_tilde_not_at_start(self):
        """Test that tilde not at start returns None."""
        span = self.parser.parse("circa ~1450", 2000, False)
        assert span is None
