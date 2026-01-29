"""Tests for ingestion strategy factory integration."""

from unittest.mock import MagicMock, patch, mock_open

from strategies.ingestion_strategy_factory import IngestionStrategyFactory, IngestionStrategies
from strategies.timeline_of_roman_history.timeline_of_roman_history_strategy import (
    TimelineOfRomanHistoryStrategy,
)


def test_factory_creates_timeline_of_roman_history_strategy(tmp_path):
    """Factory returns TimelineOfRomanHistoryStrategy for roman history enum."""
    strategy = IngestionStrategyFactory.get_strategy(
        IngestionStrategies.TIMELINE_OF_ROMAN_HISTORY,
        run_id="test",
        output_dir=tmp_path,
    )

    assert isinstance(strategy, TimelineOfRomanHistoryStrategy)
    assert strategy.name() == "timeline_of_roman_history"


def test_ingest_wikipedia_accepts_timeline_of_roman_history():
    """ingest() should dispatch timeline_of_roman_history to the factory."""
    from ingest_wikipedia import ingest
    from strategies.strategy_base import ArtifactData

    dummy_strategy = MagicMock()
    dummy_strategy.name.return_value = "timeline_of_roman_history"
    dummy_strategy.ingest.return_value = ArtifactData(
        strategy_name="TimelineOfRomanHistory",
        run_id="test",
        generated_at_utc="2026-01-28T00:00:00Z",
        event_count=0,
        events=[],
        metadata={},
        suggested_filename="events_timeline_of_roman_history_test.json",
    )

    with patch(
        "ingest_wikipedia.IngestionStrategyFactory.get_strategy",
        return_value=dummy_strategy,
    ) as mock_factory, patch("builtins.open", mock_open()), patch("json.dump"):
        ingest(["timeline_of_roman_history"])

    mock_factory.assert_called_once()
    args, _ = mock_factory.call_args
    assert args[0] == IngestionStrategies.TIMELINE_OF_ROMAN_HISTORY
    dummy_strategy.ingest.assert_called_once()
    dummy_strategy.cleanup_logs.assert_called_once()
