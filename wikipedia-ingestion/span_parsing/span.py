"""Dataclass representing a parsed date span."""

from dataclasses import dataclass


@dataclass
class Span:
    """Represents a parsed date span with start/end dates and metadata."""
    start_year: int
    end_year: int
    start_month: int
    start_day: int
    end_month: int
    end_day: int
    is_bc: bool
    precision: str
    match_type: str
    weight: int | None = None  # Weight in days, computed from span length
