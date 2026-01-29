"""
Unit tests for timeline_common.event_key module

Tests the SHA-256 event key computation, validation, and idempotency
across multiple runs to ensure deterministic deduplication.
"""

import pytest
from timeline_common.event_key import (
    compute_event_key,
    compute_event_key_from_dict,
    validate_event_key,
)


class TestComputeEventKey:
    """Tests for compute_event_key function"""

    def test_compute_event_key_with_all_fields(self):
        """Test event key computation with all fields populated"""
        key = compute_event_key(
            title="Battle of Hastings",
            start_year=1066,
            end_year=1066,
            description="Norman conquest of England"
        )
        assert isinstance(key, str)
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_compute_event_key_without_description(self):
        """Test event key computation with optional description field None"""
        key = compute_event_key(
            title="Battle of Hastings",
            start_year=1066,
            end_year=1066
        )
        assert isinstance(key, str)
        assert len(key) == 64

    def test_compute_event_key_idempotency(self):
        """Test that identical inputs always produce identical keys"""
        key1 = compute_event_key(
            title="Moon Landing",
            start_year=1969,
            end_year=1969,
            description="Apollo 11"
        )
        key2 = compute_event_key(
            title="Moon Landing",
            start_year=1969,
            end_year=1969,
            description="Apollo 11"
        )
        assert key1 == key2

    def test_compute_event_key_sensitivity_to_title(self):
        """Test that different titles produce different keys"""
        key1 = compute_event_key("Battle of Hastings", 1066, 1066, "")
        key2 = compute_event_key("Battle of Marathon", 1066, 1066, "")
        assert key1 != key2

    def test_compute_event_key_sensitivity_to_year(self):
        """Test that different years produce different keys"""
        key1 = compute_event_key("Battle", 1066, 1066, "")
        key2 = compute_event_key("Battle", 1067, 1067, "")
        assert key1 != key2

    def test_compute_event_key_sensitivity_to_description(self):
        """Test that different descriptions produce different keys"""
        key1 = compute_event_key("Battle", 1066, 1066, "Norman victory")
        key2 = compute_event_key("Battle", 1066, 1066, "Saxon defeat")
        assert key1 != key2

    def test_compute_event_key_year_range(self):
        """Test event key with multi-year event"""
        key = compute_event_key(
            title="World War II",
            start_year=1939,
            end_year=1945,
            description="Global conflict"
        )
        assert isinstance(key, str)
        assert len(key) == 64

    def test_compute_event_key_bc_dates(self):
        """Test event key with BC dates (negative years)"""
        key = compute_event_key(
            title="Rome Founded",
            start_year=-753,
            end_year=-753,
            description="753 BC"
        )
        assert isinstance(key, str)
        assert len(key) == 64

    def test_compute_event_key_empty_description(self):
        """Test that empty description string is treated same as None"""
        key1 = compute_event_key("Battle", 1066, 1066, "")
        key2 = compute_event_key("Battle", 1066, 1066, None)
        assert key1 == key2

    def test_compute_event_key_whitespace_trimmed(self):
        """Test that whitespace is trimmed from title and description"""
        key1 = compute_event_key("  Battle  ", 1066, 1066, "  Norman  ")
        key2 = compute_event_key("Battle", 1066, 1066, "Norman")
        assert key1 == key2

    def test_compute_event_key_empty_title_raises(self):
        """Test that empty title raises ValueError"""
        with pytest.raises(ValueError, match="Event title must not be empty"):
            compute_event_key("", 1066, 1066, "")

    def test_compute_event_key_none_title_raises(self):
        """Test that None title raises ValueError"""
        with pytest.raises(ValueError, match="Event title must not be empty"):
            compute_event_key(None, 1066, 1066, "")

    def test_compute_event_key_whitespace_only_title_raises(self):
        """Test that whitespace-only title raises ValueError"""
        with pytest.raises(ValueError, match="Event title must not be empty"):
            compute_event_key("   ", 1066, 1066, "")


