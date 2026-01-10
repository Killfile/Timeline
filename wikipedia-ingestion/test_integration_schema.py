"""Integration tests for canonical event schema across ingestion strategies.

Verifies that all ingestion strategies produce events conforming to the
canonical schema defined in event_schema.py.
"""

import json
from pathlib import Path

import pytest

from event_schema import validate_canonical_event


def test_list_of_years_artifact_format():
    """Verify list_of_years artifacts use canonical schema."""
    # Find the most recent list_of_years artifact
    artifacts = sorted(Path("logs").glob("events_list_of_years_*.json"))
    
    if not artifacts:
        pytest.skip("No list_of_years artifacts found in logs/")
    
    artifact_path = artifacts[-1]
    
    with open(artifact_path) as f:
        data = json.load(f)
    
    events = data.get("events", [])
    assert len(events) > 0, f"No events found in {artifact_path}"
    
    # Check first 10 events for canonical schema compliance
    for i, event in enumerate(events[:10]):
        is_valid, error = validate_canonical_event(event)
        assert is_valid, f"Event {i} in {artifact_path.name} failed validation: {error}"
        
        # Verify no nested span object
        assert "span" not in event, f"Event {i} has nested 'span' object (non-canonical)"
        
        # Verify correct field names
        assert "is_bc_start" in event, f"Event {i} uses wrong field name (should be 'is_bc_start')"
        assert "is_bc_end" in event, f"Event {i} uses wrong field name (should be 'is_bc_end')"
        assert "start_year_is_bc" not in event, "Event uses old field name 'start_year_is_bc'"


def test_list_of_time_periods_artifact_format():
    """Verify list_of_time_periods artifacts use canonical schema."""
    # Find the most recent list_of_time_periods artifact
    artifacts = sorted(Path("logs").glob("*list_of_time_periods*.json"))
    
    if not artifacts:
        pytest.skip("No list_of_time_periods artifacts found in logs/")
    
    artifact_path = artifacts[-1]
    
    with open(artifact_path) as f:
        data = json.load(f)
    
    events = data.get("events", [])
    if len(events) == 0:
        pytest.skip(f"No events found in {artifact_path}")
    
    # Check all events for canonical schema compliance
    for i, event in enumerate(events):
        is_valid, error = validate_canonical_event(event)
        assert is_valid, f"Event {i} in {artifact_path.name} failed validation: {error}"
        
        # Verify no nested span object
        assert "span" not in event, f"Event {i} has nested 'span' object (non-canonical)"
        
        # Verify correct field names
        assert "is_bc_start" in event, f"Event {i} uses wrong field name"
        assert "is_bc_end" in event, f"Event {i} uses wrong field name"


def test_artifact_schema_consistency():
    """Verify all artifacts from both strategies have same schema structure."""
    # Collect all recent artifacts
    list_of_years_artifacts = sorted(Path("logs").glob("events_list_of_years_*.json"))
    time_periods_artifacts = sorted(Path("logs").glob("*list_of_time_periods*.json"))
    
    if not list_of_years_artifacts or not time_periods_artifacts:
        pytest.skip("Need artifacts from both strategies")
    
    # Get most recent from each
    loy_path = list_of_years_artifacts[-1]
    ltp_path = time_periods_artifacts[-1]
    
    with open(loy_path) as f:
        loy_data = json.load(f)
    
    with open(ltp_path) as f:
        ltp_data = json.load(f)
    
    loy_events = loy_data.get("events", [])
    ltp_events = ltp_data.get("events", [])
    
    if not loy_events or not ltp_events:
        pytest.skip("No events in one or both artifacts")
    
    # Compare schema structure (field names) of first event from each
    loy_fields = set(loy_events[0].keys())
    ltp_fields = set(ltp_events[0].keys())
    
    # Required fields must be present in both
    required = {
        "title", "description", "url",
        "start_year", "end_year",
        "is_bc_start", "is_bc_end",
        "weight", "precision"
    }
    
    assert required.issubset(loy_fields), f"list_of_years missing required fields: {required - loy_fields}"
    assert required.issubset(ltp_fields), f"list_of_time_periods missing required fields: {required - ltp_fields}"
    
    # Neither should have nested span
    assert "span" not in loy_fields, "list_of_years has nested span"
    assert "span" not in ltp_fields, "list_of_time_periods has nested span"


def test_weight_and_precision_validity():
    """Verify all events have valid weight and precision values."""
    artifacts = list(Path("logs").glob("events_list_of_years_*.json")) + \
                list(Path("logs").glob("*list_of_time_periods*.json"))
    
    if not artifacts:
        pytest.skip("No artifacts found")
    
    for artifact_path in artifacts:
        with open(artifact_path) as f:
            data = json.load(f)
        
        events = data.get("events", [])
        
        for i, event in enumerate(events):
            # Check weight
            weight = event.get("weight")
            assert weight is not None, f"Event {i} in {artifact_path.name} has None weight"
            assert isinstance(weight, int), f"Event {i} weight is not int: {type(weight)}"
            assert weight > 0, f"Event {i} weight is not positive: {weight}"
            
            # Check precision
            precision = event.get("precision")
            assert precision is not None, f"Event {i} in {artifact_path.name} has None precision"
            assert isinstance(precision, (int, float)), f"Event {i} precision is not numeric: {type(precision)}"
            assert precision > 0, f"Event {i} precision is not positive: {precision}"
