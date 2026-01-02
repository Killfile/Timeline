"""
Unit tests for event_key computation module.

Tests ensure that event_key generation is:
- Deterministic (same input always produces same output)
- Unique (different events produce different keys)
- Stable (handles various input formats consistently)
"""

import pytest
from event_key import compute_event_key, compute_event_key_from_dict, validate_event_key


class TestComputeEventKey:
    """Tests for compute_event_key function."""
    
    def test_deterministic(self):
        """Same input should always produce same output."""
        key1 = compute_event_key("Battle of Hastings", 1066, 1066, "Norman conquest")
        key2 = compute_event_key("Battle of Hastings", 1066, 1066, "Norman conquest")
        assert key1 == key2
    
    def test_different_titles_produce_different_keys(self):
        """Different event titles should produce different keys."""
        key1 = compute_event_key("Battle of Hastings", 1066, 1066, "Norman conquest")
        key2 = compute_event_key("Battle of Waterloo", 1066, 1066, "Norman conquest")
        assert key1 != key2
    
    def test_different_dates_produce_different_keys(self):
        """Different dates should produce different keys."""
        key1 = compute_event_key("Battle of Hastings", 1066, 1066, "Norman conquest")
        key2 = compute_event_key("Battle of Hastings", 1067, 1067, "Norman conquest")
        assert key1 != key2
    
    def test_different_descriptions_produce_different_keys(self):
        """Different descriptions should produce different keys."""
        key1 = compute_event_key("Battle of Hastings", 1066, 1066, "Norman conquest")
        key2 = compute_event_key("Battle of Hastings", 1066, 1066, "Different description")
        assert key1 != key2
    
    def test_none_description_is_treated_as_empty(self):
        """None description should be treated as empty string."""
        key1 = compute_event_key("Battle of Hastings", 1066, 1066, None)
        key2 = compute_event_key("Battle of Hastings", 1066, 1066, "")
        assert key1 == key2
    
    def test_whitespace_is_normalized(self):
        """Leading/trailing whitespace should be normalized."""
        key1 = compute_event_key("  Battle of Hastings  ", 1066, 1066, "  Norman conquest  ")
        key2 = compute_event_key("Battle of Hastings", 1066, 1066, "Norman conquest")
        assert key1 == key2
    
    def test_empty_title_raises_error(self):
        """Empty title should raise ValueError."""
        with pytest.raises(ValueError, match="title must not be empty"):
            compute_event_key("", 1066, 1066, "Description")
    
    def test_whitespace_only_title_raises_error(self):
        """Whitespace-only title should raise ValueError."""
        with pytest.raises(ValueError, match="title must not be empty"):
            compute_event_key("   ", 1066, 1066, "Description")
    
    def test_none_title_raises_error(self):
        """None title should raise ValueError."""
        with pytest.raises(ValueError, match="title must not be empty"):
            compute_event_key(None, 1066, 1066, "Description")
    
    def test_returns_64_char_hex_string(self):
        """Should return 64-character hexadecimal string (SHA-256)."""
        key = compute_event_key("Battle of Hastings", 1066, 1066, "Norman conquest")
        assert len(key) == 64
        assert all(c in '0123456789abcdef' for c in key)
    
    def test_handles_special_characters(self):
        """Should handle special characters in title and description."""
        key = compute_event_key("Event & <Special> \"Chars\"", 1066, 1066, "Description with 'quotes'")
        assert len(key) == 64
    
    def test_handles_unicode(self):
        """Should handle Unicode characters."""
        key = compute_event_key("Événement français", 1066, 1066, "Description avec accents")
        assert len(key) == 64
    
    def test_handles_negative_years(self):
        """Should handle negative years (BC dates stored as negative)."""
        key = compute_event_key("Ancient Event", -500, -400, "BC event")
        assert len(key) == 64
    
    def test_span_events_produce_unique_keys(self):
        """Events with different end dates should produce different keys."""
        key1 = compute_event_key("World War II", 1939, 1945, "Global conflict")
        key2 = compute_event_key("World War II", 1939, 1946, "Global conflict")
        assert key1 != key2


