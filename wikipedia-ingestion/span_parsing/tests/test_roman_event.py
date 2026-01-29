"""Unit tests for RomanEvent domain model"""

import pytest
from datetime import datetime
from span_parsing.roman_event import RomanEvent, EventCategory
from span_parsing.span import SpanPrecision
from span_parsing.table_row_date_parser import ConfidenceLevel


class TestRomanEventCreation:
    """Tests for creating RomanEvent instances."""
    
    def test_minimal_event(self):
        """Test creating event with required fields only"""
        event = RomanEvent(title="Rome Founded", year=-753)
        assert event.title == "Rome Founded"
        assert event.year == -753
        assert event.is_bc == False  # We don't set is_bc, it defaults to False
        assert event.month is None
        assert event.day is None
    
    def test_event_with_all_fields(self):
        """Test creating event with all fields"""
        now = datetime.utcnow()
        event = RomanEvent(
            title="Augustus Becomes Emperor",
            year=-27,
            month=1,
            day=16,
            is_bc=True,
            description="Octavian takes power and becomes Augustus",
            confidence=ConfidenceLevel.EXPLICIT,
            precision=SpanPrecision.EXACT,
            category=EventCategory.POLITICAL,
            source="Timeline of Roman History",
            tags=["emperor", "succession"],
            created_at=now,
            rowspan_inherited=False
        )
        
        assert event.title == "Augustus Becomes Emperor"
        assert event.year == -27
        assert event.is_bc == True
        assert event.month == 1
        assert event.day == 16
        assert event.description == "Octavian takes power and becomes Augustus"
        assert event.category == EventCategory.POLITICAL
        assert "emperor" in event.tags
    
    def test_empty_title_raises(self):
        """Test that empty title raises ValueError"""
        with pytest.raises(ValueError):
            RomanEvent(title="", year=100)
    
    def test_whitespace_title_raises(self):
        """Test that whitespace-only title raises ValueError"""
        with pytest.raises(ValueError):
            RomanEvent(title="   ", year=100)
    
    def test_invalid_year_raises(self):
        """Test that out-of-range year raises ValueError"""
        with pytest.raises(ValueError):
            RomanEvent(title="Event", year=100000)
    
    def test_invalid_month_raises(self):
        """Test that invalid month raises ValueError"""
        with pytest.raises(ValueError):
            RomanEvent(title="Event", year=100, month=13)
    
    def test_invalid_day_raises(self):
        """Test that invalid day raises ValueError"""
        with pytest.raises(ValueError):
            RomanEvent(title="Event", year=100, day=32)


class TestDateFormatting:
    """Tests for date_string property."""
    
    def test_exact_date(self):
        """Test exact date formatting"""
        event = RomanEvent(
            title="Rome Founded",
            year=-753,
            month=4,
            day=21,
            is_bc=True
        )
        assert event.date_string == "21 April 753 BC"
    
    def test_month_year_only(self):
        """Test month and year formatting"""
        event = RomanEvent(
            title="Event",
            year=1066,
            month=10,
            is_bc=False
        )
        assert event.date_string == "October 1066 AD"
    
    def test_year_only(self):
        """Test year-only formatting"""
        event = RomanEvent(
            title="Event",
            year=-100,
            is_bc=True
        )
        assert event.date_string == "100 BC"
    
    def test_approximate_date(self):
        """Test approximate date prefix"""
        event = RomanEvent(
            title="Event",
            year=-1000,
            is_bc=True,
            confidence=ConfidenceLevel.APPROXIMATE
        )
        assert event.date_string.startswith("c. ")
        assert "1000 BC" in event.date_string
    
    def test_uncertain_date(self):
        """Test uncertain date prefix"""
        event = RomanEvent(
            title="Event",
            year=500,
            confidence=ConfidenceLevel.UNCERTAIN
        )
        assert event.date_string.startswith("? ")
        assert "500 AD" in event.date_string
    
    def test_month_names_all(self):
        """Test all month names format correctly"""
        months = [
            (1, "January"), (2, "February"), (3, "March"), (4, "April"),
            (5, "May"), (6, "June"), (7, "July"), (8, "August"),
            (9, "September"), (10, "October"), (11, "November"), (12, "December")
        ]
        for month_num, month_name in months:
            event = RomanEvent(
                title="Event",
                year=100,
                month=month_num
            )
            assert month_name in event.date_string


