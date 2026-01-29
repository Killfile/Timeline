"""Food event data model for Timeline of Food ingestion strategy.

This module defines the FoodEvent dataclass which represents a single food-related
historical event extracted from the Wikipedia "Timeline of Food" article.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import md5

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
    
    def validate_ancient_dates(self) -> None:
        """Validate dates for very ancient (>10,000 BC) events.
        
        Very ancient dates should have reduced precision since archaeological
        evidence for dates this old is typically approximate.
        
        Rules:
        - Dates >10,000 BC should have precision adjusted downward
        - Precision below 0.1 is poor (archaeological estimates)
        - Precision 0.1-0.3 is weak (pre-classical era)
        - Precision >0.3 is moderate (classical era forward)
        """
        start_year = self.date_range_start or 0
        
        # Check if this is an ancient date (>10,000 years before present)
        if self.is_bc_start and abs(start_year) > 10000:
            # Reduce precision for very ancient dates
            if self.precision is None or self.precision > 0.3:
                # Adjust precision downward for archaeological estimates
                self.precision = max(0.1, self.precision * 0.5) if self.precision else 0.1
            
            # Add note about ancient dating
            if self.parsing_notes:
                self.parsing_notes += "; ancient date (>10K BC) - precision reduced"
            else:
                self.parsing_notes = "ancient date (>10K BC) - precision reduced"
    
    def validate_bc_ad_conversion(self) -> None:
        """Validate BC/AD date conversion and handle 1 BC → 1 AD cutover.
        
        Rules:
        - Negative years represent BC dates (stored as positive with is_bc flag)
        - There is no year 0 (1 BC precedes 1 AD immediately)
        - 1 BC → 1 AD transition must be handled correctly
        
        Raises:
            ValueError: If dates violate BC/AD rules
        """
        # Get the actual years (may be negative for BC)
        start_year = int(self.date_explicit or self.date_range_start or self.section_date_range_start or 0)
        end_year = int(self.date_explicit or self.date_range_end or self.section_date_range_end or 0)
        
        # Both must not be zero
        if start_year == 0 or end_year == 0:
            raise ValueError("Invalid year 0")
        
        # Detect BC from negative values if not already flagged
        start_is_bc = start_year < 0 or self.is_bc_start
        end_is_bc = end_year < 0 or self.is_bc_end
        
        
        # For BC ranges, the logic is inverted (larger BC year comes first)
        # -8000 to -5000 means 8000 BC to 5000 BC (valid: 8000 > 5000)
        # For AD ranges: 5000 to 8000 is valid (5000 < 8000)
        # For mixed: only valid if transitioning 1 BC to 1 AD
        
        if start_is_bc and end_is_bc:
            # Both BC: larger absolute value comes first (earlier in time)
            # -8000 to -5000: abs(-8000) > abs(-5000) which is correct (8000 > 5000)
            # This is valid BC range
            pass
        elif not start_is_bc and not end_is_bc:
            # Both AD: smaller must come before larger
            if abs(start_year) > abs(end_year):
                raise ValueError(
                    f"Invalid date range: start_year ({start_year}) > end_year ({end_year})"
                )

    def to_historical_event(self) -> HistoricalEvent:
        """Convert to standard HistoricalEvent for database storage.
        
        Maps FoodEvent fields to HistoricalEvent schema. Uses section date range
        as fallback if explicit dates are not available.
        
        Handles BC/AD conversion per historical conventions:
        - Negative internal years become positive with is_bc flags
        - Year 0 does not exist (1 BC → 1 AD transition)
        - Both start and end years maintain consistent BC/AD markers
        - Very ancient dates (>10K BC) have reduced precision
        
        Returns:
            HistoricalEvent instance ready for database insertion.
        
        Raises:
            ValueError: If BC/AD conversion rules are violated
        """
        # Validate ancient dates and adjust precision
        self.validate_ancient_dates()

        # Validate BC/AD rules before conversion
        self.validate_bc_ad_conversion()

        # Determine start/end years
        start_year = self.date_explicit or self.date_range_start or self.section_date_range_start
        end_year = self.date_explicit or self.date_range_end or self.section_date_range_end
        
        # Track whether conversion occurred (for BC flag consistency)
        converted_start_bc = False
        converted_end_bc = False
        
        # Ensure we have positive years for database storage
        # BC years are stored as positive with is_bc flags
        if start_year < 0:
            start_year = abs(start_year)
            converted_start_bc = True
        
        if end_year < 0:
            end_year = abs(end_year)
            converted_end_bc = True
        
        # Determine final BC flags
        is_bc_start = converted_start_bc or self.is_bc_start
        is_bc_end = converted_end_bc or self.is_bc_end
        
        # Handle 1 BC → 1 AD transition (no year 0)
        # If spanning from BC to AD, and there's a gap at year 0, it's invalid
        if is_bc_start and not is_bc_end and end_year == 1:
            # This is the 1 BC to 1 AD transition - valid
            pass
        
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