class TestComputeEventKeyFromDict:
    """Tests for compute_event_key_from_dict convenience function."""
    
    def test_extracts_fields_from_dict(self):
        """Should extract fields from dictionary and compute key."""
        event = {
            'title': 'Moon Landing',
            'start_year': 1969,
            'end_year': 1969,
            'description': 'Apollo 11 lands on the moon'
        }
        key = compute_event_key_from_dict(event)
        assert len(key) == 64
    
    def test_same_as_direct_call(self):
        """Should produce same result as direct compute_event_key call."""
        event = {
            'title': 'Moon Landing',
            'start_year': 1969,
            'end_year': 1969,
            'description': 'Apollo 11 lands on the moon'
        }
        key1 = compute_event_key_from_dict(event)
        key2 = compute_event_key('Moon Landing', 1969, 1969, 'Apollo 11 lands on the moon')
        assert key1 == key2
    
    def test_handles_missing_description(self):
        """Should handle missing description field."""
        event = {
            'title': 'Moon Landing',
            'start_year': 1969,
            'end_year': 1969
        }
        key = compute_event_key_from_dict(event)
        assert len(key) == 64
    
    def test_raises_on_missing_required_fields(self):
        """Should raise KeyError if required fields are missing."""
        with pytest.raises(KeyError):
            compute_event_key_from_dict({'title': 'Moon Landing'})


class TestValidateEventKey:
    """Tests for validate_event_key function."""
    
    def test_valid_key(self):
        """Should return True for valid 64-char hex string."""
        key = compute_event_key("Battle of Hastings", 1066, 1066, "Norman conquest")
        assert validate_event_key(key) is True
    
    def test_valid_all_zeros(self):
        """Should return True for valid key with all zeros."""
        assert validate_event_key('0' * 64) is True
    
    def test_valid_all_f(self):
        """Should return True for valid key with all F's."""
        assert validate_event_key('f' * 64) is True
    
    def test_invalid_too_short(self):
        """Should return False for string shorter than 64 chars."""
        assert validate_event_key('a' * 63) is False
    
    def test_invalid_too_long(self):
        """Should return False for string longer than 64 chars."""
        assert validate_event_key('a' * 65) is False
    
    def test_invalid_non_hex_characters(self):
        """Should return False for non-hexadecimal characters."""
        invalid_key = 'g' * 64
        assert validate_event_key(invalid_key) is False
    
    def test_invalid_not_string(self):
        """Should return False for non-string types."""
        assert validate_event_key(123) is False
        assert validate_event_key(None) is False
        assert validate_event_key(['a' * 64]) is False
    
    def test_invalid_empty_string(self):
        """Should return False for empty string."""
        assert validate_event_key('') is False


class TestEventKeyStability:
    """Tests to ensure event_key remains stable across changes."""
    
    def test_same_event_after_reingestion(self):
        """Simulates same event being reingested - should get same key."""
        # First ingestion
        key1 = compute_event_key(
            "Apollo 11",
            1969,
            1969,
            "First crewed mission to land on the Moon"
        )
        
        # Second ingestion (same data)
        key2 = compute_event_key(
            "Apollo 11",
            1969,
            1969,
            "First crewed mission to land on the Moon"
        )
        
        assert key1 == key2
    
    def test_changed_event_gets_different_key(self):
        """Event with changed description should get different key (expected orphaning)."""
        key1 = compute_event_key(
            "Apollo 11",
            1969,
            1969,
            "First crewed mission to land on the Moon"
        )
        
        # Wikipedia updates description
        key2 = compute_event_key(
            "Apollo 11",
            1969,
            1969,
            "First crewed mission to land on the Moon. Updated description."
        )
        
        assert key1 != key2
