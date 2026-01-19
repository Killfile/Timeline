"""Tests for war row parsing strategies."""

import pytest
from unittest.mock import Mock

from strategies.wars.war_row_parsing_strategies import (
    MergedDateCellsStrategy,
    SingleDateSeparateColumnsStrategy,
    TwoDateColumnsStrategy,
)
from strategies.wars.war_row_parser_factory import WarRowParserFactory
from strategies.wars.wars_strategy import WarEvent


class TestMergedDateCellsStrategy:
    """Test the merged date cells strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = MergedDateCellsStrategy()

    def test_can_parse_merged_date_range(self):
        """Test detection of merged date cells with range."""
        cell_texts = ["2300–2200 BC", "Mari-Ebla War", "Ebla vs Mari"]
        assert self.strategy.can_parse(cell_texts)

    def test_can_parse_single_date_in_merged(self):
        """Test detection when single date is in merged format."""
        cell_texts = ["1000 BC", "Some War", "Belligerents"]
        assert not self.strategy.can_parse(cell_texts)

    def test_parse_merged_date_range(self):
        """Test parsing merged date range."""
        cell_texts = ["2300–2200 BC", "Mari-Ebla War", "Ebla vs Mari"]
        result = self.strategy.parse_row(cell_texts, "http://test.com", "Test Page")

        assert result is not None
        assert result.start_year == -2300
        assert result.end_year == -2200
        assert result.title == "Mari-Ebla War"
        assert result.belligerents == ["Ebla", "Mari"]

    def test_parse_with_notes(self):
        """Test parsing with additional notes column."""
        cell_texts = ["2300–2200 BC", "Mari-Ebla War", "Ebla vs Mari", "Some notes"]
        result = self.strategy.parse_row(cell_texts, "http://test.com", "Test Page")

        assert result is not None
        assert result.notes == "Some notes"


class TestSingleDateSeparateColumnsStrategy:
    """Test the single date separate columns strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = SingleDateSeparateColumnsStrategy()

    def test_can_parse_single_date_separate(self):
        """Test detection of single date with separate columns."""
        cell_texts = ["2300 BC", "Mari-Ebla War", "Ebla vs Mari"]
        assert self.strategy.can_parse(cell_texts)

    def test_can_parse_rejects_date_in_second_cell(self):
        """Test rejection when second cell contains a date."""
        cell_texts = ["2300 BC", "2200 BC", "Mari-Ebla War", "Ebla vs Mari"]
        assert not self.strategy.can_parse(cell_texts)

    def test_parse_single_date(self):
        """Test parsing single date row."""
        cell_texts = ["2300 BC", "Mari-Ebla War", "Ebla vs Mari"]
        result = self.strategy.parse_row(cell_texts, "http://test.com", "Test Page")

        assert result is not None
        assert result.start_year == -2300
        assert result.end_year == -2300  # Same as start
        assert result.title == "Mari-Ebla War"
        assert result.belligerents == ["Ebla", "Mari"]


class TestTwoDateColumnsStrategy:
    """Test the two date columns strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = TwoDateColumnsStrategy()

    def test_can_parse_two_dates(self):
        """Test detection of two date columns."""
        cell_texts = ["2300 BC", "2200 BC", "Mari-Ebla War", "Ebla vs Mari"]
        assert self.strategy.can_parse(cell_texts)

    def test_can_parse_rejects_single_date(self):
        """Test rejection when only one date column."""
        cell_texts = ["2300 BC", "Mari-Ebla War", "Ebla vs Mari"]
        assert not self.strategy.can_parse(cell_texts)

    def test_parse_two_dates(self):
        """Test parsing two date columns."""
        cell_texts = ["2300 BC", "2200 BC", "Mari-Ebla War", "Ebla vs Mari"]
        result = self.strategy.parse_row(cell_texts, "http://test.com", "Test Page")

        assert result is not None
        assert result.start_year == -2300
        assert result.end_year == -2200
        assert result.title == "Mari-Ebla War"
        assert result.belligerents == ["Ebla", "Mari"]


class TestWarRowParserFactory:
    """Test the parser factory."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = WarRowParserFactory()

    def test_get_parser_for_merged_dates(self):
        """Test factory selects merged date strategy."""
        cell_texts = ["2300–2200 BC", "Mari-Ebla War", "Ebla vs Mari"]
        parser = self.factory.get_parser(cell_texts)

        assert isinstance(parser, MergedDateCellsStrategy)

    def test_get_parser_for_single_date(self):
        """Test factory selects single date strategy."""
        cell_texts = ["2300 BC", "Mari-Ebla War", "Ebla vs Mari"]
        parser = self.factory.get_parser(cell_texts)

        assert isinstance(parser, SingleDateSeparateColumnsStrategy)

    def test_get_parser_for_two_dates(self):
        """Test factory selects two date strategy."""
        cell_texts = ["2300 BC", "2200 BC", "Mari-Ebla War", "Ebla vs Mari"]
        parser = self.factory.get_parser(cell_texts)

        assert isinstance(parser, TwoDateColumnsStrategy)

    def test_get_parser_no_match(self):
        """Test factory returns None when no strategy matches."""
        cell_texts = ["Not a date", "Also not a date", "Still not"]
        parser = self.factory.get_parser(cell_texts)

        assert parser is None