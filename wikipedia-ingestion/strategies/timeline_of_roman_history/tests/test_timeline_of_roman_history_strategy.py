"""Tests for Timeline of Roman History ingestion strategy."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from strategies.timeline_of_roman_history.timeline_of_roman_history_strategy import (
    TimelineOfRomanHistoryStrategy
)
from strategies.strategy_base import FetchResult, ParseResult


def _load_fixture(filename: str) -> str:
    """Load HTML fixture content from the fixtures directory."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    return (fixtures_dir / filename).read_text(encoding="utf-8")


# Sample HTML fragments for testing
SAMPLE_TABLE_HTML = """
<html>
<body>
<table class="wikitable">
<tr>
<th>Year</th>
<th>Date</th>
<th>Event</th>
</tr>
<tr>
<td>753 BC</td>
<td>21 April</td>
<td>Traditional founding of Rome by Romulus</td>
</tr>
<tr>
<td>509 BC</td>
<td></td>
<td>Overthrow of the Roman monarchy; establishment of the Roman Republic</td>
</tr>
<tr>
<td>264 BC</td>
<td></td>
<td>First Punic War begins</td>
</tr>
</table>
</body>
</html>
"""

SAMPLE_TABLE_WITH_ROWSPAN = """
<html>
<body>
<table class="wikitable">
<tr>
<th>Year</th>
<th>Date</th>
<th>Event</th>
</tr>
<tr>
<td rowspan="3">44 BC</td>
<td>15 March</td>
<td>Assassination of Julius Caesar</td>
</tr>
<tr>
<td>20 March</td>
<td>Funeral of Caesar</td>
</tr>
<tr>
<td></td>
<td>Octavian arrives in Rome</td>
</tr>
<tr>
<td>27 BC</td>
<td>16 January</td>
<td>Octavian receives the title Augustus</td>
</tr>
</table>
</body>
</html>
"""

SAMPLE_TABLE_BC_TO_AD = """
<html>
<body>
<table class="wikitable">
<tr>
<th>Year</th>
<th>Date</th>
<th>Event</th>
</tr>
<tr>
<td>1 BC</td>
<td></td>
<td>Last year of the BC era</td>
</tr>
<tr>
<td>AD 1</td>
<td></td>
<td>First year of the AD era</td>
</tr>
<tr>
<td>AD 14</td>
<td>19 August</td>
<td>Death of Augustus</td>
</tr>
</table>
</body>
</html>
"""

SAMPLE_TABLE_BYZANTINE = """
<html>
<body>
<table class="wikitable">
<tr>
<th>Year</th>
<th>Date</th>
<th>Event</th>
</tr>
<tr>
<td>AD 476</td>
<td>4 September</td>
<td>Fall of Western Roman Empire</td>
</tr>
<tr>
<td>AD 527</td>
<td></td>
<td>Justinian I becomes Byzantine Emperor</td>
</tr>
</table>
</body>
</html>
"""

SAMPLE_MALFORMED_TABLE = """
<html>
<body>
<table class="wikitable">
<tr>
<th>Year</th>
<th>Date</th>
<th>Event</th>
</tr>
<tr>
<td>Invalid Year</td>
<td>Invalid Date</td>
<td>This should be skipped</td>
</tr>
<tr>
<td>509 BC</td>
</tr>
<tr>
<td>264 BC</td>
<td>January</td>
<td>Valid event after malformed row</td>
</tr>
</table>
</body>
</html>
"""


@pytest.fixture
def strategy():
    """Create a strategy instance for testing."""
    run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path("/tmp/test_roman_history")
    output_dir.mkdir(parents=True, exist_ok=True)
    return TimelineOfRomanHistoryStrategy(run_id, output_dir)


class TestStrategyBasics:
    """Test basic strategy properties."""
    
    def test_strategy_name(self, strategy):
        """Test strategy returns correct name."""
        assert strategy.name() == "timeline_of_roman_history"
    
    def test_strategy_initialization(self, strategy):
        """Test strategy initializes with correct properties."""
        assert strategy.run_id is not None
        assert strategy.output_dir.exists()
        assert strategy.html_content is None
        assert strategy.canonical_url is None
        assert len(strategy.roman_events) == 0


