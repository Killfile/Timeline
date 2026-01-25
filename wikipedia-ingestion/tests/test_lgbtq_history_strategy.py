"""Tests for the main LGBTQ history strategy."""

import pytest
from pathlib import Path
from strategies.lgbtq_history.lgbtq_history_strategy import LgbtqHistoryStrategy


class TestLgbtqHistoryStrategy:
    """Test the main LGBTQ history ingestion strategy."""

    def setup_method(self):
        self.strategy = LgbtqHistoryStrategy(run_id="test_run", output_dir=Path("/tmp/test"))

    def test_strategy_creation(self):
        """Test that the strategy can be created."""
        assert self.strategy is not None
        assert self.strategy.run_id == "test_run"
        assert self.strategy.output_dir == Path("/tmp/test")

    def test_name(self):
        """Test strategy name."""
        assert self.strategy.name() == "lgbtq_history"