class TestComputeEventKeyFromDict:
    """Tests for compute_event_key_from_dict function"""

    def test_compute_event_key_from_dict_with_all_fields(self):
        """Test event key computation from dict with all fields"""
        event = {
            'title': 'Battle of Hastings',
            'start_year': 1066,
            'end_year': 1066,
            'description': 'Norman conquest'
        }
        key = compute_event_key_from_dict(event)
        assert isinstance(key, str)
        assert len(key) == 64

    def test_compute_event_key_from_dict_without_description(self):
        """Test event key computation from dict without description field"""
        event = {
            'title': 'Battle of Hastings',
            'start_year': 1066,
            'end_year': 1066
        }
        key = compute_event_key_from_dict(event)
        assert isinstance(key, str)
        assert len(key) == 64

    def test_compute_event_key_from_dict_matches_direct_call(self):
        """Test that dict-based computation matches direct function call"""
        event = {
            'title': 'Moon Landing',
            'start_year': 1969,
            'end_year': 1969,
            'description': 'Apollo 11'
        }
        key1 = compute_event_key_from_dict(event)
        key2 = compute_event_key(
            title='Moon Landing',
            start_year=1969,
            end_year=1969,
            description='Apollo 11'
        )
        assert key1 == key2

    def test_compute_event_key_from_dict_missing_title_raises(self):
        """Test that missing title field raises KeyError"""
        event = {
            'start_year': 1066,
            'end_year': 1066,
            'description': ''
        }
        with pytest.raises(KeyError):
            compute_event_key_from_dict(event)

    def test_compute_event_key_from_dict_missing_start_year_raises(self):
        """Test that missing start_year field raises KeyError"""
        event = {
            'title': 'Battle',
            'end_year': 1066,
            'description': ''
        }
        with pytest.raises(KeyError):
            compute_event_key_from_dict(event)

    def test_compute_event_key_from_dict_missing_end_year_raises(self):
        """Test that missing end_year field raises KeyError"""
        event = {
            'title': 'Battle',
            'start_year': 1066,
            'description': ''
        }
        with pytest.raises(KeyError):
            compute_event_key_from_dict(event)


class TestValidateEventKey:
    """Tests for validate_event_key function"""

    def test_validate_event_key_valid(self):
        """Test validation of valid 64-char hex event key"""
        valid_key = 'a' * 64
        assert validate_event_key(valid_key) is True

    def test_validate_event_key_all_hex_digits(self):
        """Test validation with all valid hex characters"""
        valid_key = '0123456789abcdef' * 4  # 64 chars
        assert validate_event_key(valid_key) is True

    def test_validate_event_key_uppercase_hex(self):
        """Test validation with uppercase hex characters"""
        valid_key = 'ABCDEF0123456789' * 4  # 64 chars
        assert validate_event_key(valid_key) is True

    def test_validate_event_key_mixed_case_hex(self):
        """Test validation with mixed case hex characters"""
        valid_key = 'AaBbCcDd' * 8  # 64 chars
        assert validate_event_key(valid_key) is True

    def test_validate_event_key_too_short(self):
        """Test that keys shorter than 64 chars are invalid"""
        invalid_key = 'a' * 63
        assert validate_event_key(invalid_key) is False

    def test_validate_event_key_too_long(self):
        """Test that keys longer than 64 chars are invalid"""
        invalid_key = 'a' * 65
        assert validate_event_key(invalid_key) is False

    def test_validate_event_key_contains_non_hex(self):
        """Test that keys with non-hex characters are invalid"""
        invalid_key = 'g' + ('a' * 63)  # 'g' is not valid hex
        assert validate_event_key(invalid_key) is False

    def test_validate_event_key_empty_string(self):
        """Test that empty string is invalid"""
        assert validate_event_key('') is False

    def test_validate_event_key_none_raises(self):
        """Test that None returns False (not TypeError)"""
        assert validate_event_key(None) is False

    def test_validate_event_key_non_string_type(self):
        """Test that non-string types return False"""
        assert validate_event_key(12345) is False
        assert validate_event_key(['a']) is False
        assert validate_event_key({'key': 'value'}) is False

    def test_validate_actual_computed_key(self):
        """Test that keys computed by compute_event_key validate correctly"""
        computed_key = compute_event_key("Test", 1000, 2000, "test description")
        assert validate_event_key(computed_key) is True


class TestEventKeyIntegration:
    """Integration tests for event key system"""

    def test_event_key_deterministic_across_multiple_calls(self):
        """Test deterministic behavior across many calls"""
        event_data = {
            'title': 'Battle of Waterloo',
            'start_year': 1815,
            'end_year': 1815,
            'description': 'Defeat of Napoleon'
        }
        keys = [compute_event_key_from_dict(event_data) for _ in range(10)]
        assert all(k == keys[0] for k in keys)

    def test_event_key_format_consistency(self):
        """Test that all computed keys follow valid format"""
        test_cases = [
            ("Rome Founded", -753, -753, "753 BC"),
            ("Julius Caesar Born", -100, -100, "100 BC"),
            ("AD 1", 1, 1, "1 AD"),
            ("Middle Ages", 476, 1453, ""),
            ("Modern Era", 1500, 2026, None),
        ]
        for title, start_year, end_year, description in test_cases:
            key = compute_event_key(title, start_year, end_year, description)
            assert validate_event_key(key), f"Key validation failed for {title}"
