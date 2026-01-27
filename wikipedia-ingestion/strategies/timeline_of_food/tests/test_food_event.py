"""Unit tests for FoodEvent dataclass."""

import pytest
from strategies.timeline_of_food.food_event import FoodEvent
from historical_event import HistoricalEvent


class TestFoodEvent:
    """Test suite for FoodEvent class."""
    
    def test_event_key_generation(self):
        """Test that event_key is generated deterministically."""
        event1 = FoodEvent(
            event_key="",
            date_explicit=1516,
            title="First coffee in Europe",
            description="Coffee arrives in Europe from Arabia"
        )
        
        event2 = FoodEvent(
            event_key="",
            date_explicit=1516,
            title="First coffee in Europe",
            description="Coffee arrives in Europe from Arabia"
        )
        
        # Same input should produce same key
        assert event1.event_key == event2.event_key
        assert len(event1.event_key) == 32  # MD5 hash is 32 chars
    
    def test_event_key_different_dates(self):
        """Test that different dates produce different keys."""
        event1 = FoodEvent(
            event_key="",
            date_explicit=1516,
            title="Event",
            description="Description"
        )
        
        event2 = FoodEvent(
            event_key="",
            date_explicit=1517,
            title="Event",
            description="Description"
        )
        
        assert event1.event_key != event2.event_key
    
    def test_title_generation_short_description(self):
        """Test title generation for short descriptions."""
        event = FoodEvent(
            event_key="",
            description="Coffee arrives in Europe"
        )
        
        assert event.title == "Coffee arrives in Europe"
    
    def test_title_generation_long_description(self):
        """Test title generation truncates at word boundary."""
        long_desc = "This is a very long description that exceeds the maximum allowed length of seventy characters and should be truncated at a word boundary"
        
        event = FoodEvent(
            event_key="",
            description=long_desc
        )
        
        assert len(event.title) <= 70
        assert len(event.title) >= 50
        assert not event.title.endswith(' ')  # Should not end with space
    
    def test_title_generation_no_space_boundary(self):
        """Test title generation when no space in 50-70 range."""
        # Create description with no spaces near boundary
        desc = "A" * 45 + "B" * 30 + " rest of text"
        
        event = FoodEvent(
            event_key="",
            description=desc
        )
        
        # Should hard truncate at 70
        assert len(event.title) == 70
    
    def test_to_historical_event_explicit_date(self):
        """Test conversion to HistoricalEvent with explicit date."""
        food_event = FoodEvent(
            event_key="abc123",
            date_explicit=1516,
            title="Coffee in Europe",
            description="Coffee arrives in Europe from Arabia",
            span_match_notes="YEAR_WITH_EXPLICIT_ERA",
            precision=1.0
        )
        
        hist_event = food_event.to_historical_event()
        
        assert isinstance(hist_event, HistoricalEvent)
        assert hist_event.title == "Coffee in Europe"
        assert hist_event.description == "Coffee arrives in Europe from Arabia"
        assert hist_event.start_year == 1516
        assert hist_event.end_year == 1516
        assert hist_event.is_bc_start is False
        assert hist_event.is_bc_end is False
        assert hist_event.precision == 1.0
        assert hist_event.category == "Food History"
        assert hist_event.url == "https://en.wikipedia.org/wiki/Timeline_of_food"
    
    def test_to_historical_event_date_range(self):
        """Test conversion with date range."""
        food_event = FoodEvent(
            event_key="abc123",
            date_range_start=1500,
            date_range_end=1600,
            title="16th century event",
            description="Something happened",
            span_match_notes="CENTURY",
            precision=0.7
        )
        
        hist_event = food_event.to_historical_event()
        
        assert hist_event.start_year == 1500
        assert hist_event.end_year == 1600
        assert hist_event.weight == (1600 - 1500 + 1) * 365  # Duration in days
    
    def test_to_historical_event_bc_dates(self):
        """Test conversion with BC dates."""
        food_event = FoodEvent(
            event_key="abc123",
            date_range_start=8000,
            date_range_end=5000,
            is_bc_start=True,
            is_bc_end=True,
            title="Prehistoric event",
            description="Agriculture begins",
            span_match_notes="YEAR_RANGE",
            precision=0.8
        )
        
        hist_event = food_event.to_historical_event()
        
        assert hist_event.start_year == 8000
        assert hist_event.end_year == 5000
        assert hist_event.is_bc_start is True
        assert hist_event.is_bc_end is True
    
    def test_to_historical_event_negative_years_converted(self):
        """Test that negative years are converted to positive with BC flag."""
        food_event = FoodEvent(
            event_key="abc123",
            date_range_start=-8000,  # Negative year
            date_range_end=-5000,
            title="Prehistoric event",
            description="Agriculture begins",
            span_match_notes="YEAR_RANGE",
            precision=0.8
        )
        
        hist_event = food_event.to_historical_event()
        
        assert hist_event.start_year == 8000  # Converted to positive
        assert hist_event.end_year == 5000
        assert hist_event.is_bc_start is True  # BC flag set
        assert hist_event.is_bc_end is True
    
    def test_to_historical_event_section_fallback(self):
        """Test that section date range is used as fallback."""
        food_event = FoodEvent(
            event_key="abc123",
            section_date_range_start=1800,
            section_date_range_end=1900,
            title="Undated 19th century event",
            description="Something happened",
            span_match_notes="FALLBACK",
            precision=0.5
        )
        
        hist_event = food_event.to_historical_event()
        
        assert hist_event.start_year == 1800
        assert hist_event.end_year == 1900
    
    def test_category_always_food_history(self):
        """Test that category is always 'Food History'."""
        food_event = FoodEvent(
            event_key="abc123",
            date_explicit=2000,
            title="Event",
            description="Description",
            food_category="Bread",  # This field is for tracking only
        )
        
        hist_event = food_event.to_historical_event()
        
        assert hist_event.category == "Food History"
    
    def test_source_is_timeline_of_food(self):
        """Test that source defaults to 'Timeline of Food'."""
        event = FoodEvent(
            event_key="",
            description="Event description"
        )
        
        assert event.source == "Timeline of Food"
    
    def test_confidence_level_defaults(self):
        """Test default confidence level."""
        event = FoodEvent(
            event_key="",
            description="Event description"
        )
        
        assert event.confidence_level == "explicit"
    
    def test_wikipedia_links_tracking(self):
        """Test that Wikipedia links can be tracked."""
        event = FoodEvent(
            event_key="",
            description="Event",
            wikipedia_links=["Coffee", "Arabia", "Europe"]
        )
        
        assert len(event.wikipedia_links) == 3
        assert "Coffee" in event.wikipedia_links
    
    def test_external_references_tracking(self):
        """Test that citation references can be tracked."""
        event = FoodEvent(
            event_key="",
            description="Event",
            external_references=[1, 2, 3]
        )
        
        assert event.external_references == [1, 2, 3]
    
    def test_source_format_tracking(self):
        """Test that source format can be tracked."""
        event = FoodEvent(
            event_key="",
            description="Event",
            source_format="table"
        )
        
        assert event.source_format == "table"
    
    def test_parsing_notes_tracking(self):
        """Test that parsing notes can be tracked."""
        event = FoodEvent(
            event_key="",
            description="Event",
            parsing_notes="Date inferred from section context"
        )
        
        assert event.parsing_notes == "Date inferred from section context"
