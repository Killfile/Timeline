"""War event data structures."""

from dataclasses import dataclass


@dataclass
class WarEvent:
    """Structured war event extracted from table row."""
    start_year: int
    end_year: int
    title: str
    belligerents: list[str]
    notes: str = ""
    source_url: str = ""
    source_title: str = ""