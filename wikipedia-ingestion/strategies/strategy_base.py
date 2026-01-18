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
from historical_event import HistoricalEvent


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

    def to_dict(self) -> dict:
        """Convert ArtifactData to a serializable dictionary."""
        return {
            "strategy": self.strategy_name,
            "run_id": self.run_id,
            "generated_at_utc": self.generated_at_utc,
            "event_count": self.event_count,
            "metadata": self.metadata,
            "events": [event.to_dict() for event in self.events],
        }

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
