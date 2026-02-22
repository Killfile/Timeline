"""Tests for HistoricalEvent JSON serialization safety."""

import pytest

from historical_event import HistoricalEvent


def test_to_dict_sets_empty_description_when_none() -> None:
    """Description should serialize as empty string when None."""
    event = HistoricalEvent(
        title="Stonewall uprising",
        description=None,
        url="https://example.com/stonewall",
        start_year=1969,
        end_year=1969,
        is_bc_start=False,
        is_bc_end=False,
        weight=1,
        precision=1.0,
        span_match_notes="exact_year",
    )

    payload = event.to_dict()

    assert payload["description"] == ""


def test_to_dict_truncates_title_to_500_chars() -> None:
    """Serialized title must fit database VARCHAR(500)."""
    long_title = "A" * 700

    event = HistoricalEvent(
        title=long_title,
        description="Some description",
        url="https://example.com/long-title",
        start_year=2000,
        end_year=2000,
        is_bc_start=False,
        is_bc_end=False,
        weight=1,
        precision=1.0,
        span_match_notes="exact_year",
    )

    payload = event.to_dict()

    assert len(payload["title"]) == 500
    assert payload["title"] == long_title[:500]


def test_empty_title_raises_value_error() -> None:
    """Invalid empty title should fail validation."""
    with pytest.raises(ValueError, match="title"):
        HistoricalEvent(
            title="   ",
            description="desc",
            url="https://example.com/invalid",
            start_year=2000,
            end_year=2000,
            is_bc_start=False,
            is_bc_end=False,
            weight=1,
            precision=1.0,
            span_match_notes="exact_year",
        )
