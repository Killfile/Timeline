"""Dataclass representing a parsed date span."""

from dataclasses import dataclass

class SpanPrecision:
    """Enumeration of span precision levels."""
    EXACT = 1.0          # Exact date
    APPROXIMATE = 0.5    # Approximate date
    YEAR_ONLY = 1 / 100  # Year only precision
    MONTH_ONLY = 1 / 12   # Month only precision
    SEASON_ONLY = 1 / 4   # Season only precision (e.g., Spring, Summer, etc.)
    CIRCA = 0


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
    match_type: str
    precision: float = SpanPrecision.EXACT  # Precision of the span (1.0 = exact, 0.5 = approximate, etc.)
    weight: int | None = None  # Weight in days, computed from span length
