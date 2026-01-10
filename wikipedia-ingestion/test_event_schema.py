"""Tests for canonical event schema.

Verifies that:
1. CanonicalEvent class can be instantiated and serialized
2. from_span_dict helper correctly flattens nested span data
3. validate_canonical_event catches schema violations
"""

import pytest
from event_schema import CanonicalEvent, validate_canonical_event


def test_canonical_event_basic():
    """Test basic CanonicalEvent instantiation and serialization."""
    event = CanonicalEvent(
        title="Industrial Age",
        description="Period of industrialization",
        url="https://en.wikipedia.org/wiki/Industrial_Age",
        start_year=1760,
        end_year=1970,
        is_bc_start=False,
        is_bc_end=False,
        weight=76285,  # ~210 years * 365 days
        precision=365.0,
        category="Technological periods",
    )
    
    event_dict = event.to_dict()
    
    # Verify all required fields present
    assert event_dict["title"] == "Industrial Age"
    assert event_dict["description"] == "Period of industrialization"
    assert event_dict["url"] == "https://en.wikipedia.org/wiki/Industrial_Age"
    assert event_dict["start_year"] == 1760
    assert event_dict["end_year"] == 1970
    assert event_dict["is_bc_start"] is False
    assert event_dict["is_bc_end"] is False
    assert event_dict["weight"] == 76285
    assert event_dict["precision"] == 365.0
    
    # Verify optional fields
    assert event_dict["category"] == "Technological periods"
    assert event_dict["start_month"] is None
    assert event_dict["start_day"] is None
    assert event_dict["end_month"] is None
    assert event_dict["end_day"] is None
    assert event_dict["pageid"] is None


def test_canonical_event_with_all_fields():
    """Test CanonicalEvent with all optional fields populated."""
    event = CanonicalEvent(
        title="Battle of Actium",
        description="Naval battle between Octavian and Mark Antony",
        url="https://en.wikipedia.org/wiki/Battle_of_Actium",
        start_year=31,
        end_year=31,
        start_month=9,
        start_day=2,
        end_month=9,
        end_day=2,
        is_bc_start=True,
        is_bc_end=True,
        weight=1,
        precision=1.0,
        category="Roman history",
        pageid=31928,
        _debug_extraction={"method": "test", "notes": "example"},
    )
    
    event_dict = event.to_dict()
    
    assert event_dict["start_month"] == 9
    assert event_dict["start_day"] == 2
    assert event_dict["end_month"] == 9
    assert event_dict["end_day"] == 2
    assert event_dict["pageid"] == 31928
    assert event_dict["_debug_extraction"]["method"] == "test"


def test_from_span_dict_flat():
    """Test from_span_dict with already-flat span data."""
    span_dict = {
        "start_year": 1066,
        "end_year": 1066,
        "start_month": 10,
        "start_day": 14,
        "end_month": 10,
        "end_day": 14,
        "start_year_is_bc": False,
        "end_year_is_bc": False,
        "weight": 1,
        "precision": 1.0,
    }
    
    event = CanonicalEvent.from_span_dict(
        title="Battle of Hastings",
        description="Norman conquest of England",
        url="https://en.wikipedia.org/wiki/Battle_of_Hastings",
        span_dict=span_dict,
        category="Medieval battles",
        pageid=4775,
    )
    
    assert event.title == "Battle of Hastings"
    assert event.start_year == 1066
    assert event.start_month == 10
    assert event.start_day == 14
    assert event.is_bc_start is False
    assert event.weight == 1


def test_from_span_dict_bc_years():
    """Test from_span_dict with BC years."""
    span_dict = {
        "start_year": 753,
        "end_year": 753,
        "start_month": 4,
        "start_day": 21,
        "end_month": 4,
        "end_day": 21,
        "start_year_is_bc": True,
        "end_year_is_bc": True,
        "weight": 1,
        "precision": 1.0,
    }
    
    event = CanonicalEvent.from_span_dict(
        title="Founding of Rome",
        description="Traditional founding date of Rome",
        url="https://en.wikipedia.org/wiki/Founding_of_Rome",
        span_dict=span_dict,
        category="Ancient Rome",
    )
    
    assert event.start_year == 753
    assert event.is_bc_start is True
    assert event.is_bc_end is True


def test_validate_canonical_event_valid():
    """Test validation passes for valid event dict."""
    event_dict = {
        "title": "Test Event",
        "description": "Test description",
        "url": "https://example.com",
        "start_year": 2000,
        "end_year": 2000,
        "is_bc_start": False,
        "is_bc_end": False,
        "weight": 365,
        "precision": 365.0,
    }
    
    is_valid, error = validate_canonical_event(event_dict)
    assert is_valid
    assert error == ""


def test_validate_canonical_event_missing_fields():
    """Test validation fails for missing required fields."""
    event_dict = {
        "title": "Test Event",
        "description": "Test description",
        # Missing url, start_year, end_year, etc.
    }
    
    is_valid, error = validate_canonical_event(event_dict)
    assert not is_valid
    assert "Missing required fields" in error


def test_validate_canonical_event_nested_span():
    """Test validation rejects nested span object (non-canonical)."""
    event_dict = {
        "title": "Test Event",
        "description": "Test description",
        "url": "https://example.com",
        "span": {  # Should NOT have nested span
            "start_year": 2000,
            "end_year": 2000,
            "is_bc_start": False,
            "is_bc_end": False,
            "weight": 365,
            "precision": 365.0,
        },
    }
    
    is_valid, error = validate_canonical_event(event_dict)
    assert not is_valid
    assert "nested 'span' object" in error


def test_canonical_event_truncation():
    """Test that very long titles/descriptions can be created (truncation is caller's responsibility)."""
    long_title = "A" * 600
    long_desc = "B" * 600
    
    # CanonicalEvent doesn't enforce length limits - that's the caller's job
    event = CanonicalEvent(
        title=long_title,
        description=long_desc,
        url="https://example.com",
        start_year=2000,
        end_year=2000,
        is_bc_start=False,
        is_bc_end=False,
        weight=365,
        precision=365.0,
    )
    
    # Just verify it can be created
    assert len(event.title) == 600
    assert len(event.description) == 600
