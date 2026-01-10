"""Canonical event schema for timeline ingestion.

This module defines the strongly-typed schema that ALL ingestion strategies
must use when serializing events to JSON artifacts.

Schema Requirements:
- All date fields at top level (not nested)
- Required fields: title, description, url, start_year, end_year, 
  is_bc_start, is_bc_end, weight, precision
- Optional fields: start_month, start_day, end_month, end_day, category, pageid
- Debug/metadata fields prefixed with underscore
"""

from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any


@dataclass
class CanonicalEvent:
    """Canonical event schema for timeline ingestion.
    
    This is the authoritative schema that all ingestion strategies must produce.
    All fields map directly to database columns or are used for debugging.
    
    Required Fields:
        title: Event title/summary (max 500 chars)
        description: Full event description (max 500 chars)
        url: Source Wikipedia URL
        start_year: Start year (positive int, era indicated by is_bc_start)
        end_year: End year (positive int, era indicated by is_bc_end)
        is_bc_start: True if start year is BC
        is_bc_end: True if end year is BC
        weight: Event duration in days (int, for packing priority)
        precision: Date precision value (float, represents uncertainty)
        
    Optional Fields:
        start_month: Start month (1-12, or None for year-only precision)
        start_day: Start day (1-31, or None)
        end_month: End month (1-12, or None)
        end_day: End day (1-31, or None)
        category: Event category/tag from extraction
        pageid: Wikipedia page ID (for deduplication)
        
    Debug/Internal Fields (prefixed with _):
        _debug_extraction: Debug metadata from extraction process
    """
    # Required fields
    title: str
    description: str
    url: str
    start_year: int
    end_year: int
    is_bc_start: bool
    is_bc_end: bool
    weight: int
    precision: float
    
    # Optional fields
    start_month: int | None = None
    start_day: int | None = None
    end_month: int | None = None
    end_day: int | None = None
    category: str | None = None
    pageid: int | None = None
    
    # Debug/metadata fields
    _debug_extraction: dict | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.
        
        Returns dict with all fields, excluding None values for optional fields
        unless they should be explicitly None (like category can be null in DB).
        """
        result = asdict(self)
        # Keep None values for fields that map to nullable DB columns
        # Remove None for fields that shouldn't appear in JSON if not set
        return result
    
    @classmethod
    def from_span_dict(
        cls,
        title: str,
        description: str,
        url: str,
        span_dict: dict,
        category: str | None = None,
        pageid: int | None = None,
        debug_info: dict | None = None
    ) -> CanonicalEvent:
        """Create CanonicalEvent from a span dictionary.
        
        This helper extracts date fields from nested span objects (as used by
        some parsers) and flattens them to the canonical top-level structure.
        
        Args:
            title: Event title
            description: Event description
            url: Source URL
            span_dict: Dictionary with date fields (may be nested or flat)
            category: Optional category
            pageid: Optional Wikipedia page ID
            debug_info: Optional debug metadata
            
        Returns:
            CanonicalEvent with flattened date fields
        """
        return cls(
            title=title,
            description=description,
            url=url,
            start_year=span_dict['start_year'],
            end_year=span_dict['end_year'],
            start_month=span_dict.get('start_month'),
            start_day=span_dict.get('start_day'),
            end_month=span_dict.get('end_month'),
            end_day=span_dict.get('end_day'),
            is_bc_start=span_dict['start_year_is_bc'],
            is_bc_end=span_dict['end_year_is_bc'],
            weight=span_dict['weight'],
            precision=span_dict['precision'],
            category=category,
            pageid=pageid,
            _debug_extraction=debug_info
        )


def validate_canonical_event(event_dict: dict) -> tuple[bool, str]:
    """Validate that a dictionary conforms to canonical event schema.
    
    This is a lightweight validation for use in loaders/validators.
    For full validation including type checking, see strategy_base.validate_event_dict.
    
    Args:
        event_dict: Dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.
    """
    # Check for nested span object first (indicates non-canonical format)
    if 'span' in event_dict:
        return False, "Event has nested 'span' object - date fields must be at top level"
    
    required_fields = {
        'title', 'description', 'url',
        'start_year', 'end_year',
        'is_bc_start', 'is_bc_end',
        'weight', 'precision'
    }
    
    missing = required_fields - set(event_dict.keys())
    if missing:
        return False, f"Missing required fields: {', '.join(sorted(missing))}"
    
    return True, ""
