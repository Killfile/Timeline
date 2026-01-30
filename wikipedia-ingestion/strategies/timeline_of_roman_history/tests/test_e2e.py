"""End-to-End Tests for Timeline of Roman History Strategy."""

import json
import time
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from strategies.timeline_of_roman_history.timeline_of_roman_history_strategy import (
    TimelineOfRomanHistoryStrategy
)
from strategies.strategy_base import FetchResult, ParseResult


def _load_fixture(filename: str) -> str:
    """Load HTML fixture content from the fixtures directory."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    return (fixtures_dir / filename).read_text(encoding="utf-8")


class TestIdempotency:
    """Test that running strategy twice produces identical results."""
    
    def test_run_strategy_twice_produces_identical_event_keys(self):
        """T100: Run strategy twice with same data, verify identical event_keys."""
        html_content = _load_fixture('sample_html_6th_century_bc.html')
        
        # First run
        strategy1 = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts_1')
        )
        strategy1.html_content = html_content
        strategy1.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        fetch_result1 = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy1.canonical_url}
        )
        parse_result1 = strategy1.parse(fetch_result1)
        artifact_data1 = strategy1.generate_artifacts(parse_result1)
        events1 = [e.to_dict() for e in artifact_data1.events]
        
        # Second run with different timestamp but same content
        strategy2 = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts_2')
        )
        strategy2.html_content = html_content
        strategy2.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        fetch_result2 = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy2.canonical_url}
        )
        parse_result2 = strategy2.parse(fetch_result2)
        artifact_data2 = strategy2.generate_artifacts(parse_result2)
        events2 = [e.to_dict() for e in artifact_data2.events]
        
        # Verify identical event count
        assert len(events1) == len(events2), "Event counts should be identical"
        
        # Verify identical events (ignoring timestamp-based fields)
        for e1, e2 in zip(events1, events2):
            # These should be identical
            assert e1["title"] == e2["title"]
            assert e1["start_year"] == e2["start_year"]
            assert e1["end_year"] == e2["end_year"]
            assert e1["is_bc_start"] == e2["is_bc_start"]
            assert e1["is_bc_end"] == e2["is_bc_end"]
            assert e1["description"] == e2["description"]
            assert e1["precision"] == e2["precision"]
            assert e1["weight"] == e2["weight"]
    
    def test_idempotent_parsing_same_dates(self):
        """Verify parsing the same HTML multiple times produces same date extractions."""
        html_content = _load_fixture('sample_html_1st_century_ad.html')
        
        extracted_years = []
        for _ in range(2):
            strategy = TimelineOfRomanHistoryStrategy(
                run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
                output_dir=Path('/tmp/test_artifacts')
            )
            strategy.html_content = html_content
            strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
            
            fetch_result = FetchResult(
                strategy_name="timeline_of_roman_history",
                fetch_count=1,
                fetch_metadata={"url": strategy.canonical_url}
            )
            parse_result = strategy.parse(fetch_result)
            artifact_data = strategy.generate_artifacts(parse_result)
            
            years = [(e.start_year, e.is_bc_start) for e in artifact_data.events]
            extracted_years.append(years)
        
        # Both runs should extract identical year/BC flag pairs
        assert extracted_years[0] == extracted_years[1], \
            "Date extraction should be deterministic"


class TestFullStrategyExecution:
    """Test full end-to-end strategy execution."""
    
    def test_full_strategy_with_6th_century_fixture(self):
        """T101: Run full strategy on 6th century BC fixture with mocked network."""
        html_content = _load_fixture('sample_html_6th_century_bc.html')
        
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        
        # Mock the network fetch to use our fixture
        with patch('strategies.timeline_of_roman_history.timeline_of_roman_history_strategy.get_html') as mock_get_html:
            mock_get_html.return_value = ((html_content, "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"), None)
            
            # Run full ingest cycle
            artifact_data = strategy.ingest()
            
            # Verify successful execution
            assert artifact_data is not None
            assert len(artifact_data.events) > 0
            assert artifact_data.event_count == len(artifact_data.events)
            assert artifact_data.strategy_name == "TimelineOfRomanHistory"
            
            # Verify get_html was called
            mock_get_html.assert_called_once()
    
    def test_full_strategy_with_1st_century_fixture(self):
        """Run full strategy on 1st century AD fixture."""
        html_content = _load_fixture('sample_html_1st_century_ad.html')
        
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        
        with patch('strategies.timeline_of_roman_history.timeline_of_roman_history_strategy.get_html') as mock_get_html:
            mock_get_html.return_value = ((html_content, "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"), None)
            
            artifact_data = strategy.ingest()
            
            # Should extract 10 events from 1st century fixture
            assert len(artifact_data.events) == 10
            assert artifact_data.event_count == 10
    
    def test_strategy_handles_network_error_gracefully(self):
        """Test strategy handles network errors without crashing."""
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        
        # Mock network error
        with patch('strategies.timeline_of_roman_history.timeline_of_roman_history_strategy.get_html') as mock_get_html:
            mock_get_html.return_value = (("", ""), "Network timeout")
            
            # Should raise with meaningful error
            with pytest.raises(RuntimeError) as exc_info:
                strategy.ingest()
            
            assert "Failed to fetch" in str(exc_info.value)


class TestPerformance:
    """Test strategy performance requirements."""
    
    def test_strategy_completes_in_under_30_seconds(self):
        """T102: Verify strategy completes in <30 seconds."""
        html_content = _load_fixture('sample_html_1st_century_ad.html')
        
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        start_time = time.time()
        
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        elapsed = time.time() - start_time
        
        assert elapsed < 30.0, f"Strategy took {elapsed:.2f}s, should be < 30s"
        assert len(artifact_data.events) > 0
    
    def test_parsing_throughput_reasonable(self):
        """Verify parsing throughput is reasonable (>10 events/second)."""
        html_content = _load_fixture('sample_html_1st_century_ad.html')
        
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        start_time = time.time()
        
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        
        elapsed = time.time() - start_time
        event_count = len(parse_result.events)
        throughput = event_count / elapsed if elapsed > 0 else float('inf')
        
        # Should parse at least 10 events per second
        assert throughput >= 10.0, f"Throughput {throughput:.1f} events/sec should be >= 10"


class TestErrorHandling:
    """Test error handling and robustness."""
    
    def test_no_events_dropped_due_to_parse_errors(self):
        """T103: Verify no events are dropped due to parse errors."""
        html_content = _load_fixture('sample_html_6th_century_bc.html')
        
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        # Check that we have events and skipped_rows is acceptable
        assert len(artifact_data.events) > 0, "Should have parsed events"
        
        # Verify metadata has error info
        metadata = artifact_data.to_dict()["metadata"]
        assert "skipped_rows" in metadata
        
        # Should have skipped minimal rows (ideally 0)
        assert metadata["skipped_rows"] == 0, "Should not skip rows in clean fixture"
    
    def test_malformed_date_handling(self):
        """Verify strategy handles malformed dates gracefully."""
        # Create HTML with intentionally malformed dates
        malformed_html = """
        <html>
        <table class="wikitable">
        <tr><th>Year</th><th>Date</th><th>Event</th></tr>
        <tr><td>753 BC</td><td>April 21</td><td>Rome founded</td></tr>
        <tr><td>INVALID_YEAR</td><td>?</td><td>Unknown event</td></tr>
        <tr><td>509 BC</td><td></td><td>Republic established</td></tr>
        </table>
        </html>
        """
        
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        strategy.html_content = malformed_html
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        # Should skip the malformed row but continue parsing
        assert len(artifact_data.events) >= 2, "Should have parsed valid rows despite error"


class TestSummaryReport:
    """Test summary report generation."""
    
    def test_artifact_contains_summary_metadata(self):
        """T104: Verify artifact contains summary report with counts."""
        html_content = _load_fixture('sample_html_1st_century_ad.html')
        
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
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
        
        # Verify artifact has required summary fields
        assert "event_count" in artifact_dict
        assert "strategy" in artifact_dict
        assert "run_id" in artifact_dict
        assert "generated_at_utc" in artifact_dict
        assert "metadata" in artifact_dict
        
        # Verify metadata has summary counts
        metadata = artifact_dict["metadata"]
        assert "total_tables" in metadata
        assert "total_rows_processed" in metadata
        assert "events_extracted" in metadata
        assert "skipped_rows" in metadata
        assert "confidence_distribution" in metadata
        
        # Verify counts are sensible
        assert metadata["events_extracted"] == len(artifact_dict["events"])
        assert metadata["total_rows_processed"] >= metadata["events_extracted"]
    
    def test_confidence_distribution_in_summary(self):
        """Verify summary includes confidence distribution breakdown."""
        html_content = _load_fixture('sample_html_6th_century_bc.html')
        
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        metadata = artifact_data.to_dict()["metadata"]
        confidence_dist = metadata["confidence_distribution"]
        
        # Should have confidence counts
        assert isinstance(confidence_dist, dict)
        assert len(confidence_dist) > 0
        
        # Sum of confidences should equal event count
        total_confidence_events = sum(confidence_dist.values())
        assert total_confidence_events == len(artifact_data.events)
    
    def test_parse_timing_in_metadata(self):
        """Verify parse timing is recorded in summary."""
        html_content = _load_fixture('sample_html_1st_century_ad.html')
        
        strategy = TimelineOfRomanHistoryStrategy(
            run_id=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
            output_dir=Path('/tmp/test_artifacts')
        )
        strategy.html_content = html_content
        strategy.canonical_url = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
        
        fetch_result = FetchResult(
            strategy_name="timeline_of_roman_history",
            fetch_count=1,
            fetch_metadata={"url": strategy.canonical_url}
        )
        parse_result = strategy.parse(fetch_result)
        artifact_data = strategy.generate_artifacts(parse_result)
        
        metadata = artifact_data.to_dict()["metadata"]
        
        # Should have parse duration
        assert "parse_duration_seconds" in metadata
        assert metadata["parse_duration_seconds"] > 0
        assert metadata["parse_duration_seconds"] < 30  # Should be fast
