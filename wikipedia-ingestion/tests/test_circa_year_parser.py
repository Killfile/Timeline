"""Tests for CircaYearParser."""

import pytest
from span_parsing.circa_year_parser import CircaYearParser
from span_parsing.orchestrators.years_parse_orchestrator import YearsParseOrchestrator
from span_parsing.span import SpanPrecision


class TestCircaYearParser:
    """Test circa year parsing."""
    
    def test_circa_with_period_and_space(self):
        """Test 'c. YEAR' pattern."""
        parser = CircaYearParser()
        span = parser.parse("c. 450 BC", page_year=450, page_bc=True)
        assert span is not None
        assert span.start_year == 450
        assert span.end_year == 450
        assert span.is_bc is True
        assert span.precision == SpanPrecision.CIRCA
        assert "circa" in span.match_type.lower()
    
    def test_circa_with_ca_period(self):
        """Test 'ca. YEAR' pattern."""
        parser = CircaYearParser()
        span = parser.parse("ca. 1200", page_year=1200, page_bc=False)
        assert span is not None
        assert span.start_year == 1200
        assert span.end_year == 1200
        assert span.is_bc is False
        assert span.precision == SpanPrecision.CIRCA
    
    def test_circa_full_word(self):
        """Test 'circa YEAR' pattern."""
        parser = CircaYearParser()
        span = parser.parse("circa 500 BC", page_year=500, page_bc=True)
        assert span is not None
        assert span.start_year == 500
        assert span.end_year == 500
        assert span.is_bc is True
    
    def test_circa_no_space_after_period(self):
        """Test 'c.YEAR' pattern (no space)."""
        parser = CircaYearParser()
        span = parser.parse("c.450", page_year=450, page_bc=True)
        assert span is not None
        assert span.start_year == 450
        assert span.end_year == 450
    
    def test_circa_with_explicit_ad(self):
        """Test circa with explicit AD marker."""
        parser = CircaYearParser()
        span = parser.parse("c. 1000 AD", page_year=1000, page_bc=False)
        assert span is not None
        assert span.start_year == 1000
        assert span.is_bc is False
    
    def test_circa_with_bce(self):
        """Test circa with BCE marker."""
        parser = CircaYearParser()
        span = parser.parse("ca. 2500 BCE", page_year=2500, page_bc=True)
        assert span is not None
        assert span.start_year == 2500
        assert span.is_bc is True
    
    def test_circa_uses_page_context_when_no_era(self):
        """Test that page context is used when no era marker present."""
        parser = CircaYearParser()
        
        # BC page context
        span_bc = parser.parse("c. 300", page_year=300, page_bc=True)
        assert span_bc is not None
        assert span_bc.is_bc is True
        
        # AD page context
        span_ad = parser.parse("c. 300", page_year=300, page_bc=False)
        assert span_ad is not None
        assert span_ad.is_bc is False
    
    def test_circa_not_at_start_returns_none(self):
        """Test that circa in middle of text returns None."""
        parser = CircaYearParser()
        span = parser.parse("Something happened c. 450 BC", page_year=450, page_bc=True)
        assert span is None
    
    def test_circa_without_year_returns_none(self):
        """Test that circa without a year returns None."""
        parser = CircaYearParser()
        span = parser.parse("c. something", page_year=100, page_bc=True)
        assert span is None
    
    def test_circa_integration_with_span_parser(self):
        """Test that SpanParser correctly uses CircaYearParser."""
        span = YearsParseOrchestrator.parse_span_from_bullet("c. 490 BC – Battle of Marathon", span_year=490, assume_is_bc=True)
        assert span is not None
        assert span.start_year == 490
        assert span.is_bc is True
        assert "circa" in span.match_type.lower()
    
    def test_circa_three_digit_year(self):
        """Test circa with 3-digit year."""
        parser = CircaYearParser()
        span = parser.parse("c. 100 BC", page_year=100, page_bc=True)
        assert span is not None
        assert span.start_year == 100
        assert span.is_bc is True
    
    def test_circa_four_digit_year(self):
        """Test circa with 4-digit year."""
        parser = CircaYearParser()
        span = parser.parse("circa 1492 AD", page_year=1492, page_bc=False)
        assert span is not None
        assert span.start_year == 1492
        assert span.is_bc is False
    
    def test_circa_case_insensitive(self):
        """Test that circa patterns are case-insensitive."""
        parser = CircaYearParser()
        
        span1 = parser.parse("C. 500 BC", page_year=500, page_bc=True)
        assert span1 is not None
        
        span2 = parser.parse("CA. 500 BC", page_year=500, page_bc=True)
        assert span2 is not None
        
        span3 = parser.parse("CIRCA 500 BC", page_year=500, page_bc=True)
        assert span3 is not None
    
    def test_circa_with_ce_marker(self):
        """Test circa with CE (Common Era) marker."""
        parser = CircaYearParser()
        span = parser.parse("c. 1500 CE", page_year=1500, page_bc=False)
        assert span is not None
        assert span.start_year == 1500
        assert span.is_bc is False
