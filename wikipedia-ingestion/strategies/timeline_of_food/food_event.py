"""Food event data model for Timeline of Food ingestion strategy.

This module defines the FoodEvent dataclass which represents a single food-related
historical event extracted from the Wikipedia "Timeline of Food" article.
"""

from dataclasses import dataclass, field
from hashlib import md5
from typing import Any

from historical_event import HistoricalEvent


@dataclass
class FoodEvent:
    """Food-related historical event with rich date handling.
    
    This class extends the standard HistoricalEvent pattern with additional
    fields specific to food history events.
    """
    
    # Basic identity
    event_key: str  # Deterministic key for deduplication (MD5)
    source: str = "Timeline of Food"
    
    # Date information (flexible to handle varied formats)
    date_explicit: int | None = None  # Year if explicitly stated (e.g., 1516)
    date_range_start: int | None = None  # Start of inferred range (e.g., 1500 for "16th century")
    date_range_end: int | None = None  # End of inferred range
    is_bc_start: bool = False  # True if start date is BC
    is_bc_end: bool = False  # True if end date is BC
    is_date_approximate: bool = False  # True if "~" or "circa" format
    is_date_range: bool = False  # True if range format (e.g., "8000-5000 BCE")
    confidence_level: str = "explicit"  # "explicit" | "inferred" | "approximate" | "contentious" | "fallback"
    
    # Event content
    title: str = ""  # Short event title (first 50-70 chars)
    description: str = ""  # Full event description
    food_category: str | None = None  # Extracted category if identifiable (e.g., "Cheese", "Bread")
    
    # Hierarchical context (section where event was found)
    section_name: str = ""  # E.g., "4000-2000 BCE", "19th century"
    section_date_range_start: int = 0  # Section's implied date range
    section_date_range_end: int = 0
    
    # References and metadata
    wikipedia_links: list[str] = field(default_factory=list)  # Wiki links found in description
    external_references: list[int] = field(default_factory=list)  # Citation indices [1], [2], etc.
    source_format: str = "bullet"  # "bullet" | "table" | "mixed"
    
    # Data quality tracking
    parsing_notes: str | None = None  # Any parsing issues or assumptions
    span_match_notes: str = ""  # Notes about how the date span was matched/parsed
    precision: float = 1.0  # Precision value (higher = more precise)
    
    def __post_init__(self):
        """Generate title and event_key if not provided."""
        if not self.title and self.description:
            self.title = self.generate_title()
        
        if not self.event_key:
            self.event_key = self.generate_event_key()
    
    def generate_title(self) -> str:
        """Generate title from description (first 50-70 characters).
        
        Returns:
            Title string truncated to 50-70 characters at word boundary.
        """
        if not self.description:
            return ""
        
        # Remove extra whitespace
        clean_desc = " ".join(self.description.split())
        
        # Truncate to 70 chars
        if len(clean_desc) <= 70:
            return clean_desc
        
        # Find word boundary between 50-70 chars
        for i in range(70, 49, -1):
            if clean_desc[i] == ' ':
                return clean_desc[:i].strip()
        
        # If no space found, hard truncate at 70
        return clean_desc[:70].strip()
    
    def generate_event_key(self) -> str:
        """Generate deterministic event key using MD5.
        
        Key components: date + title + source
        This ensures events are deduplicated across ingestion runs.
        
        Returns:
            MD5 hash string (32 characters)
        """
        date_str = str(self.date_explicit or self.date_range_start or 0)
        key_input = f"{date_str}|{self.title}|{self.source}"
        return md5(key_input.encode('utf-8')).hexdigest()
    
    def to_historical_event(self) -> HistoricalEvent:
        """Convert to standard HistoricalEvent for database storage.
        
        Maps FoodEvent fields to HistoricalEvent schema. Uses section date range
        as fallback if explicit dates are not available.
        
        Returns:
            HistoricalEvent instance ready for database insertion.
        """
        # Determine start/end years
        start_year = self.date_explicit or self.date_range_start or self.section_date_range_start
        end_year = self.date_explicit or self.date_range_end or self.section_date_range_end
        
        # Ensure we have positive years for database storage
        # BC years are stored as positive with is_bc flags
        if start_year < 0:
            start_year = abs(start_year)
            is_bc_start = True
        else:
            is_bc_start = self.is_bc_start
        
        if end_year < 0:
            end_year = abs(end_year)
            is_bc_end = True
        else:
            is_bc_end = self.is_bc_end
        
        # Calculate weight (duration in days) for packing priority
        # Longer duration events get lower weight (rendered smaller)
        year_span = abs(end_year - start_year) + 1
        weight = year_span * 365
        
        return HistoricalEvent(
            title=self.title,
            description=self.description,
            start_year=start_year,
            end_year=end_year,
            is_bc_start=is_bc_start,
            is_bc_end=is_bc_end,
            precision=self.precision,
            weight=weight,
            url=f"https://en.wikipedia.org/wiki/Timeline_of_food",
            span_match_notes=self.span_match_notes,
            category="Food History",
        )
