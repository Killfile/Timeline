"""Data structures for LGBTQ v2 parsing."""

from dataclasses import dataclass
from typing import List, Any, Optional
from abc import ABC, abstractmethod

from historical_event import HistoricalEvent


@dataclass
class PageData:
    """Represents the parsed structure of a page."""
    url: str
    title: str
    hierarchies: List[Any]  # List of hierarchy objects (different types for different page structures)


@dataclass
class EventCandidate:
    """Represents a potential event to be parsed."""
    text: str
    context: dict  # Additional context like date hints, hierarchy level, etc.


class PageParsingStrategy(ABC):
    """Strategy for parsing different types of timeline pages."""

    @abstractmethod
    def can_parse(self, url: str, soup) -> bool:
        """Check if this strategy can parse the given page."""
        pass

    @abstractmethod
    def parse_page(self, url: str, soup) -> Optional[PageData]:
        """Parse the page into PageData structure."""
        pass


class HierarchyParsingStrategy(ABC):
    """Strategy for parsing different hierarchy structures within pages."""

    @abstractmethod
    def can_parse(self, hierarchy) -> bool:
        """Check if this strategy can parse the given hierarchy."""
        pass

    @abstractmethod
    def parse_hierarchy(self, hierarchy) -> List[EventCandidate]:
        """Parse hierarchy into event candidates."""
        pass


class EventParsingStrategy(ABC):
    """Strategy for parsing individual events from text."""

    @abstractmethod
    def can_parse(self, candidate: EventCandidate) -> bool:
        """Check if this strategy can parse the given event candidate."""
        pass

    @abstractmethod
    def parse_event(self, candidate: EventCandidate, source_url: str) -> Optional[HistoricalEvent]:
        """Parse event candidate into HistoricalEvent."""
        pass