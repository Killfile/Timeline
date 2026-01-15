"""Unit tests for ingestion_list_of_years module.

These tests cover the pure parsing functions without requiring Docker or HTTP.
They validate core business logic independently of IO operations.
"""

import pytest
from strategies.list_of_years.list_of_years_strategy import (
    _parse_scope_from_title,
    _get_tag_and_month_from_h3_context,
    _is_heading_generic,
    _bump_excluded,
    _merge_exclusions,
)


class TestParseScopeFromTitle:
    """Tests for _parse_scope_from_title function."""

    def test_parse_year_bc(self):
        """Should parse BC year titles correctly."""
        result = _parse_scope_from_title("100 BC")
        assert result is not None
        assert result["precision"] == "year"
        assert result["start_year"] == 100
        assert result["end_year"] == 100
        assert result["is_bc"] is True

    def test_parse_year_ad(self):
        """Should parse AD year titles correctly."""
        result = _parse_scope_from_title("100 AD")
        assert result is not None
        assert result["precision"] == "year"
        assert result["start_year"] == 100
        assert result["end_year"] == 100
        assert result["is_bc"] is False

    def test_parse_decade_bc(self):
        """Should parse BC decade titles correctly."""
        result = _parse_scope_from_title("100s BC")
        assert result is not None
        assert result["precision"] == "decade"
        assert result["start_year"] == 100
        assert result["end_year"] == 109
        assert result["is_bc"] is True

    def test_parse_decade_ad(self):
        """Should parse AD decade titles correctly."""
        result = _parse_scope_from_title("100s")
        assert result is not None
        assert result["precision"] == "decade"
        assert result["start_year"] == 100
        assert result["end_year"] == 109
        assert result["is_bc"] is False

    def test_parse_century_bc(self):
        """Should parse BC century titles correctly."""
        result = _parse_scope_from_title("1st century BC")
        assert result is not None
        assert result["precision"] == "century"
        assert result["start_year"] == 100
        assert result["end_year"] == 1
        assert result["is_bc"] is True

    def test_parse_century_ad(self):
        """Should parse AD century titles correctly."""
        result = _parse_scope_from_title("1st century")
        assert result is not None
        assert result["precision"] == "century"
        assert result["start_year"] == 0
        assert result["end_year"] == 99
        assert result["is_bc"] is False

    def test_parse_invalid_title(self):
        """Should return None for invalid titles."""
        assert _parse_scope_from_title("Not a year") is None
        assert _parse_scope_from_title("") is None
        assert _parse_scope_from_title("   ") is None


class TestClassifyEventsH3Context:
    """Tests for _classify_events_h3_context function."""

    def test_classify_by_place(self):
        """Should treat 'By place' as a tag."""
        tag, month_bucket = _get_tag_and_month_from_h3_context("By place")
        assert tag == "By place"
        assert month_bucket is None

    def test_classify_by_topic(self):
        """Should treat 'By topic' as a tag."""
        tag, month_bucket = _get_tag_and_month_from_h3_context("By topic")
        assert tag == "By topic"
        assert month_bucket is None

    def test_classify_month(self):
        """Should identify month headings."""
        tag, month_bucket = _get_tag_and_month_from_h3_context("January")
        assert tag is None
        assert month_bucket == "January"

    def test_classify_month_range(self):
        """Should identify month range headings."""
        tag, month_bucket = _get_tag_and_month_from_h3_context("January–February")
        assert tag is None
        assert month_bucket == "January–February"

    def test_classify_unknown_dates(self):
        """Should handle 'Unknown dates' headings."""
        tag, month_bucket = _get_tag_and_month_from_h3_context("Unknown dates")
        assert tag is None
        assert month_bucket == "Unknown dates"

    def test_classify_none(self):
        """Should handle None input."""
        tag, month_bucket = _get_tag_and_month_from_h3_context(None)
        assert tag is None
        assert month_bucket is None