class TestFetchPhase:
    """Test the fetch phase."""
    
    @patch('strategies.timeline_of_roman_history.timeline_of_roman_history_strategy.get_html')
    def test_fetch_success(self, mock_get_html, strategy):
        """Test successful fetch returns FetchResult."""
        mock_get_html.return_value = (
            ("<html><body>Test content</body></html>", "https://final.url"),
            None
        )
        
        result = strategy.fetch()
        
        assert isinstance(result, FetchResult)
        assert result.strategy_name == "TimelineOfRomanHistory"
        assert result.fetch_count == 1
        assert strategy.html_content == "<html><body>Test content</body></html>"
        assert strategy.canonical_url == "https://final.url"
        assert "url" in result.fetch_metadata
        assert "final_url" in result.fetch_metadata
    
    @patch('strategies.timeline_of_roman_history.timeline_of_roman_history_strategy.get_html')
    def test_fetch_failure(self, mock_get_html, strategy):
        """Test fetch failure raises RuntimeError."""
        mock_get_html.return_value = (
            ("", "https://url"),
            "Connection timeout"
        )
        
        with pytest.raises(RuntimeError, match="Failed to fetch article"):
            strategy.fetch()
    
    @patch('strategies.timeline_of_roman_history.timeline_of_roman_history_strategy.get_html')
    def test_fetch_empty_content(self, mock_get_html, strategy):
        """Test fetch with empty content raises RuntimeError."""
        mock_get_html.return_value = (
            ("   ", "https://url"),
            None
        )
        
        with pytest.raises(RuntimeError, match="Failed to fetch article"):
            strategy.fetch()