class TestPeriodClassification:
    """Tests for historical period classification."""
    
    def test_legendary_period(self):
        """Test events 753 BC and earlier are legendary"""
        event753 = RomanEvent(title="Rome Founded", year=-753, is_bc=True)
        event754 = RomanEvent(title="Before Rome", year=-754, is_bc=True)
        
        assert event753.is_legendary == True
        assert event754.is_legendary == True
        assert event753.period_name() == "Legendary Period"
    
    def test_early_republic_period(self):
        """Test early republic (509-27 BC)"""
        event = RomanEvent(title="Event", year=-100, is_bc=True)
        assert event.is_early_republic == True
        assert event.period_name() == "Early Republic"
        
        # Boundary: not in early republic if >= 27 BC
        event27 = RomanEvent(title="Augustus", year=-27, is_bc=True)
        assert event27.is_early_republic == False
    
    def test_imperial_period(self):
        """Test imperial period (27 BC - 476 AD)"""
        event = RomanEvent(title="Event", year=100)
        assert event.is_imperial == True
        assert event.period_name() == "Imperial Period"
        
        # Boundary: 27 BC is start of imperial
        event27bc = RomanEvent(title="Augustus", year=-27, is_bc=True)
        assert event27bc.is_imperial == True
        
        # Boundary: 476 AD is end
        event476 = RomanEvent(title="Fall", year=476)
        assert event476.is_imperial == True
    
    def test_byzantine_period(self):
        """Test Byzantine period (476-1453 AD)"""
        event = RomanEvent(title="Event", year=1000)
        assert event.is_byzantine == True
        assert event.period_name() == "Byzantine Period"
        
        # 476 is not included (just after imperial)
        event476 = RomanEvent(title="Fall", year=476)
        assert event476.is_byzantine == False
        
        # 1453 is end
        event1453 = RomanEvent(title="Fall of Constantinople", year=1453)
        assert event1453.is_byzantine == True


class TestStringRepresentations:
    """Tests for string representations."""
    
    def test_str_representation(self):
        """Test __str__ method"""
        event = RomanEvent(
            title="Rome Founded",
            year=-753,
            month=4,
            day=21,
            is_bc=True
        )
        assert str(event) == "21 April 753 BC: Rome Founded"
    
    def test_repr_representation(self):
        """Test __repr__ method"""
        event = RomanEvent(
            title="Event",
            year=-100,
            is_bc=True
        )
        repr_str = repr(event)
        assert "RomanEvent" in repr_str
        assert "Event" in repr_str
        assert "year=-100" in repr_str


class TestDictConversion:
    """Tests for to_dict method."""
    
    def test_to_dict_basic(self):
        """Test basic to_dict conversion"""
        event = RomanEvent(
            title="Rome Founded",
            year=-753,
            is_bc=True,
            category=EventCategory.FOUNDING
        )
        d = event.to_dict()
        
        assert d["title"] == "Rome Founded"
        assert d["year"] == -753
        assert d["is_bc"] == True
        assert d["category"] == "founding"
    
    def test_to_dict_with_all_fields(self):
        """Test to_dict with all fields"""
        now = datetime(2024, 1, 1, 12, 0, 0)
        event = RomanEvent(
            id="event123",
            title="Event",
            year=100,
            month=6,
            day=15,
            description="Test event",
            confidence=ConfidenceLevel.EXPLICIT,
            precision=SpanPrecision.EXACT,
            category=EventCategory.POLITICAL,
            source="Test Source",
            tags=["test", "example"],
            created_at=now,
            rowspan_inherited=True
        )
        d = event.to_dict()
        
        assert d["id"] == "event123"
        assert d["title"] == "Event"
        assert d["month"] == 6
        assert d["day"] == 15
        assert d["description"] == "Test event"
        assert d["confidence"] == "explicit"
        assert d["precision"] == 1000.0  # EXACT precision
        assert d["category"] == "political"
        assert d["source"] == "Test Source"
        assert "test" in d["tags"]
        assert d["created_at"] == "2024-01-01T12:00:00"
        assert d["rowspan_inherited"] == True
    
    def test_to_dict_date_string(self):
        """Test to_dict includes properly formatted date_string"""
        event = RomanEvent(
            title="Event",
            year=-100,
            month=3,
            day=20,
            is_bc=True
        )
        d = event.to_dict()
        assert d["date_string"] == "20 March 100 BC"


