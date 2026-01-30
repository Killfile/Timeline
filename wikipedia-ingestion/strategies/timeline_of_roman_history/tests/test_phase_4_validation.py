"""Phase 4: Schema Validation and Integration Tests for Timeline of Roman History Strategy."""

import json
import pytest
from pathlib import Path
from datetime import datetime
import jsonschema

from strategies.timeline_of_roman_history.timeline_of_roman_history_strategy import (
    TimelineOfRomanHistoryStrategy
)
from strategies.strategy_base import FetchResult


def _load_fixture(filename: str) -> str:
    """Load HTML fixture content from the fixtures directory."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    return (fixtures_dir / filename).read_text(encoding="utf-8")


def _load_expected_events(filename: str) -> list:
    """Load expected events fixture from JSON."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    with open(fixtures_dir / filename, 'r') as f:
        return json.load(f)


def _load_schema() -> dict:
    """Load the import schema."""
    schema_path = Path(__file__).parent.parent.parent.parent / "import_schema.json"
    with open(schema_path, 'r') as f:
        return json.load(f)


class TestArtifactSchemaValidation:
    """Test that generated artifacts match the import_schema.json schema."""
    
    def test_schema_file_exists(self):
        """Verify import_schema.json exists."""
        schema_path = Path(__file__).parent.parent.parent.parent / "import_schema.json"
        assert schema_path.exists(), f"Schema file not found at {schema_path}"
    
    def test_6th_century_bc_fixture_matches_schema(self):
        """T095: Parse 6th century BC fixture and validate events against schema."""
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        
        # Load fixture
        html_content = _load_fixture('sample_html_6th_century_bc.html')
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        # Parse
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        # Validate event structure against schema
        schema = _load_schema()
        event_schema = schema["properties"]["events"]["items"]
        
        artifact_dict = artifact_data.to_dict()
        
        # Verify artifact structure
        assert artifact_dict["strategy"] == "TimelineOfRomanHistory"  # STRATEGY_NAME constant
        assert "run_id" in artifact_dict
        assert "generated_at_utc" in artifact_dict
        assert artifact_dict["event_count"] == len(artifact_dict["events"])
        
        # Validate each event against the event schema
        for event_dict in artifact_dict["events"]:
            try:
                jsonschema.validate(instance=event_dict, schema=event_schema)
            except jsonschema.ValidationError as e:
                pytest.fail(f"Event validation failed: {e.message}")

    
    def test_1st_century_ad_fixture_matches_schema(self):
        """Parse 1st century AD fixture and validate events against schema."""
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        
        # Load fixture
        html_content = _load_fixture('sample_html_1st_century_ad.html')
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        # Parse
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        # Validate event structure against schema
        schema = _load_schema()
        event_schema = schema["properties"]["events"]["items"]
        
        artifact_dict = artifact_data.to_dict()
        
        assert artifact_dict["event_count"] == len(artifact_dict["events"])
        
        # Validate each event against the event schema
        for event_dict in artifact_dict["events"]:
            try:
                jsonschema.validate(instance=event_dict, schema=event_schema)
            except jsonschema.ValidationError as e:
                pytest.fail(f"Event validation failed: {e.message}")

    
    def test_artifact_event_count_matches_expected(self):
        """T096: Verify artifact event_count matches expected event count."""
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        
        html_content = _load_fixture('sample_html_6th_century_bc.html')
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        # Check event count
        assert artifact_data.event_count == 8
        assert len(artifact_data.events) == 8
        assert artifact_data.to_dict()["event_count"] == 8
    
    def test_all_events_have_valid_event_keys(self):
        """T097: Verify all events have valid event_key values."""
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        
        html_content = _load_fixture('sample_html_1st_century_ad.html')
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        # All events should have proper keys
        for event in artifact_data.events:
            # Basic validation: event_key should be computable from event data
            assert event.start_year > 0
            assert isinstance(event.is_bc_start, bool)
            assert event.title is not None and len(event.title) > 0
            assert event.url is not None and event.url.startswith("http")
    
    def test_bc_dates_have_correct_flags(self):
        """T098: Verify BC dates have is_bc_start=True, AD dates have is_bc_start=False."""
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        
        html_content = _load_fixture('sample_html_1st_century_ad.html')
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        # Check specific known events:
        # BC events (should have is_bc_start=True): Caesar (100), Social War (100), Augustus (63), Augustus era (27)
        # AD events (should have is_bc_start=False): Augustus dies (14 AD), Crucifixion (33 AD), Vesuvius (79 AD)
        for event in artifact_data.events:
            if "Caesar" in event.title:
                # Gaius Julius Caesar born 100 BC
                assert event.is_bc_start == True, f"Caesar should be BC"
            if "Augustus" in event.title:
                # Various Augustus events, mostly BC or transition
                # "granted the title" is 27 BC, "celebrates his birthday" is 27 BC, "Death of Augustus" is 14 AD
                if "Death" in event.title:
                    assert event.is_bc_start == False, f"Augustus death should be AD 14"
                else:
                    assert event.is_bc_start == True, f"Augustus era events should be BC"
            if "Jesus" in event.title or "Crucifixion" in event.title:
                # 33 AD
                assert event.is_bc_start == False, f"Crucifixion should be AD"
            if "Vesuvius" in event.title:
                # 79 AD
                assert event.is_bc_start == False, f"Vesuvius should be AD"


    
    def test_all_events_have_required_fields(self):
        """T099: Verify all events have required fields per schema."""
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        
        html_content = _load_fixture('sample_html_6th_century_bc.html')
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        required_fields = [
            "title", "start_year", "end_year", "is_bc_start", "is_bc_end",
            "precision", "weight", "url", "span_match_notes", "description", "category"
        ]
        
        for event in artifact_data.events:
            event_dict = event.to_dict()
            for field in required_fields:
                assert field in event_dict, f"Event missing required field: {field}"
                # Field should not be None for required fields
                if field not in ["start_month", "start_day", "end_month", "end_day", "_debug_extraction"]:
                    assert event_dict[field] is not None, f"Event required field {field} is None"
    
    def test_schema_validation_with_jsonschema(self):
        """T099b: Validate event documents match import_schema.json using jsonschema."""
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        
        html_content = _load_fixture('sample_html_6th_century_bc.html')
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        schema = _load_schema()
        event_schema = schema["properties"]["events"]["items"]
        artifact_dict = artifact_data.to_dict()
        
        # Validate each event against the event schema
        for event_dict in artifact_dict["events"]:
            try:
                jsonschema.validate(instance=event_dict, schema=event_schema)
            except jsonschema.ValidationError as e:
                pytest.fail(f"Event schema validation failed: {e.message}\nEvent: {event_dict}")

    
    def test_metadata_structure_complete(self):
        """Verify metadata has all accessible fields."""
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        
        html_content = _load_fixture('sample_html_6th_century_bc.html')
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        artifact_dict = artifact_data.to_dict()
        metadata = artifact_dict["metadata"]
        
        # Check metadata has parsing information
        assert isinstance(metadata, dict)
        assert "parse_duration_seconds" in metadata
        assert "total_tables" in metadata
        assert "total_rows_processed" in metadata
        assert "events_extracted" in metadata
        assert "skipped_rows" in metadata
        assert "confidence_distribution" in metadata
        
        # Confidence distribution should have counts
        confidence = metadata["confidence_distribution"]
        assert isinstance(confidence, dict)
        assert len(confidence) > 0  # Should have at least one confidence level