class TestParsePhase:
    """Test the parse phase."""
    
    def test_parse_without_fetch_raises_error(self, strategy):
        """Test parsing without fetch raises RuntimeError."""
        fetch_result = FetchResult(
            strategy_name="TimelineOfRomanHistory",
            fetch_count=1
        )
        
        with pytest.raises(RuntimeError, match="No HTML content available"):
            strategy.parse(fetch_result)
    
    def test_parse_simple_table(self, strategy):
        """Test parsing a simple table with BC dates."""
        strategy.html_content = SAMPLE_TABLE_HTML
        strategy.canonical_url = "https://test.url"
        
        fetch_result = FetchResult(
            strategy_name="TimelineOfRomanHistory",
            fetch_count=1
        )
        
        result = strategy.parse(fetch_result)
        
        assert isinstance(result, ParseResult)
        assert result.strategy_name == "TimelineOfRomanHistory"
        assert len(result.events) == 3
        
        # Check first event (753 BC with exact date)
        event1 = result.events[0]
        assert event1.start_year == 753
        assert event1.is_bc_start is True
        assert event1.start_month == 4
        assert event1.start_day == 21
        assert "Romulus" in event1.title or "Romulus" in event1.description
        
        # Check second event (509 BC, year only)
        event2 = result.events[1]
        assert event2.start_year == 509
        assert event2.is_bc_start is True
        assert "Republic" in event2.title or "Republic" in event2.description
    
    def test_parse_table_with_rowspan(self, strategy):
        """Test parsing table with rowspan inheritance."""
        strategy.html_content = SAMPLE_TABLE_WITH_ROWSPAN
        strategy.canonical_url = "https://test.url"
        
        fetch_result = FetchResult(
            strategy_name="TimelineOfRomanHistory",
            fetch_count=1
        )
        
        result = strategy.parse(fetch_result)
        
        assert len(result.events) == 4
        
        # All first three events should be from 44 BC
        assert result.events[0].start_year == 44
        assert result.events[0].is_bc_start is True
        assert result.events[1].start_year == 44
        assert result.events[1].is_bc_start is True
        assert result.events[2].start_year == 44
        assert result.events[2].is_bc_start is True
        
        # Check Caesar assassination has exact date
        assert result.events[0].start_month == 3
        assert result.events[0].start_day == 15
        
        # Fourth event should be 27 BC
        assert result.events[3].start_year == 27
        assert result.events[3].is_bc_start is True
    
    def test_parse_bc_to_ad_transition(self, strategy):
        """Test parsing BC to AD transition."""
        strategy.html_content = SAMPLE_TABLE_BC_TO_AD
        strategy.canonical_url = "https://test.url"
        
        fetch_result = FetchResult(
            strategy_name="TimelineOfRomanHistory",
            fetch_count=1
        )
        
        result = strategy.parse(fetch_result)
        
        assert len(result.events) == 3
        
        # Check 1 BC
        assert result.events[0].start_year == 1
        assert result.events[0].is_bc_start is True
        
        # Check AD 1
        assert result.events[1].start_year == 1
        assert result.events[1].is_bc_start is False
        
        # Check AD 14
        assert result.events[2].start_year == 14
        assert result.events[2].is_bc_start is False
        assert result.events[2].start_month == 8
        assert result.events[2].start_day == 19
    
    def test_parse_byzantine_period(self, strategy):
        """Test parsing Byzantine period events."""
        strategy.html_content = _load_fixture("sample_html_byzantine.html")
        strategy.canonical_url = "https://test.url"
        
        fetch_result = FetchResult(
            strategy_name="TimelineOfRomanHistory",
            fetch_count=1
        )
        
        result = strategy.parse(fetch_result)
        
        assert len(result.events) == 8
        
        years = {event.start_year for event in result.events}
        assert {330, 395, 527, 532, 1204, 1453}.issubset(years)
        assert all(event.category == "roman_history" for event in result.events)

    def test_parse_fixture_6th_century_bc(self, strategy):
        """Parse fixture with legendary period and rowspan inheritance."""
        strategy.html_content = _load_fixture("sample_html_6th_century_bc.html")
        strategy.canonical_url = "https://test.url"

        fetch_result = FetchResult(
            strategy_name="TimelineOfRomanHistory",
            fetch_count=1
        )

        result = strategy.parse(fetch_result)

        assert len(result.events) == 8
        assert result.parse_metadata["confidence_distribution"].get("legendary", 0) > 0

    def test_parse_fixture_1st_century_ad(self, strategy):
        """Parse fixture with BC→AD transition and rowspans."""
        strategy.html_content = _load_fixture("sample_html_1st_century_ad.html")
        strategy.canonical_url = "https://test.url"

        fetch_result = FetchResult(
            strategy_name="TimelineOfRomanHistory",
            fetch_count=1
        )

        result = strategy.parse(fetch_result)

        assert len(result.events) == 10
        assert any(event.is_bc_start for event in result.events)
        assert any(not event.is_bc_start for event in result.events)

    @patch("strategies.timeline_of_roman_history.timeline_of_roman_history_strategy.log_info")
    def test_parse_logs_inherited_rows(self, mock_log_info, strategy):
        """Rows inheriting from rowspan should log a message."""
        strategy.html_content = _load_fixture("sample_html_6th_century_bc.html")
        strategy.canonical_url = "https://test.url"

        fetch_result = FetchResult(
            strategy_name="TimelineOfRomanHistory",
            fetch_count=1
        )

        strategy.parse(fetch_result)

        assert any("Inherited year" in call.args[0] for call in mock_log_info.call_args_list)
    
    def test_parse_malformed_table(self, strategy):
        """Test parsing table with malformed rows."""
        strategy.html_content = SAMPLE_MALFORMED_TABLE
        strategy.canonical_url = "https://test.url"
        
        fetch_result = FetchResult(
            strategy_name="TimelineOfRomanHistory",
            fetch_count=1
        )
        
        result = strategy.parse(fetch_result)
        
        # Should extract one valid event, skip malformed rows
        assert len(result.events) == 1
        assert result.events[0].start_year == 264
        assert result.events[0].is_bc_start is True
        
        # Check metadata shows skipped rows
        assert result.parse_metadata["skipped_rows"] >= 2
        assert len(strategy.parse_errors) > 0
    
    def test_parse_metadata_structure(self, strategy):
        """Test parse result includes proper metadata."""
        strategy.html_content = SAMPLE_TABLE_HTML
        strategy.canonical_url = "https://test.url"
        
        fetch_result = FetchResult(
            strategy_name="TimelineOfRomanHistory",
            fetch_count=1
        )
        
        result = strategy.parse(fetch_result)
        
        # Check metadata structure
        assert "elapsed_seconds" in result.parse_metadata
        assert "total_tables" in result.parse_metadata
        assert "total_rows_processed" in result.parse_metadata
        assert "events_extracted" in result.parse_metadata
        assert "skipped_rows" in result.parse_metadata
        assert "confidence_distribution" in result.parse_metadata
        
        # Check values make sense
        assert result.parse_metadata["total_tables"] == 1
        assert result.parse_metadata["events_extracted"] == len(result.events)


