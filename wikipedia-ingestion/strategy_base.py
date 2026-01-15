"""Base class and interfaces for ingestion strategies.

This module defines the abstract base class that all ingestion strategies must implement.
Each strategy is responsible for:
1. Fetching data from its source (HTTP, API, files, etc)
2. Parsing and extracting structured events
3. Generating JSON artifact files
4. Producing strategy-specific logs and diagnostics

The orchestrator will call these phases sequentially and then perform consolidated
database insertion using the generated artifacts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
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
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistoricalEvent:
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
    ) -> HistoricalEvent:
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


@dataclass
class FetchResult:
    """Result of the fetch phase.
    
    Contains metadata about what was fetched and any intermediate data
    needed for the parse phase.
    """
    strategy_name: str
    fetch_count: int  # Number of pages/items fetched
    fetch_metadata: dict[str, Any] = field(default_factory=dict)  # Strategy-specific metadata
    

@dataclass
class ParseResult:
    """Result of the parse phase.
    
    Contains extracted events and metadata about parsing.
    """
    strategy_name: str
    events: list[HistoricalEvent]  # Structured event instances
    parse_metadata: dict[str, Any] = field(default_factory=dict)  # Strategy-specific metadata


@dataclass
class ArtifactData:
    """Artifact data to be written to disk.
    
    This is the strongly-typed data that strategies return from generate_artifacts().
    The orchestrator is responsible for serializing this to JSON and writing to disk.
    """
    strategy_name: str
    run_id: str
    generated_at_utc: str  # ISO 8601 timestamp
    event_count: int
    events: list[HistoricalEvent]  # List of HistoricalEvent instances
    metadata: dict[str, Any] = field(default_factory=dict)  # Strategy-specific metadata
    suggested_filename: str | None = None  # Optional filename suggestion (e.g., "events_list_of_years_20240115.json")


@dataclass
class ArtifactResult:
    """Result of the artifact generation phase.
    
    Contains paths to generated files.
    """
    strategy_name: str
    artifact_path: Path  # Primary JSON artifact
    log_paths: list[Path] = field(default_factory=list)  # Additional log files


class IngestionStrategy(ABC):
    """Abstract base class for ingestion strategies.
    
    Each strategy must implement all abstract methods. The orchestrator will
    call these methods in sequence:
    1. fetch() - Retrieve data from source
    2. parse(fetch_result) - Extract structured events
    3. generate_artifacts(parse_result) - Write JSON files
    4. cleanup_logs() - Generate diagnostic logs
    
    Strategies should be self-contained and not depend on other strategies.
    Strategies should not perform database operations (that's the orchestrator's job).
    """
    
    def __init__(self, run_id: str, output_dir: Path):
        """Initialize strategy with run context.
        
        Args:
            run_id: Unique identifier for this ingestion run (e.g., "20240115T120000Z")
            output_dir: Directory for writing artifacts and logs
        """
        self.run_id = run_id
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    @abstractmethod
    def name(self) -> str:
        """Return the strategy name for logging and artifact naming.
        
        Should be lowercase, underscored (e.g., "list_of_years", "by_category").
        """
        pass
    
    @abstractmethod
    def fetch(self) -> FetchResult:
        """Fetch data from the strategy's source.
        
        This phase performs all HTTP/API operations, page discovery, and HTML fetching.
        Should be idempotent where possible.
        
        Returns:
            FetchResult with metadata and any intermediate data needed for parsing.
            
        Raises:
            Exception on unrecoverable fetch errors.
        """
        pass
    
    @abstractmethod
    def parse(self, fetch_result: FetchResult) -> ParseResult:
        """Parse fetched data and extract structured events.
        
        This phase performs HTML parsing, event extraction, date parsing, etc.
        Should not perform any IO except logging.
        
        Args:
            fetch_result: Output from the fetch() phase.
            
        Returns:
            ParseResult containing list of HistoricalEvent instances.
            
        Each HistoricalEvent must have these fields:
            title: str              # Required: event title
            start_year: int         # Required: start year (positive for AD, positive for BC)
            end_year: int           # Required: end year
            is_bc_start: bool       # Required: True if start is BC
            is_bc_end: bool         # Required: True if end is BC
            precision: float        # Required: precision value (higher = more precise)
            weight: int             # Required: duration in days (for packing priority)
            url: str                # Required: source URL
            description: str | None # Optional: event description
            start_month: int | None # Optional: 1-12
            start_day: int | None   # Optional: 1-31
            end_month: int | None   # Optional: 1-12
            end_day: int | None     # Optional: 1-31
            category: str | None    # Optional: categorization
            _debug_extraction: dict | None  # Optional: extraction diagnostics
        """
        pass
    
    @abstractmethod
    def generate_artifacts(self, parse_result: ParseResult) -> ArtifactData:
        """Prepare artifact data for serialization.
        
        This phase prepares the standardized artifact data structure that will be
        serialized to JSON and written to disk by the orchestrator.
        
        Strategies should NOT perform file I/O in this method - they should return
        an ArtifactData object that the orchestrator will serialize and write.
        
        Args:
            parse_result: Output from the parse() phase.
            
        Returns:
            ArtifactData with events and metadata ready for serialization.
        """
        pass
    
    @abstractmethod
    def cleanup_logs(self) -> None:
        """Generate strategy-specific log files.
        
        This phase writes any additional diagnostic logs, exclusion reports,
        extraction statistics, etc. These are separate from the primary artifact
        and are for debugging/analysis purposes.
        
        Should not raise exceptions - log errors internally if needed.
        """
        pass


def validate_event_dict(event: dict) -> tuple[bool, str]:
    """Validate that an event dict conforms to the expected schema.
    
    Args:
        event: Event dictionary to validate.
        
    Returns:
        Tuple of (is_valid, error_message). error_message is empty string if valid.
    """
    required_fields = {
        "title": str,
        "start_year": int,
        "end_year": int,
        "is_bc_start": bool,
        "is_bc_end": bool,
        "precision": float,
        "weight": int,
        "url": str,
    }
    
    optional_fields = {
        "description": (str, type(None)),
        "start_month": (int, type(None)),
        "start_day": (int, type(None)),
        "end_month": (int, type(None)),
        "end_day": (int, type(None)),
        "category": (str, type(None)),
        "_debug_extraction": (dict, type(None)),
    }
    
    # Check required fields
    for field_name, field_type in required_fields.items():
        if field_name not in event:
            return False, f"Missing required field: {field_name}"
        if not isinstance(event[field_name], field_type):
            return False, f"Field {field_name} has wrong type: expected {field_type}, got {type(event[field_name])}"
    
    # Check optional fields if present
    for field_name, field_types in optional_fields.items():
        if field_name in event and event[field_name] is not None:
            if not isinstance(event[field_name], field_types):
                return False, f"Field {field_name} has wrong type: expected {field_types}, got {type(event[field_name])}"
    
    # Validate title is non-empty
    if not event["title"].strip():
        return False, "Field 'title' cannot be empty"
    
    return True, ""
