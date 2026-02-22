from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class HistoricalEvent:
    """Represents a single historical event with validated fields.
    
    This is the canonical representation of an event across all ingestion strategies.
    All strategies must return HistoricalEvent instances rather than raw dictionaries
    to ensure consistency and type safety.
    
    Required fields:
        title: Event title (non-empty string)
        start_year: Start year (positive int)
        end_year: End year (positive int)
        is_bc_start: True if start date is BC
        is_bc_end: True if end date is BC
        precision: Precision value (higher = more precise)
        weight: Duration in days (for packing priority)
        url: Source URL
        span_match_notes: Notes about how the date span was matched/parsed
    
    Optional fields:
        description: Event description
        start_month: Start month (1-12)
        start_day: Start day (1-31)
        end_month: End month (1-12)
        end_day: End day (1-31)
        category: Event categorization
        _debug_extraction: Extraction diagnostics
    """
    title: str
    start_year: int
    end_year: int
    is_bc_start: bool
    is_bc_end: bool
    precision: float
    weight: int
    url: str
    span_match_notes: str
    description: str | None = None
    start_month: int | None = None
    start_day: int | None = None
    end_month: int | None = None
    end_day: int | None = None
    category: str | None = None
    _debug_extraction: dict | None = None
    
    def __post_init__(self) -> None:
        """Validate field values after initialization."""
        is_valid, error_message = self.validate()
        if not is_valid:
            raise ValueError(f"Invalid HistoricalEvent: {error_message}")
    
    def validate(self) -> tuple[bool, str]:
        """Validate that this event conforms to the expected schema.
        
        Returns:
            Tuple of (is_valid, error_message). error_message is empty string if valid.
        """
        # Validate required string fields
        if not isinstance(self.title, str):
            return False, f"Field 'title' must be str, got {type(self.title).__name__}"
        if not self.title.strip():
            return False, "Field 'title' cannot be empty"
        
        if not isinstance(self.url, str):
            return False, f"Field 'url' must be str, got {type(self.url).__name__}"
        
        if not isinstance(self.span_match_notes, str):
            return False, f"Field 'span_match_notes' must be str, got {type(self.span_match_notes).__name__}"
        
        # Validate required int fields
        for field_name in ["start_year", "end_year", "weight"]:
            value = getattr(self, field_name)
            if not isinstance(value, int):
                return False, f"Field '{field_name}' must be int, got {type(value).__name__}"
        
        # Validate required bool fields
        for field_name in ["is_bc_start", "is_bc_end"]:
            value = getattr(self, field_name)
            if not isinstance(value, bool):
                return False, f"Field '{field_name}' must be bool, got {type(value).__name__}"
        
        # Validate required float field (allow int as well since it's numeric)
        if not isinstance(self.precision, (float, int)):
            return False, f"Field 'precision' must be float, got {type(self.precision).__name__}"
        
        # Validate optional fields if present
        if self.description is not None and not isinstance(self.description, str):
            return False, f"Field 'description' must be str or None, got {type(self.description).__name__}"
        
        for field_name in ["start_month", "start_day", "end_month", "end_day"]:
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, int):
                return False, f"Field '{field_name}' must be int or None, got {type(value).__name__}"
        
        if self.category is not None and not isinstance(self.category, str):
            return False, f"Field 'category' must be str or None, got {type(self.category).__name__}"
        
        if self._debug_extraction is not None and not isinstance(self._debug_extraction, dict):
            return False, f"Field '_debug_extraction' must be dict or None, got {type(self._debug_extraction).__name__}"
        
        # Validate date ranges
        if self.start_month is not None and not (1 <= self.start_month <= 12):
            return False, f"Field 'start_month' must be between 1 and 12, got {self.start_month}"
        
        if self.start_day is not None and not (1 <= self.start_day <= 31):
            return False, f"Field 'start_day' must be between 1 and 31, got {self.start_day}"
        
        if self.end_month is not None and not (1 <= self.end_month <= 12):
            return False, f"Field 'end_month' must be between 1 and 12, got {self.end_month}"
        
        if self.end_day is not None and not (1 <= self.end_day <= 31):
            return False, f"Field 'end_day' must be between 1 and 31, got {self.end_day}"
        
        return True, ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert this HistoricalEvent to a dictionary for JSON serialization.
        
        Returns:
            Dictionary representation suitable for JSON serialization.
            Ensures all fields conform to schema constraints.
        """
        data = asdict(self)
        
        # Ensure category is never None (schema requires it to be string)
        if data.get("category") is None:
            data["category"] = "Uncategorized"

        # Ensure description is a string (schema requires string, not null)
        if data.get("description") is None:
            data["description"] = ""

        # historical_events.title is VARCHAR(500) in database schema
        # Keep artifacts upload-safe by enforcing this limit at serialization time
        if isinstance(data.get("title"), str):
            data["title"] = data["title"].strip()[:500]
        
        # _debug_extraction should be string or null per schema, not a dict
        # If it's a dict, convert to JSON string or set to None
        if isinstance(data.get("_debug_extraction"), dict):
            import json
            data["_debug_extraction"] = json.dumps(data["_debug_extraction"])
        
        # Precision must be <= 100 per schema, cap if needed
        if isinstance(data.get("precision"), (int, float)):
            data["precision"] = min(float(data["precision"]), 100.0)
        
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoricalEvent":
        """Create a HistoricalEvent from a dictionary.
        
        Args:
            data: Dictionary with event data conforming to the HistoricalEvent schema.
            
        Returns:
            HistoricalEvent instance.
            
        Raises:
            ValueError: If the dictionary data is invalid.
        """
        # Extract only the fields that HistoricalEvent expects
        valid_fields = {
            "title", "start_year", "end_year", "is_bc_start", "is_bc_end",
            "precision", "weight", "url", "span_match_notes", "description", "start_month",
            "start_day", "end_month", "end_day", "category", "_debug_extraction"
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    @classmethod
    def from_span_dict(
        cls,
        title: str,
        description: str,
        url: str,
        span_dict: dict,
        span_match_notes: str,
        category: str | None = None,
        pageid: int | None = None,
        debug_info: dict | None = None
    ) -> "HistoricalEvent":
        """Create HistoricalEvent from a span dictionary.
        
        This helper extracts date fields from nested span objects (as used by
        the span parsing framework) and flattens them to the HistoricalEvent structure.
        
        Args:
            title: Event title
            description: Event description
            url: Source URL
            span_dict: Dictionary with date fields from span parser
            span_match_notes: Notes about how the span was matched/parsed
            category: Optional category
            pageid: Optional Wikipedia page ID (currently unused in schema, for future use)
            debug_info: Optional debug metadata
            
        Returns:
            HistoricalEvent with flattened date fields
        """
        return cls(
            title=title,
            description=description or "",
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
            span_match_notes=span_match_notes,
            category=category,
            _debug_extraction=debug_info
        )