class TestArtifactGeneration:
    """Test artifact generation phase."""
    
    def test_generate_artifacts_structure(self, strategy):
        """Test artifact generation creates proper structure."""
        from historical_event import HistoricalEvent
        
        # Create mock parse result
        sample_events = [
            HistoricalEvent(
                title="Test Event 1",
                description="Test description",
                start_year=753,
                end_year=753,
                is_bc_start=True,
                is_bc_end=True,
                precision=100.0,
                weight=1,
                url="https://test.url",
                span_match_notes="test",
                category="roman_history"
            ),
            HistoricalEvent(
                title="Test Event 2",
                description="Another test",
                start_year=509,
                end_year=509,
                is_bc_start=True,
                is_bc_end=True,
                precision=100.0,
                weight=1,
                url="https://test.url",
                span_match_notes="test",
                category="roman_history"
            )
        ]
        
        parse_result = ParseResult(
            strategy_name="TimelineOfRomanHistory",
            events=sample_events,
            parse_metadata={
                "total_tables": 1,
                "events_extracted": 2
            }
        )
        
        artifact = strategy.generate_artifacts(parse_result)
        
        assert artifact is not None
        assert artifact.strategy_name == "TimelineOfRomanHistory"
        assert artifact.event_count == 2
        assert len(artifact.events) == 2
        assert artifact.run_id == strategy.run_id
        assert artifact.suggested_filename is not None
        assert "timeline_of_roman_history" in artifact.suggested_filename
    
    def test_generate_artifacts_empty_events(self, strategy):
        """Test artifact generation with no events."""
        parse_result = ParseResult(
            strategy_name="TimelineOfRomanHistory",
            events=[],
            parse_metadata={}
        )
        
        artifact = strategy.generate_artifacts(parse_result)
        
        assert artifact.event_count == 0
        assert len(artifact.events) == 0


class TestIntegration:
    """Integration tests for the full workflow."""
    
    @patch('strategies.timeline_of_roman_history.timeline_of_roman_history_strategy.get_html')
    def test_full_workflow_fetch_parse_generate(self, mock_get_html, strategy):
        """Test complete workflow: fetch → parse → generate."""
        mock_get_html.return_value = (
            (SAMPLE_TABLE_HTML, "https://final.url"),
            None
        )
        
        # Fetch
        fetch_result = strategy.fetch()
        assert fetch_result.fetch_count == 1
        
        # Parse
        parse_result = strategy.parse(fetch_result)
        assert len(parse_result.events) == 3
        
        # Generate artifacts
        artifact = strategy.generate_artifacts(parse_result)
        assert artifact.event_count == 3
        
        # Verify event conversion worked correctly
        for event in artifact.events:
            assert hasattr(event, 'start_year')
            assert hasattr(event, 'is_bc_start')
            assert hasattr(event, 'title')
    
    @patch('strategies.timeline_of_roman_history.timeline_of_roman_history_strategy.get_html')
    def test_confidence_distribution(self, mock_get_html, strategy):
        """Test that confidence distribution is calculated."""
        mock_get_html.return_value = (
            (SAMPLE_TABLE_WITH_ROWSPAN, "https://final.url"),
            None
        )
        
        fetch_result = strategy.fetch()
        parse_result = strategy.parse(fetch_result)
        
        # Check confidence distribution exists
        assert "confidence_distribution" in parse_result.parse_metadata
        conf_dist = parse_result.parse_metadata["confidence_distribution"]
        assert isinstance(conf_dist, dict)
        assert len(conf_dist) > 0


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_cleanup_logs_with_errors(self, strategy):
        """Test cleanup logs writes error file when errors exist."""
        strategy.parse_errors = [
            {"table_idx": 0, "row_idx": 5, "error": "Invalid date"}
        ]
        
        # Should not raise exception
        strategy.cleanup_logs()
        
        # Check error file was created
        error_files = list(strategy.output_dir.glob("parse_errors_*.json"))
        assert len(error_files) > 0
    
    def test_cleanup_logs_without_errors(self, strategy):
        """Test cleanup logs works with no errors."""
        strategy.parse_errors = []
        
        # Should not raise exception
        strategy.cleanup_logs()


class TestEventConversion:
    """Test RomanEvent to HistoricalEvent conversion."""
    
    def test_roman_event_to_historical_event_conversion(self, strategy):
        """Test that RomanEvents are properly converted to HistoricalEvents."""
        strategy.html_content = SAMPLE_TABLE_HTML
        strategy.canonical_url = "https://test.url"
        
        fetch_result = FetchResult(
            strategy_name="TimelineOfRomanHistory",
            fetch_count=1
        )
        
        result = strategy.parse(fetch_result)
        
        # All events should be HistoricalEvent instances
        for event in result.events:
            from historical_event import HistoricalEvent
            assert isinstance(event, HistoricalEvent)
            
            # Check required fields
            assert event.start_year > 0
            assert isinstance(event.is_bc_start, bool)
            assert event.precision > 0
            assert event.weight > 0
            assert event.url is not None
            assert event.title is not None
