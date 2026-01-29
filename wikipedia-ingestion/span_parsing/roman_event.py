"""RomanEvent domain model for timeline events

Represents a historical event from the Timeline of Roman History,
combining date information with event narrative and categorization.

This is a narrower domain model than HistoricalEvent, focused on Roman history specifics.
RomanEvents are converted to HistoricalEvent for export via import_schema.json.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from span_parsing.span import SpanPrecision
from span_parsing.table_row_date_parser import ConfidenceLevel

if TYPE_CHECKING:
    from historical_event import HistoricalEvent


class EventCategory(Enum):
    """Categories for Roman historical events."""
    FOUNDING = "founding"                    # Rome founding and early kings
    REPUBLIC = "republic"                    # Republican era events
    CONFLICTS = "conflicts"                  # Wars, battles, conflicts
    POLITICAL = "political"                  # Government, elections, laws
    CULTURAL = "cultural"                    # Arts, architecture, literature
    RELIGIOUS = "religious"                  # Religions, deities, temples
    ECONOMIC = "economic"                    # Trade, economy, taxation
    MILITARY = "military"                    # Military events, campaigns
    SUCCESSION = "succession"                # Emperor succession, dynasties
    NATURAL = "natural"                      # Natural disasters, plagues
    SOCIAL = "social"                        # Social movements, reforms
    ADMINISTRATIVE = "administrative"       # Administrative changes
    UNKNOWN = "unknown"                      # Uncategorized


@dataclass
class RomanEvent:
    """Represents a historical event in Roman history.
    
    Attributes:
        id: Unique identifier (assigned during ingestion)
        date: Event date with year, month, day and precision
        title: Event title/description
        description: Longer narrative description
        year: Year (negative for BC)
        month: Month (1-12) or None
        day: Day (1-31) or None
        is_bc: True if year is BC
        confidence: Date confidence level
        precision: Date precision level (YEAR_ONLY, MONTH_ONLY, EXACT, etc.)
        category: Event category for classification
        source: Wikipedia page/section source
        tags: Additional tags for filtering
        created_at: Timestamp when ingested
        rowspan_inherited: True if year was inherited from rowspan
        original_text: Original text from Wikipedia source
    """
    
    title: str
    year: int                                # Negative for BC
    month: Optional[int] = None              # 1-12
    day: Optional[int] = None                # 1-31
    is_bc: bool = False
    confidence: ConfidenceLevel = ConfidenceLevel.EXPLICIT
    precision: SpanPrecision = SpanPrecision.YEAR_ONLY
    
    # Additional fields
    description: str = ""
    category: EventCategory = EventCategory.UNKNOWN
    source: str = ""                         # Wikipedia page
    tags: List[str] = field(default_factory=list)
    id: Optional[str] = None                 # UUID or DB ID
    created_at: Optional[datetime] = None
    rowspan_inherited: bool = False
    original_text: str = ""
    
    def __post_init__(self):
        """Validate fields after initialization."""
        if not self.title or not self.title.strip():
            raise ValueError("Event title cannot be empty")
        if not (-10000 <= self.year <= 10000):
            raise ValueError(f"Year {self.year} out of valid range")
        if self.month is not None and not (1 <= self.month <= 12):
            raise ValueError(f"Month {self.month} out of range (1-12)")
        if self.day is not None and not (1 <= self.day <= 31):
            raise ValueError(f"Day {self.day} out of range (1-31)")
    
    @property
    def date_string(self) -> str:
        """Format date as human-readable string.
        
        Examples:
            "21 April 753 BC" - exact date
            "January 1066 AD" - month/year
            "1453" - year only
            "c. 1000 BC" - approximate
        """
        if self.confidence == ConfidenceLevel.APPROXIMATE:
            prefix = "c. "
        elif self.confidence == ConfidenceLevel.UNCERTAIN:
            prefix = "? "
        else:
            prefix = ""
        
        year_str = str(abs(self.year))
        era = " BC" if self.is_bc else " AD"
        
        if self.day and self.month:
            month_name = self._month_name(self.month)
            return f"{prefix}{self.day} {month_name} {year_str}{era}"
        elif self.month:
            month_name = self._month_name(self.month)
            return f"{prefix}{month_name} {year_str}{era}"
        else:
            return f"{prefix}{year_str}{era}"
    
    @property
    def is_legendary(self) -> bool:
        """Check if event is in legendary period (753 BC or earlier)."""
        return self.year <= -753
    
    @property
    def is_early_republic(self) -> bool:
        """Check if in early republic period (509-27 BC)."""
        return -509 <= self.year < -27
    
    @property
    def is_imperial(self) -> bool:
        """Check if in imperial period (27 BC-476 AD)."""
        return -27 <= self.year <= 476
    
    @property
    def is_byzantine(self) -> bool:
        """Check if in Byzantine period (476-1453 AD)."""
        return 476 < self.year <= 1453
    
    def period_name(self) -> str:
        """Get the historical period name."""
        if self.is_legendary:
            return "Legendary Period"
        elif self.is_early_republic:
            return "Early Republic"
        elif self.is_imperial:
            return "Imperial Period"
        elif self.is_byzantine:
            return "Byzantine Period"
        else:
            return "Ancient Rome"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "date_string": self.date_string,
            "year": self.year,
            "month": self.month,
            "day": self.day,
            "is_bc": self.is_bc,
            "confidence": self.confidence.value,
            "precision": self.precision,  # Already a float
            "category": self.category.value,
            "period": self.period_name(),
            "source": self.source,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "rowspan_inherited": self.rowspan_inherited,
        }
    
    @staticmethod
    def _month_name(month: int) -> str:
        """Convert month number to name."""
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        if 1 <= month <= 12:
            return months[month - 1]
        return f"Month{month}"
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.date_string}: {self.title}"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"RomanEvent(title={self.title!r}, year={self.year}, "
            f"month={self.month}, day={self.day}, is_bc={self.is_bc}, "
            f"confidence={self.confidence.value}, precision={self.precision})"
        )
    
    def to_historical_event(self, url: str, span_match_notes: str = "") -> "HistoricalEvent":
        """Convert RomanEvent to HistoricalEvent for JSON export.
        
        This conversion bridges the narrower Roman history domain model
        to the canonical HistoricalEvent format for import_schema.json export.
        
        Args:
            url: Source URL for the event
            span_match_notes: Optional notes about span matching/parsing
            
        Returns:
            HistoricalEvent instance ready for JSON serialization
        """
        from historical_event import HistoricalEvent
        
        # For point events, end date equals start date
        end_year = abs(self.year)
        end_month = self.month
        end_day = self.day
        
        # Calculate weight (duration in days, or 1 day for point events)
        weight = 1  # Default to 1 day for single-date events
        
        # Map confidence to span precision value
        # RomanEvent uses confidence levels; HistoricalEvent uses precision (0-100)
        precision_map = {
            ConfidenceLevel.EXPLICIT: 100.0,      # High precision
            ConfidenceLevel.INFERRED: 75.0,       # Good precision
            ConfidenceLevel.APPROXIMATE: 50.0,    # Medium precision
            ConfidenceLevel.UNCERTAIN: 25.0,      # Low precision
            ConfidenceLevel.LEGENDARY: 10.0,      # Very low precision
        }
        precision = precision_map.get(self.confidence, 50.0)
        
        return HistoricalEvent(
            title=self.title,
            description=self.description,
            start_year=abs(self.year),
            end_year=end_year,
            start_month=self.month,
            start_day=self.day,
            end_month=end_month,
            end_day=end_day,
            is_bc_start=self.is_bc,
            is_bc_end=self.is_bc,
            precision=precision,
            weight=weight,
            url=url,
            span_match_notes=span_match_notes or self.original_text or "",
            category=self.category.value if self.category else "roman_history",
            _debug_extraction={
                "roman_event_id": self.id,
                "rowspan_inherited": self.rowspan_inherited,
                "confidence": self.confidence.value,
                "span_precision": self.precision,
            } if self.id else None
        )