class TestEventCategories:
    """Tests for event categories."""
    
    def test_all_categories_exist(self):
        """Test that all expected categories exist"""
        expected = {
            "founding", "republic", "conflicts", "political",
            "cultural", "religious", "economic", "military",
            "succession", "natural", "social", "administrative", "unknown"
        }
        actual = {ec.value for ec in EventCategory}
        assert expected == actual
    
    def test_category_assignment(self):
        """Test assigning different categories"""
        categories = [
            EventCategory.FOUNDING,
            EventCategory.MILITARY,
            EventCategory.POLITICAL,
            EventCategory.RELIGIOUS
        ]
        for cat in categories:
            event = RomanEvent(
                title="Event",
                year=100,
                category=cat
            )
            assert event.category == cat


class TestEventWithRomanNumbers:
    """Tests for events in typical Roman history periods."""
    
    def test_founding_of_rome(self):
        """Test creating a Rome founding event"""
        event = RomanEvent(
            title="Founding of Rome",
            year=-753,
            month=4,
            day=21,
            is_bc=True,
            category=EventCategory.FOUNDING,
            confidence=ConfidenceLevel.LEGENDARY,
            source="Wikipedia: Timeline of Roman History"
        )
        
        assert event.is_legendary == True
        assert event.confidence == ConfidenceLevel.LEGENDARY
        assert str(event) == "21 April 753 BC: Founding of Rome"
    
    def test_republic_event(self):
        """Test a republic-era event"""
        event = RomanEvent(
            title="First Punic War",
            year=-264,
            is_bc=True,
            category=EventCategory.CONFLICTS,
            description="First major war between Rome and Carthage"
        )
        
        assert event.is_early_republic == True
        assert event.period_name() == "Early Republic"
    
    def test_imperial_event(self):
        """Test an imperial-era event"""
        event = RomanEvent(
            title="Augustus Becomes Emperor",
            year=-27,
            month=1,
            day=16,
            is_bc=True,
            category=EventCategory.SUCCESSION,
            description="Octavian takes the title Augustus and becomes first emperor"
        )
        
        assert event.is_imperial == True
        assert event.period_name() == "Imperial Period"
    
    def test_byzantine_event(self):
        """Test a Byzantine-era event"""
        event = RomanEvent(
            title="Fall of Constantinople",
            year=1453,
            month=5,
            day=29,
            category=EventCategory.CONFLICTS,
            description="Ottoman conquest of Constantinople ends Byzantine Empire"
        )
        
        assert event.is_byzantine == True
        assert event.period_name() == "Byzantine Period"


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""
    
    def test_event_with_year_zero(self):
        """Test that year 0 works (though historically doesn't exist)"""
        # Year 0 doesn't exist historically (goes from 1 BC to 1 AD)
        # but we should still accept it as a value
        event = RomanEvent(title="Non-existent year", year=0)
        assert event.year == 0
    
    def test_ad_dates(self):
        """Test AD (positive) year dates"""
        event = RomanEvent(
            title="Fire of Rome",
            year=64,
            is_bc=False,
            category=EventCategory.NATURAL
        )
        assert event.year == 64
        assert event.is_bc == False
        assert "64 AD" in event.date_string
    
    def test_event_copying(self):
        """Test creating similar events"""
        event1 = RomanEvent(
            title="Event",
            year=-100,
            month=6,
            is_bc=True,
            category=EventCategory.POLITICAL
        )
        
        # Create "copy" with different year
        event2 = RomanEvent(
            title="Event",
            year=-50,
            month=6,
            is_bc=True,
            category=EventCategory.POLITICAL
        )
        
        assert event1.year != event2.year
        assert event1.title == event2.title
    
    def test_event_with_tags(self):
        """Test events with multiple tags"""
        event = RomanEvent(
            title="Event",
            year=100,
            tags=["war", "military", "conquest", "expansion"]
        )
        assert len(event.tags) == 4
        assert "war" in event.tags
        assert "expansion" in event.tags


class TestEventComparison:
    """Tests for logical event ordering."""
    
    def test_events_chronological_comparison(self):
        """Test creating events in chronological order"""
        events = [
            RomanEvent(title="A", year=-753, is_bc=True),
            RomanEvent(title="B", year=-509, is_bc=True),
            RomanEvent(title="C", year=-100, is_bc=True),
            RomanEvent(title="D", year=1),
            RomanEvent(title="E", year=500),
            RomanEvent(title="F", year=1453),
        ]
        
        # Verify they can be created in order
        for i, event in enumerate(events):
            assert event.title == chr(65 + i)  # A, B, C, D, E, F