class TestIsGroupingCategoryHeading:
    """Tests for _is_grouping_category_heading function."""

    def test_by_place_topic_is_grouping(self):
        """Should identify 'By place/topic' as grouping header."""
        assert _is_heading_generic("By place/topic") is True

    def test_by_place_topic_subject_is_grouping(self):
        """Should identify 'By place/topic/subject' as grouping header."""
        assert _is_heading_generic("By place/topic/subject") is True

    def test_by_topic_subject_is_grouping(self):
        """Should identify 'By topic/subject' as grouping header."""
        assert _is_heading_generic("By topic/subject") is True

    def test_by_place_not_grouping(self):
        """Should NOT identify standalone 'By place' as grouping header."""
        assert _is_heading_generic("By place") is False

    def test_none_not_grouping(self):
        """Should handle None input."""
        assert _is_heading_generic(None) is False


class TestBumpExcluded:
    """Tests for _bump_excluded function."""

    def test_increments_count(self):
        """Should increment count for reason."""
        counts = {}
        samples = {}
        _bump_excluded(counts, samples, "test_reason")
        assert counts["test_reason"] == 1
        _bump_excluded(counts, samples, "test_reason")
        assert counts["test_reason"] == 2

    def test_adds_sample_with_text(self):
        """Should add sample when text provided."""
        counts = {}
        samples = {}
        _bump_excluded(counts, samples, "test_reason", text="Sample text", h3="Sample h3")
        assert len(samples["test_reason"]) == 1
        assert samples["test_reason"][0]["text"] == "Sample text"
        assert samples["test_reason"][0]["h3"] == "Sample h3"

    def test_limits_samples_to_eight(self):
        """Should limit samples to 8 per reason."""
        counts = {}
        samples = {}
        for i in range(20):
            _bump_excluded(counts, samples, "test_reason", text=f"Sample {i}")
        assert counts["test_reason"] == 20
        assert len(samples["test_reason"]) == 8

    def test_no_sample_without_text(self):
        """Should not add sample when text not provided."""
        counts = {}
        samples = {}
        _bump_excluded(counts, samples, "test_reason")
        assert counts["test_reason"] == 1
        assert "test_reason" not in samples


class TestMergeExclusions:
    """Tests for _merge_exclusions function."""

    def test_merges_counts(self):
        """Should merge exclusion counts."""
        agg_counts = {"reason1": 5}
        agg_samples = {}
        report = {
            "excluded_counts": {"reason1": 3, "reason2": 2},
            "excluded_samples": {}
        }
        _merge_exclusions(agg_counts, agg_samples, report)
        assert agg_counts["reason1"] == 8
        assert agg_counts["reason2"] == 2

    def test_merges_samples(self):
        """Should merge sample lists."""
        agg_counts = {}
        agg_samples = {"reason1": [{"text": "existing"}]}
        report = {
            "excluded_counts": {},
            "excluded_samples": {
                "reason1": [{"text": "new1"}, {"text": "new2"}]
            }
        }
        _merge_exclusions(agg_counts, agg_samples, report)
        assert len(agg_samples["reason1"]) == 3
        assert agg_samples["reason1"][0]["text"] == "existing"
        assert agg_samples["reason1"][1]["text"] == "new1"

    def test_limits_aggregate_samples_to_25(self):
        """Should limit aggregate samples to 25 per reason."""
        agg_counts = {}
        agg_samples = {"reason1": [{"text": f"existing{i}"} for i in range(20)]}
        report = {
            "excluded_counts": {},
            "excluded_samples": {
                "reason1": [{"text": f"new{i}"} for i in range(10)]
            }
        }
        _merge_exclusions(agg_counts, agg_samples, report)
        assert len(agg_samples["reason1"]) == 25

    def test_handles_none_report(self):
        """Should handle None report gracefully."""
        agg_counts = {}
        agg_samples = {}
        _merge_exclusions(agg_counts, agg_samples, None)
        assert agg_counts == {}
        assert agg_samples == {}

    def test_handles_empty_report(self):
        """Should handle empty report gracefully."""
        agg_counts = {}
        agg_samples = {}
        _merge_exclusions(agg_counts, agg_samples, {})
        assert agg_counts == {}
        assert agg_samples == {}
