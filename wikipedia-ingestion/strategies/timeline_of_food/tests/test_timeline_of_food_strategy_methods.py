"""
Unit tests for TimelineOfFoodStrategy individual methods.

Covers:
- T015a: fetch() method (caching, HTTP responses, error handling)
- T016a: parse() method (orchestration, event extraction, edge cases)
- T018a: title generation (truncation, word boundaries)
- T019a: event_key generation (MD5 consistency, deduplication)
- T023a: undated event logging (info warnings, error recording)
- T024a: error handling (404s, timeouts, malformed HTML)
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest
from strategies.timeline_of_food.timeline_of_food_strategy import TimelineOfFoodStrategy
from strategies.timeline_of_food.food_event import FoodEvent


@pytest.fixture
def strategy(tmp_path):
    """Create a TimelineOfFoodStrategy instance for testing."""
    return TimelineOfFoodStrategy(run_id="test-run", output_dir=tmp_path)


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    response = Mock()
    response.status_code = 200
    response.text = "<html><body>Test content</body></html>"
    return response


class TestTimelineOfFoodStrategyFetch:
    """Tests for fetch() method (T015a)."""
    
    def test_fetch_returns_fetch_result(self, strategy):
        """Test that fetch() returns a FetchResult object."""
        from strategies.strategy_base import FetchResult
        
        with patch('strategies.timeline_of_food.timeline_of_food_strategy.get_html') as mock_get_html:
            mock_get_html.return_value = (("<html><body>Test content</body></html>", "https://en.wikipedia.org/wiki/Timeline_of_food"), None)
            
            result = strategy.fetch()
            
            assert isinstance(result, FetchResult)
            assert result.strategy_name == "TimelineOfFood"
            assert result.fetch_count == 1

    def test_fetch_caches_content(self, strategy):
        """Test that fetch() caches the HTML content."""
        with patch('strategies.timeline_of_food.timeline_of_food_strategy.get_html') as mock_get_html:
            mock_get_html.return_value = (("<html><body>Fetched content</body></html>", "https://en.wikipedia.org/wiki/Timeline_of_food"), None)
            
            result = strategy.fetch()
            
            assert strategy.html_content is not None
            # HTML content comes from mock, just verify it's not empty
            assert len(strategy.html_content) > 0
            assert result.fetch_count == 1

    def test_fetch_with_cache_hit(self, strategy):
        """Test that fetch() uses cached content from ingestion_common cache."""
        with patch('strategies.timeline_of_food.timeline_of_food_strategy.get_html') as mock_get_html:
            # Simulate cache hit in get_html
            mock_get_html.return_value = (("<html><body>Cached content</body></html>", "https://en.wikipedia.org/wiki/Timeline_of_food"), None)
            
            result = strategy.fetch()
            
            # get_html should be called (it handles caching internally)
            mock_get_html.assert_called_once()
            assert strategy.html_content == "<html><body>Cached content</body></html>"
            # Check that final_url is captured
            assert strategy.canonical_url == "https://en.wikipedia.org/wiki/Timeline_of_food"

    def test_fetch_http_error(self, strategy, tmp_path):
        """Test fetch() handling of HTTP errors."""
        with patch('strategies.timeline_of_food.timeline_of_food_strategy.get_html') as mock_get_html:
            # Simulate HTTP error from get_html
            mock_get_html.return_value = (("", "https://en.wikipedia.org/wiki/Timeline_of_food"), "HTTP error: 404 Not Found")
            
            with pytest.raises(RuntimeError) as exc_info:
                strategy.fetch()
            
            assert "404" in str(exc_info.value) or "error" in str(exc_info.value).lower()

    def test_fetch_timeout_error(self, strategy, tmp_path):
        """Test fetch() handling of timeout errors."""
        with patch('strategies.timeline_of_food.timeline_of_food_strategy.get_html') as mock_get_html:
            # Simulate timeout error from get_html
            mock_get_html.return_value = (("", "https://en.wikipedia.org/wiki/Timeline_of_food"), "Connection timeout")
            
            with pytest.raises(RuntimeError) as exc_info:
                strategy.fetch()
            
            error_msg = str(exc_info.value).lower()
            assert "timeout" in error_msg or "timed out" in error_msg or "error" in error_msg

    def test_fetch_sets_metadata(self, strategy):
        """Test that fetch() populates metadata correctly."""
        with patch('strategies.timeline_of_food.timeline_of_food_strategy.get_html') as mock_get_html:
            html_content = "<html><body>Test content</body></html>"
            mock_get_html.return_value = ((html_content, "https://en.wikipedia.org/wiki/Timeline_of_food"), None)
            
            result = strategy.fetch()
            
            assert result.fetch_metadata["url"] == strategy.WIKIPEDIA_URL
            assert result.fetch_metadata["final_url"] == "https://en.wikipedia.org/wiki/Timeline_of_food"
            assert "fetch_timestamp_utc" in result.fetch_metadata
            assert "content_length_bytes" in result.fetch_metadata
            assert result.fetch_metadata["content_length_bytes"] == len(html_content)


class TestTimelineOfFoodStrategyParse:
    """Tests for parse() method (T016a)."""
    
    def test_parse_returns_parse_result(self, strategy):
        """Test that parse() returns a ParseResult object."""
        from strategies.strategy_base import FetchResult, ParseResult
        
        strategy.html_content = "<html><body><h2><span class='mw-headline'>Test</span></h2></body></html>"
        fetch_result = FetchResult(strategy_name="TimelineOfFood", fetch_count=1)
        
        result = strategy.parse(fetch_result)
        
        assert isinstance(result, ParseResult)
        assert result.strategy_name == "TimelineOfFood"
        assert result.events is not None

    def test_parse_requires_html_content(self, strategy):
        """Test that parse() raises error if html_content is not set."""
        from strategies.strategy_base import FetchResult
        
        strategy.html_content = None
        fetch_result = FetchResult(strategy_name="TimelineOfFood", fetch_count=1)
        
        with pytest.raises(RuntimeError):
            strategy.parse(fetch_result)

    def test_parse_with_empty_html(self, strategy):
        """Test parse() with empty HTML content."""
        from strategies.strategy_base import FetchResult, ParseResult
        
        strategy.html_content = "<html><body></body></html>"
        fetch_result = FetchResult(strategy_name="TimelineOfFood", fetch_count=1)
        
        result = strategy.parse(fetch_result)
        
        assert isinstance(result, ParseResult)
        assert len(result.events) == 0

    def test_parse_generates_metadata(self, strategy):
        """Test that parse() generates metadata with statistics."""
        from strategies.strategy_base import FetchResult
        
        strategy.html_content = "<html><body><h2><span class='mw-headline'>Century</span></h2></body></html>"
        fetch_result = FetchResult(strategy_name="TimelineOfFood", fetch_count=1)
        
        result = strategy.parse(fetch_result)
        
        assert "total_events_found" in result.parse_metadata
        assert "total_events_parsed" in result.parse_metadata
        assert "parsing_start_utc" in result.parse_metadata
        assert "parsing_end_utc" in result.parse_metadata
        assert "elapsed_seconds" in result.parse_metadata

    def test_parse_tracks_confidence_distribution(self, strategy):
        """Test that parse() tracks confidence levels of parsed events."""
        from strategies.strategy_base import FetchResult
        
        strategy.html_content = "<html><body><h2><span class='mw-headline'>Test</span></h2></body></html>"
        fetch_result = FetchResult(strategy_name="TimelineOfFood", fetch_count=1)
        
        result = strategy.parse(fetch_result)
        
        assert "confidence_distribution" in result.parse_metadata
        confidence = result.parse_metadata["confidence_distribution"]
        assert "explicit" in confidence
        assert "inferred" in confidence
        assert "approximate" in confidence


class TestFoodEventTitleGeneration:
    """Tests for title generation (T018a)."""
    
    def test_title_generation_from_description(self):
        """Test that title is generated from description."""
        event = FoodEvent(
            event_key="",
            description="Coffee arrives in Europe from the Ottoman Empire"
        )
        
        assert event.title != ""
        assert len(event.title) <= 70
        assert event.title in event.description

    def test_title_truncation_at_word_boundary(self):
        """Test that title truncates at word boundary, not mid-word."""
        long_desc = "This is a very long description that should be truncated at a word boundary and not cut off mid-word in the middle of something"
        
        event = FoodEvent(
            event_key="",
            description=long_desc
        )
        
        # Should not end with a hyphen or partial word
        assert not event.title.endswith("-")
        # Title should be reasonable length
        assert len(event.title) <= 70
        assert len(event.title) >= 20

    def test_title_respects_70_char_limit(self):
        """Test that title never exceeds 70 characters."""
        event = FoodEvent(
            event_key="",
            description="x" * 200  # Very long description
        )
        
        assert len(event.title) <= 70

    def test_title_handles_short_description(self):
        """Test that short descriptions become the full title."""
        short_desc = "Coffee arrives"
        
        event = FoodEvent(
            event_key="",
            description=short_desc
        )
        
        assert event.title == short_desc

    def test_title_handles_empty_description(self):
        """Test that empty description results in empty title."""
        event = FoodEvent(
            event_key="",
            title="Manual Title",
            description=""
        )
        
        # Manually set title should be preserved
        assert event.title == "Manual Title"

    def test_title_generation_with_special_characters(self):
        """Test title generation with special characters."""
        event = FoodEvent(
            event_key="",
            description="Coca-Cola's® expansion in the 1960s: A story of globalization"
        )
        
        assert len(event.title) <= 70
        # Should preserve special characters
        assert "-" in event.title or "Cola" in event.title


class TestFoodEventKeyGeneration:
    """Tests for event_key generation (T019a)."""
    
    def test_event_key_generation(self):
        """Test that event_key is generated as MD5 hash."""
        event = FoodEvent(
            event_key="",
            date_explicit=1847,
            title="First candy machine",
            description="Invented in Boston"
        )
        
        # Should be generated in __post_init__
        assert event.event_key != ""
        assert len(event.event_key) == 32  # MD5 is 32 hex chars

    def test_event_key_deterministic(self):
        """Test that same inputs produce same event_key."""
        event1 = FoodEvent(
            event_key="",
            date_explicit=1847,
            title="First candy machine",
            description="Invented in Boston"
        )
        
        event2 = FoodEvent(
            event_key="",
            date_explicit=1847,
            title="First candy machine",
            description="Invented in Boston"
        )
        
        assert event1.event_key == event2.event_key

    def test_event_key_different_for_different_events(self):
        """Test that different events have different keys."""
        event1 = FoodEvent(
            event_key="",
            date_explicit=1847,
            title="First candy machine",
            description="Event 1"
        )
        
        event2 = FoodEvent(
            event_key="",
            date_explicit=1850,
            title="First candy machine",
            description="Event 1"
        )
        
        assert event1.event_key != event2.event_key

    def test_event_key_includes_date(self):
        """Test that event_key changes with different dates."""
        # Same title/description, different dates should have different keys
        event_with_date1 = FoodEvent(
            event_key="",
            date_explicit=1847,
            title="Event",
            description="Same description"
        )
        
        event_with_date2 = FoodEvent(
            event_key="",
            date_explicit=1950,
            title="Event",
            description="Same description"
        )
        
        assert event_with_date1.event_key != event_with_date2.event_key

    def test_event_key_format_is_hex(self):
        """Test that event_key is valid hexadecimal."""
        event = FoodEvent(
            event_key="",
            date_explicit=1847,
            title="Test",
            description="Test"
        )
        
        # Should be valid hex string
        try:
            int(event.event_key, 16)
        except ValueError:
            pytest.fail("event_key is not valid hexadecimal")


class TestEventParserLogging:
    """Tests for undated event logging (T023a)."""
    
    def test_undated_event_logging(self):
        """Test that undated events are logged."""
        from strategies.timeline_of_food.date_extraction_strategies import EventParser
        from strategies.timeline_of_food.hierarchical_strategies import TextSection
        
        parser = EventParser()
        section = TextSection(
            name="Test Section",
            level=2,
            date_range_start=1800,
            date_range_end=1900,
            date_is_explicit=False,
            date_is_range=True,
            position=0,
            is_bc_start=False,
            is_bc_end=False,
            event_count=0
        )
        
        # Log an undated event
        parser._log_undated_event("Event without date", section)
        
        summary = parser.get_undated_summary()
        assert summary["total_undated"] == 1
        assert len(summary["events"]) == 1

    def test_undated_events_accumulate(self):
        """Test that multiple undated events are tracked."""
        from strategies.timeline_of_food.date_extraction_strategies import EventParser
        from strategies.timeline_of_food.hierarchical_strategies import TextSection
        
        parser = EventParser()
        section = TextSection(
            name="Test",
            level=2,
            date_range_start=1800,
            date_range_end=1900,
            date_is_explicit=False,
            date_is_range=True,
            position=0,
            is_bc_start=False,
            is_bc_end=False,
            event_count=0
        )
        
        # Log multiple undated events
        parser._log_undated_event("Event 1", section)
        parser._log_undated_event("Event 2", section)
        parser._log_undated_event("Event 3", section)
        
        summary = parser.get_undated_summary()
        assert summary["total_undated"] == 3
        assert len(summary["events"]) == 3

    def test_undated_event_metadata_captured(self):
        """Test that undated event metadata is captured."""
        from strategies.timeline_of_food.date_extraction_strategies import EventParser
        from strategies.timeline_of_food.hierarchical_strategies import TextSection
        
        parser = EventParser()
        section = TextSection(
            name="Medieval Period",
            level=2,
            date_range_start=1000,
            date_range_end=1500,
            date_is_explicit=False,
            date_is_range=True,
            position=5,
            is_bc_start=False,
            is_bc_end=False,
            event_count=0
        )
        
        parser._log_undated_event("Event description text", section)
        
        summary = parser.get_undated_summary()
        event = summary["events"][0]
        
        assert "text" in event
        assert "section" in event
        assert event["section"] == "Medieval Period"
        assert "section_date_range" in event


class TestTimelineOfFoodStrategyErrorHandling:
    """Tests for error handling (T024a)."""
    
    def test_malformed_html_handling(self, strategy):
        """Test parse() handles malformed HTML gracefully."""
        from strategies.strategy_base import FetchResult
        
        # Malformed HTML with unclosed tags
        strategy.html_content = "<html><body><h2>No span</h2><ul><li>Event</li>"
        fetch_result = FetchResult(strategy_name="TimelineOfFood", fetch_count=1)
        
        # Should not raise, should return ParseResult
        result = strategy.parse(fetch_result)
        assert result is not None

    def test_empty_section_handling(self, strategy):
        """Test that empty sections are handled."""
        from strategies.strategy_base import FetchResult
        
        strategy.html_content = """
        <html><body>
            <h2><span class='mw-headline'>Empty Section</span></h2>
            <h2><span class='mw-headline'>Another Section</span></h2>
        </body></html>
        """
        fetch_result = FetchResult(strategy_name="TimelineOfFood", fetch_count=1)
        
        result = strategy.parse(fetch_result)
        # Should handle empty sections gracefully
        assert isinstance(result.events, list)

    def test_missing_date_handling(self, strategy):
        """Test handling of events without parseable dates."""
        from strategies.strategy_base import FetchResult
        
        strategy.html_content = """
        <html><body>
            <h2><span class='mw-headline'>19th Century</span></h2>
            <ul>
                <li>Some event without a date</li>
                <li>Another undated event</li>
            </ul>
        </body></html>
        """
        fetch_result = FetchResult(strategy_name="TimelineOfFood", fetch_count=1)
        
        result = strategy.parse(fetch_result)
        
        # Should track undated events without raising
        assert "undated_events" in result.parse_metadata

    def test_special_characters_in_event_text(self, strategy):
        """Test handling of special characters in event text."""
        from strategies.strategy_base import FetchResult
        
        strategy.html_content = """
        <html><body>
            <h2><span class='mw-headline'>Modern Era</span></h2>
            <ul>
                <li>1990: Café® opens with café-au-lait® specialty drink</li>
                <li>2000: McDonald's™ expands globally</li>
            </ul>
        </body></html>
        """
        fetch_result = FetchResult(strategy_name="TimelineOfFood", fetch_count=1)
        
        result = strategy.parse(fetch_result)
        
        # Should handle special characters without errors
        assert isinstance(result.events, list)

    def test_unicode_handling(self, strategy):
        """Test handling of unicode characters."""
        from strategies.strategy_base import FetchResult
        
        strategy.html_content = """
        <html><body>
            <h2><span class='mw-headline'>中文 & 日本語</span></h2>
            <ul>
                <li>1847: Côté français événement</li>
                <li>1900: Αρχαίος Ελληνικός Ιστορία</li>
            </ul>
        </body></html>
        """
        fetch_result = FetchResult(strategy_name="TimelineOfFood", fetch_count=1)
        
        result = strategy.parse(fetch_result)
        
        # Should handle unicode without errors
        assert isinstance(result.events, list)

    def test_html_with_script_tags(self, strategy):
        """Test handling of HTML with script tags."""
        from strategies.strategy_base import FetchResult
        
        strategy.html_content = """
        <html><body>
            <script>alert('test');</script>
            <h2><span class='mw-headline'>Real Content</span></h2>
            <ul><li>1847: Event</li></ul>
        </body></html>
        """
        fetch_result = FetchResult(strategy_name="TimelineOfFood", fetch_count=1)
        
        result = strategy.parse(fetch_result)
        
        # Should handle script tags without executing them
        assert isinstance(result.events, list)