class TestRomanEventConversion:
    """Tests for converting RomanEvent to HistoricalEvent."""
    
    def test_convert_exact_date_to_historical_event(self):
        """Test converting exact date RomanEvent to HistoricalEvent"""
        roman_event = RomanEvent(
            title="Rome Founded",
            year=-753,
            month=4,
            day=21,
            is_bc=True,
            description="Founding of Rome",
            confidence=ConfidenceLevel.EXPLICIT,
            category=EventCategory.FOUNDING
        )
        
        hist_event = roman_event.to_historical_event(
            url="https://en.wikipedia.org/wiki/Timeline_of_Roman_History",
            span_match_notes="753 BC, April 21"
        )
        
        # Verify conversion preserves core data
        assert hist_event.title == "Rome Founded"
        assert hist_event.description == "Founding of Rome"
        assert hist_event.start_year == 753
        assert hist_event.end_year == 753
        assert hist_event.start_month == 4
        assert hist_event.start_day == 21
        assert hist_event.end_month == 4
        assert hist_event.end_day == 21
        assert hist_event.is_bc_start == True
        assert hist_event.is_bc_end == True
        assert hist_event.category == "founding"
        assert hist_event.url == "https://en.wikipedia.org/wiki/Timeline_of_Roman_History"
        assert hist_event.span_match_notes == "753 BC, April 21"
    
    def test_convert_year_only_to_historical_event(self):
        """Test converting year-only RomanEvent to HistoricalEvent"""
        roman_event = RomanEvent(
            title="Augustus",
            year=-27,
            is_bc=True,
            category=EventCategory.POLITICAL
        )
        
        hist_event = roman_event.to_historical_event(
            url="https://example.com",
            span_match_notes="27 BC"
        )
        
        assert hist_event.start_year == 27
        assert hist_event.end_year == 27
        assert hist_event.start_month is None
        assert hist_event.start_day is None
        assert hist_event.is_bc_start == True
    
    def test_convert_ad_date_to_historical_event(self):
        """Test converting AD date RomanEvent to HistoricalEvent"""
        roman_event = RomanEvent(
            title="Fall of Rome",
            year=476,
            category=EventCategory.CONFLICTS
        )
        
        hist_event = roman_event.to_historical_event(url="https://example.com")
        
        assert hist_event.start_year == 476
        assert hist_event.is_bc_start == False
        assert hist_event.is_bc_end == False
    
    def test_confidence_maps_to_precision(self):
        """Test that confidence levels map to precision values"""
        confidence_mapping = [
            (ConfidenceLevel.EXPLICIT, 100.0),
            (ConfidenceLevel.INFERRED, 75.0),
            (ConfidenceLevel.APPROXIMATE, 50.0),
            (ConfidenceLevel.UNCERTAIN, 25.0),
            (ConfidenceLevel.LEGENDARY, 10.0),
        ]
        
        for confidence, expected_precision in confidence_mapping:
            roman_event = RomanEvent(
                title="Test",
                year=100,
                confidence=confidence
            )
            hist_event = roman_event.to_historical_event(url="https://example.com")
            assert hist_event.precision == expected_precision
    
    def test_debug_extraction_metadata(self):
        """Test that debug extraction data is preserved"""
        roman_event = RomanEvent(
            id="test-id-123",
            title="Test",
            year=-100,
            is_bc=True,
            rowspan_inherited=True,
            confidence=ConfidenceLevel.INFERRED,
            precision=SpanPrecision.MONTH_ONLY
        )
        
        hist_event = roman_event.to_historical_event(url="https://example.com")
        
        assert hist_event._debug_extraction is not None
        assert hist_event._debug_extraction["roman_event_id"] == "test-id-123"
        assert hist_event._debug_extraction["rowspan_inherited"] == True
        assert hist_event._debug_extraction["confidence"] == "inferred"
        assert hist_event._debug_extraction["span_precision"] == 1.0
    
    def test_roundtrip_conversion(self):
        """Test that converted HistoricalEvent can be serialized to dict"""
        roman_event = RomanEvent(
            title="Event",
            year=1066,
            month=10,
            day=14,
            description="Battle of Hastings",
            category=EventCategory.MILITARY,
            tags=["battle", "normandy"]
        )
        
        hist_event = roman_event.to_historical_event(
            url="https://en.wikipedia.org/wiki/Timeline_of_Roman_History"
        )
        
        # Verify it can be converted to dict (for JSON export)
        event_dict = hist_event.to_dict()
        
        assert event_dict["title"] == "Event"
        assert event_dict["start_year"] == 1066
        assert event_dict["start_month"] == 10
        assert event_dict["start_day"] == 14
        assert event_dict["is_bc_start"] == False
        assert event_dict["description"] == "Battle of Hastings"
        assert event_dict["category"] == "military"
        assert event_dict["url"] == "https://en.wikipedia.org/wiki/Timeline_of_Roman_History"
