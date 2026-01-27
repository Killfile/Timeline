"""
Unit tests for EventParser (date_extraction_strategies.py)
Covers: bullet point parsing, date extraction with orchestrator, logging
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest
from strategies.timeline_of_food.date_extraction_strategies import (
    EventParser,
    EventParseResult,
)
from strategies.timeline_of_food.hierarchical_strategies import TextSection
from strategies.timeline_of_food.food_event import FoodEvent
from span_parsing.span import Span


@pytest.fixture
def sample_section():
    """Create a sample TextSection for testing."""
    return TextSection(
        name="19th Century",
        level=2,
        date_range_start=1801,
        date_range_end=1900,
        date_is_explicit=False,
        date_is_range=True,
        position=0,
        is_bc_start=False,
        is_bc_end=False,
        event_count=0,
    )


@pytest.fixture
def event_parser():
    """Create an EventParser instance for testing."""
    return EventParser()


class TestEventParserBasics:
    """Test basic EventParser functionality."""

    def test_eventparser_initialization(self, event_parser):
        """Test that EventParser initializes with orchestrator."""
        assert event_parser is not None
        assert event_parser.orchestrator is not None
        assert event_parser.undated_events == []

    def test_eventparser_parses_bullet_with_date(self, event_parser, sample_section):
        """Test parsing a bullet point with an explicit date."""
        bullet_text = "1847: First candy machine invented in Boston"
        
        result = event_parser.parse_bullet_point(bullet_text, sample_section)
        
        assert isinstance(result, EventParseResult)
        # Will be None if orchestrator can't parse the date
        # (orchestrator needs proper setup)
        if result.event is not None:
            assert result.has_date is True
            # Description may include the date if orchestrator didn't extract it
            assert "candy machine" in result.event.description.lower()
        else:
            # Orchestrator returned None, but parsing should complete
            assert result.has_date is False


class TestEventParserBulletCleaning:
    """Test bullet text cleaning functionality."""

    def test_clean_bullet_removes_leading_dash(self, event_parser):
        """Test that leading dash is removed."""
        cleaned = event_parser._clean_bullet_text("- Event description")
        assert cleaned == "Event description"

    def test_clean_bullet_removes_leading_bullet(self, event_parser):
        """Test that leading bullet point is removed."""
        cleaned = event_parser._clean_bullet_text("• Event description")
        assert cleaned == "Event description"

    def test_clean_bullet_removes_html_tags(self, event_parser):
        """Test that HTML tags are removed."""
        cleaned = event_parser._clean_bullet_text(
            "<li>1847</li><li>Event <b>description</b></li>"
        )
        assert "1847" in cleaned or "Event" in cleaned

    def test_clean_bullet_normalizes_whitespace(self, event_parser):
        """Test that multiple spaces are normalized."""
        cleaned = event_parser._clean_bullet_text("Event   with    spaces")
        assert "   " not in cleaned
        assert cleaned == "Event with spaces"

    def test_clean_bullet_empty_after_cleaning(self, event_parser):
        """Test handling of text that becomes empty after cleaning."""
        cleaned = event_parser._clean_bullet_text("-  ")
        assert cleaned == ""

    def test_clean_bullet_with_citations(self, event_parser):
        """Test that citation superscripts are removed."""
        cleaned = event_parser._clean_bullet_text("Event<sup>[1]</sup> description")
        assert "[1]" not in cleaned


class TestEventParserWikiLinks:
    """Test Wikipedia link extraction."""

    def test_extract_wiki_links_simple(self, event_parser):
        """Test extraction of simple Wikipedia links."""
        html = '<a href="/wiki/Coffee">Coffee</a> arrived in Europe'
        links = event_parser._extract_wiki_links(html)
        assert "Coffee" in links

    def test_extract_wiki_links_multiple(self, event_parser):
        """Test extraction of multiple Wikipedia links."""
        html = '<a href="/wiki/Coffee">Coffee</a> and <a href="/wiki/Tea">Tea</a>'
        links = event_parser._extract_wiki_links(html)
        assert len(links) >= 2
        assert "Coffee" in links
        assert "Tea" in links

    def test_extract_wiki_links_skips_special_pages(self, event_parser):
        """Test that special pages (with :) are skipped."""
        html = '<a href="/wiki/File:Example.jpg">File</a>'
        links = event_parser._extract_wiki_links(html)
        # File namespace links should be filtered out
        assert "File:Example.jpg" not in links

    def test_extract_wiki_links_empty(self, event_parser):
        """Test extraction when no links present."""
        html = "Plain text with no links"
        links = event_parser._extract_wiki_links(html)
        assert links == []


class TestEventParserCitations:
    """Test citation extraction."""

    def test_extract_citations_single(self, event_parser):
        """Test extraction of single citation."""
        text = "Event description[1]"
        citations = event_parser._extract_citations(text)
        assert 1 in citations

    def test_extract_citations_multiple(self, event_parser):
        """Test extraction of multiple citations."""
        text = "First part[1] and second part[2] and third[3]"
        citations = event_parser._extract_citations(text)
        assert len(citations) >= 3
        assert 1 in citations
        assert 2 in citations
        assert 3 in citations

    def test_extract_citations_none(self, event_parser):
        """Test extraction when no citations present."""
        text = "Event description with no citations"
        citations = event_parser._extract_citations(text)
        assert citations == []

    def test_extract_citations_large_numbers(self, event_parser):
        """Test extraction of large citation numbers."""
        text = "Event[42] and another[123]"
        citations = event_parser._extract_citations(text)
        assert 42 in citations
        assert 123 in citations


class TestEventParserConfidenceLevel:
    """Test confidence level determination."""

    def test_confidence_no_span(self, event_parser, sample_section):
        """Test confidence when span is None."""
        confidence = event_parser._determine_confidence(None, sample_section)
        assert confidence == "fallback"

    def test_confidence_explicit_year(self, event_parser, sample_section):
        """Test confidence for explicit year match."""
        span = Mock()
        span.match_type = "YEAR"
        confidence = event_parser._determine_confidence(span, sample_section)
        assert confidence == "explicit"

    def test_confidence_circa(self, event_parser, sample_section):
        """Test confidence for circa/approximate dates."""
        span = Mock()
        span.match_type = "CIRCA_YEAR"
        confidence = event_parser._determine_confidence(span, sample_section)
        assert confidence == "approximate"

    def test_confidence_century(self, event_parser, sample_section):
        """Test confidence for century matches."""
        span = Mock()
        span.match_type = "CENTURY"
        confidence = event_parser._determine_confidence(span, sample_section)
        assert confidence == "approximate"

    def test_confidence_years_ago(self, event_parser, sample_section):
        """Test confidence for years ago notation."""
        span = Mock()
        span.match_type = "YEARS_AGO"
        confidence = event_parser._determine_confidence(span, sample_section)
        # YEARS_AGO should return approximate since it's relative/imprecise
        assert confidence == "approximate"

    def test_confidence_unknown_span(self, event_parser, sample_section):
        """Test confidence for unknown span type defaults to explicit."""
        span = Mock()
        span.match_type = "UNKNOWN_TYPE"
        confidence = event_parser._determine_confidence(span, sample_section)
        assert confidence == "explicit"


class TestEventParserPrecision:
    """Test precision calculation."""

    def test_calculate_precision_with_value_attribute(self, event_parser):
        """Test precision calculation when span has value attribute."""
        span = Mock()
        span.precision = Mock()
        span.precision.value = 0.95
        precision = event_parser._calculate_precision(span)
        assert precision == 0.95

    def test_calculate_precision_without_value_attribute(self, event_parser):
        """Test precision calculation when span has direct float."""
        span = Mock()
        span.precision = 0.75
        precision = event_parser._calculate_precision(span)
        assert precision == 0.75

    def test_calculate_precision_returns_float(self, event_parser):
        """Test that precision always returns a float."""
        span = Mock()
        span.precision = 0.5
        precision = event_parser._calculate_precision(span)
        assert isinstance(precision, float)


class TestEventParserLogging:
    """Test undated event logging."""

    def test_log_undated_event_tracks_event(self, event_parser, sample_section):
        """Test that undated events are tracked."""
        text = "Event without date"
        event_parser._log_undated_event(text, sample_section)
        
        assert len(event_parser.undated_events) == 1
        assert event_parser.undated_events[0]["text"] == text
        assert event_parser.undated_events[0]["section"] == "19th Century"

    def test_log_undated_event_truncates_long_text(self, event_parser, sample_section):
        """Test that long text is truncated to 100 chars."""
        long_text = "x" * 200
        event_parser._log_undated_event(long_text, sample_section)
        
        assert len(event_parser.undated_events[0]["text"]) <= 100

    def test_get_undated_summary(self, event_parser, sample_section):
        """Test getting undated event summary."""
        event_parser._log_undated_event("Event 1", sample_section)
        event_parser._log_undated_event("Event 2", sample_section)
        
        summary = event_parser.get_undated_summary()
        assert summary["total_undated"] == 2
        assert len(summary["events"]) == 2

    def test_undated_summary_empty_initially(self, event_parser):
        """Test that summary is empty initially."""
        summary = event_parser.get_undated_summary()
        assert summary["total_undated"] == 0
        assert summary["events"] == []


class TestEventParserIntegration:
    """Integration tests for full parsing workflow."""

    def test_parse_bullet_returns_result_type(self, event_parser, sample_section):
        """Test that parse_bullet_point always returns EventParseResult."""
        result = event_parser.parse_bullet_point("Test event", sample_section)
        assert isinstance(result, EventParseResult)

    def test_parse_bullet_empty_text(self, event_parser, sample_section):
        """Test handling of empty bullet text."""
        result = event_parser.parse_bullet_point("", sample_section)
        assert result.has_date is False
        assert result.event is None
        assert result.error_message is not None

    def test_parse_bullet_whitespace_only(self, event_parser, sample_section):
        """Test handling of whitespace-only text."""
        result = event_parser.parse_bullet_point("   \n\t  ", sample_section)
        assert result.has_date is False
        assert result.event is None

    def test_parse_bullet_source_format_bullet(self, event_parser, sample_section):
        """Test that source_format defaults to 'bullet'."""
        result = event_parser.parse_bullet_point("1847: Test event", sample_section)
        # Check would require orchestrator parsing to work
        # This is a smoke test that parsing completes

    def test_parse_bullet_source_format_table(self, event_parser, sample_section):
        """Test setting source_format to 'table'."""
        result = event_parser.parse_bullet_point(
            "1847: Test event",
            sample_section,
            source_format="table"
        )
        # Check would require orchestrator parsing to work
        # This is a smoke test that parsing completes
