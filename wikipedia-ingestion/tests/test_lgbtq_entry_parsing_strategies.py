"""Tests for LGBTQ entry parsing strategies."""

import pytest
from strategies.lgbtq_history.lgbtq_entry_parsing_strategies import (
    SimpleDateEntryStrategy,
    MainArticleEntryStrategy,
    ColonEndingEntryStrategy,
    AdditionalContentStrategy,
)
from strategies.lgbtq_history.lgbtq_entry_parser_factory import LgbtqEntryParserFactory
from strategies.lgbtq_history.lgbtq_event import LgbtqEvent


class TestSimpleDateEntryStrategy:
    """Test the simple date entry parsing strategy."""

    def setup_method(self):
        self.strategy = SimpleDateEntryStrategy()

    def test_can_parse_simple_date_entry(self):
        """Test detection of simple date entries."""
        text = "c. 540 – 530 BCE – Wall paintings from the Etruscan Tomb of the Bulls"
        assert self.strategy.can_parse(text, False)

    def test_can_parse_without_circa(self):
        """Test detection without circa."""
        text = "534 – 492 BCE – Duke Ling of Wey and Mizi Xia"
        assert self.strategy.can_parse(text, False)

    def test_cannot_parse_main_article(self):
        """Test that main article entries are not handled by this strategy."""
        text = "c. 486 BCE – King Darius I – Main article: Holiness Code – adopts the Holiness Code"
        assert not self.strategy.can_parse(text, False)

    def test_parse_simple_entry(self):
        """Test parsing a simple date entry."""
        text = "c. 540 – 530 BCE – Wall paintings from the Etruscan Tomb of the Bulls depict homosexual intercourse."
        source_url = "https://example.com"
        source_title = "Test Page"

        result = self.strategy.parse_entry(text, source_url, source_title, False)

        assert result is not None
        assert result.title == "Wall paintings from the Etruscan Tomb of the Bulls depict homosexual intercourse"
        assert result.date_text == "c. 540 – 530 BCE"
        assert result.is_bc_context == False
        assert result.source_url == source_url
        assert result.source_title == source_title

    def test_parse_with_citations_removed(self):
        """Test that citations are removed from description."""
        text = "534 – 492 BCE – Duke Ling of Wey and Mizi Xia had a loving same-sex relationship.[24]"
        source_url = "https://example.com"
        source_title = "Test Page"

        result = self.strategy.parse_entry(text, source_url, source_title, False)

        assert result is not None
        assert "[24]" not in result.description


class TestMainArticleEntryStrategy:
    """Test the main article entry parsing strategy."""

    def setup_method(self):
        self.strategy = MainArticleEntryStrategy()

    def test_can_parse_main_article_entry(self):
        """Test detection of main article entries."""
        text = "c. 486 BCE – King Darius I – Main article: Holiness Code – adopts the Holiness Code"
        assert self.strategy.can_parse(text, False)

    def test_cannot_parse_simple_entry(self):
        """Test that simple entries are not handled by this strategy."""
        text = "c. 540 – 530 BCE – Wall paintings from the Etruscan Tomb of the Bulls"
        assert not self.strategy.can_parse(text, False)

    def test_parse_main_article_entry(self):
        """Test parsing a main article entry."""
        text = "c. 486 BCE – King Darius I – Main article: Holiness Code – adopts the Holiness Code of Leviticus"
        source_url = "https://example.com"
        source_title = "Test Page"

        result = self.strategy.parse_entry(text, source_url, source_title, False)

        assert result is not None
        assert result.title == "King Darius I: adopts the Holiness Code of Leviticus"
        assert result.date_text == "c. 486 BCE"
        assert result.has_main_article == True
        assert result.main_article_url == "Holiness Code"


class TestColonEndingEntryStrategy:
    """Test the colon-ending entry parsing strategy."""

    def setup_method(self):
        self.strategy = ColonEndingEntryStrategy()

    def test_can_parse_colon_ending(self):
        """Test detection of colon-ending entries."""
        text = "c. 1500 BCE – c. 1101 BCE – The Code of Assura:"
        assert self.strategy.can_parse(text, False)

    def test_can_parse_with_citations(self):
        """Test detection with citations before colon."""
        text = "c. 1500 BCE – c. 1101 BCE – The Code of Assura:[12][13][14][15][16][17]"
        assert self.strategy.can_parse(text, False)

    def test_cannot_parse_without_colon(self):
        """Test that entries without colon are not detected."""
        text = "c. 540 – 530 BCE – Wall paintings from the Etruscan Tomb of the Bulls"
        assert not self.strategy.can_parse(text, False)

    def test_parse_colon_ending_entry(self):
        """Test parsing a colon-ending entry."""
        text = "c. 1500 BCE – c. 1101 BCE – The Code of Assura:"
        source_url = "https://example.com"
        source_title = "Test Page"

        result = self.strategy.parse_entry(text, source_url, source_title, False)

        assert result is not None
        assert result.title == "The Code of Assura"
        assert result.date_text == "c. 1500 BCE – c. 1101 BCE"
        assert result.description == ""  # Should be empty, to be filled by additional content


class TestLgbtqEntryParserFactory:
    """Test the parser factory."""

    def setup_method(self):
        self.factory = LgbtqEntryParserFactory()

    def test_get_parser_for_simple_entry(self):
        """Test factory returns correct parser for simple entries."""
        text = "c. 540 – 530 BCE – Wall paintings from the Etruscan Tomb of the Bulls"
        parser = self.factory.get_parser(text, False)

        assert isinstance(parser, SimpleDateEntryStrategy)

    def test_get_parser_for_main_article(self):
        """Test factory returns correct parser for main article entries."""
        text = "c. 486 BCE – King Darius I – Main article: Holiness Code – adopts the Holiness Code"
        parser = self.factory.get_parser(text, False)

        assert isinstance(parser, MainArticleEntryStrategy)

    def test_get_parser_for_colon_ending(self):
        """Test factory returns correct parser for colon-ending entries."""
        text = "c. 1500 BCE – c. 1101 BCE – The Code of Assura:"
        parser = self.factory.get_parser(text, False)

        assert isinstance(parser, ColonEndingEntryStrategy)

    def test_get_parser_returns_none_for_unmatched(self):
        """Test factory returns None for unmatched text."""
        text = "This is not a timeline entry"
        parser = self.factory.get_parser(text, False)

        assert parser is None

    def test_get_additional_content_parser(self):
        """Test getting additional content parser."""
        parser = self.factory.get_additional_content_parser()
        assert isinstance(parser, AdditionalContentStrategy)