class TestExpectedEventFixtures:
    """Tests comparing parsed output against expected fixtures."""
    
    def test_6th_century_bc_matches_expected_events(self):
        """T093: Compare parsed 6th century BC against expected_events_6th_century_bc.json."""
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        
        html_content = _load_fixture('sample_html_6th_century_bc.html')
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        expected_events = _load_expected_events('expected_events_6th_century_bc.json')
        actual_events = [e.to_dict() for e in artifact_data.events]
        
        # Event count should match
        assert len(actual_events) == len(expected_events), \
            f"Event count mismatch: expected {len(expected_events)}, got {len(actual_events)}"
        
        # Check key properties of each event
        for actual, expected in zip(actual_events, expected_events):
            assert actual["title"] == expected["title"]
            assert actual["start_year"] == expected["start_year"]
            assert actual["end_year"] == expected["end_year"]
            assert actual["is_bc_start"] == expected["is_bc_start"]
            assert actual["is_bc_end"] == expected["is_bc_end"]
            assert actual["description"] == expected["description"]
    
    def test_1st_century_ad_matches_expected_events(self):
        """T094: Compare parsed 1st century AD against expected_events_1st_century_ad.json."""
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        
        html_content = _load_fixture('sample_html_1st_century_ad.html')
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        expected_events = _load_expected_events('expected_events_1st_century_ad.json')
        actual_events = [e.to_dict() for e in artifact_data.events]
        
        # Event count should match
        assert len(actual_events) == len(expected_events), \
            f"Event count mismatch: expected {len(expected_events)}, got {len(actual_events)}"
        
        # Check key properties
        for actual, expected in zip(actual_events, expected_events):
            assert actual["title"] == expected["title"]
            assert actual["start_year"] == expected["start_year"]
            assert actual["end_year"] == expected["end_year"]
            assert actual["is_bc_start"] == expected["is_bc_start"]
            assert actual["is_bc_end"] == expected["is_bc_end"]
