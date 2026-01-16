"""Dataclass representing a parsed date span."""

from dataclasses import dataclass
import json

class SpanPrecision:
    """Enumeration of span precision levels."""
    EXACT = 1000.0          # Exact date
    APPROXIMATE = 100.0    # Approximate date
    YEAR_ONLY = 10.0  # Year only precision
    MONTH_ONLY = 1.0  # Month only precision
    SEASON_ONLY = 0.25   # Season only precision (e.g., Spring, Summer, etc.)
    # CIRCA should be a small, non-zero precision value so it doesn't
    # collapse downstream calculations to zero. Use a moderate approximate
    # precision (smaller than APPROXIMATE but larger than YEAR_ONLY).
    CIRCA = 1/100  # Circa precision -- Minimum value b/c of database precision limits
    FALLBACK = 0.0    # Fallback precision when no better info is available


@dataclass
class Span:
    """Represents a parsed date span with start/end dates and metadata."""
    start_year: int
    end_year: int
    start_month: int
    start_day: int
    end_month: int
    end_day: int
    start_year_is_bc: bool
    end_year_is_bc: bool
    match_type: str = "Unspecified"  # Description of how the span was matched
    precision: float = SpanPrecision.EXACT  # Precision of the span
    weight: int | None = None  # Weight in days, computed from span length
    
    # Legacy property for backwards compatibility
    @property
    def is_bc(self) -> bool:
        """Legacy property. Returns True if both start and end are BC."""
        return self.start_year_is_bc and self.end_year_is_bc

    def is_valid(self) -> bool:
        """Validate that this span has logical date values.
        
        Returns:
            True if the span is valid, False otherwise
        """
        # Year 0 doesn't exist historically (1 BC → 1 AD)
        if int(self.start_year) == 0 or int(self.end_year) == 0:
            return False
        
        # Convert to a comparable form where AD years are positive and BC years are negative
        # BC: 100 BC = -99, 1 BC = 0, AD: 1 AD = 1, 100 AD = 100
        def to_comparable(year: int, is_bc: bool) -> int:
            if is_bc:
                return -year + 1
            return year
        
        start_comparable = to_comparable(self.start_year, self.start_year_is_bc)
        end_comparable = to_comparable(self.end_year, self.end_year_is_bc)
        
        # Start must be before or equal to end
        if start_comparable > end_comparable:
            return False
        
        # If same year, check months and days
        if start_comparable == end_comparable:
            if self.start_month > self.end_month:
                return False
            if self.start_month == self.end_month:
                if self.start_day > self.end_day:
                    return False
                
        # Sanity check for month/day ranges (not exhaustive)
        if not (1 <= self.start_month <= 12 and 1 <= self.end_month <= 12):
            return False
        if not (1 <= self.start_day <= 31 and 1 <= self.end_day <= 31):
            return False
        
        
        return True

    def to_dict(self) -> dict:
        """Return a dictionary representation of the Span for JSON serialization."""
        return {
            "start_year": self.start_year,
            "start_month": self.start_month,
            "start_day": self.start_day,
            "end_year": self.end_year,
            "end_month": self.end_month,
            "end_day": self.end_day,
            "start_year_is_bc": self.start_year_is_bc,
            "end_year_is_bc": self.end_year_is_bc,
            "is_bc": self.is_bc,  # Legacy field for backwards compatibility
            "precision": float(self.precision) if self.precision is not None else None,
            "match_type": self.match_type,
            "weight": self.weight,
        }


class SpanEncoder(json.JSONEncoder):
    """JSON encoder that handles Span objects."""
    
    def default(self, obj):
        if isinstance(obj, Span):
            return obj.to_dict()
        # Let the base class handle everything else
        return super().default(obj)
