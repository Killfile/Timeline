"""Bespoke events ingestion strategy.

This strategy loads hard-coded events from a JSON file, allowing manual
curation of specific events to add to the timeline. This is useful for:
- Events not well-covered by Wikipedia's List of years
- Custom milestone events
- Testing and demonstration data
- Correcting or supplementing automated extraction

The strategy looks for a file named 'bespoke_events.json' in the same
directory as this module. If the file doesn't exist, it will create a
template file with example events.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

# Support both module and script imports
try:
    from .ingestion_common import log_error, log_info
    from .strategy_base import (
        ArtifactResult,
        FetchResult,
        IngestionStrategy,
        ParseResult,
        validate_event_dict,
    )
except ImportError:  # pragma: no cover
    from ingestion_common import log_error, log_info
    from strategy_base import (
        ArtifactResult,
        FetchResult,
        IngestionStrategy,
        ParseResult,
        validate_event_dict,
    )


# Template with example bespoke events
TEMPLATE_EVENTS = [
    {
        "title": "Example: First human on Mars",
        "description": "Hypothetical future event for demonstration purposes",
        "start_year": 2035,
        "start_month": 7,
        "start_day": 20,
        "end_year": 2035,
        "end_month": 7,
        "end_day": 20,
        "is_bc_start": False,
        "is_bc_end": False,
        "precision": "day",
        "weight": 1,
        "category": "Space Exploration",
        "url": None,
    },
    {
        "title": "Example: Signing of the Magna Carta",
        "description": "Charter of rights agreed to by King John of England",
        "start_year": 1215,
        "start_month": 6,
        "start_day": 15,
        "end_year": 1215,
        "end_month": 6,
        "end_day": 15,
        "is_bc_start": False,
        "is_bc_end": False,
        "precision": "day",
        "weight": 1,
        "category": "Legal History",
        "url": "https://en.wikipedia.org/wiki/Magna_Carta",
    },
]


class BespokeEventsStrategy(IngestionStrategy):
    """Ingestion strategy for manually curated events.
    
    Loads events from a JSON file named 'bespoke_events.json' in the
    wikipedia-ingestion directory.
    """
    
    def __init__(self, run_id: str, output_dir: Path):
        """Initialize strategy.
        
        Args:
            run_id: Unique identifier for this ingestion run
            output_dir: Directory for artifacts and logs
        """
        super().__init__(run_id, output_dir)
        
        # Path to bespoke events file (in same directory as this module)
        module_dir = Path(__file__).parent
        self.bespoke_file = module_dir / "bespoke_events.json"
        
        # Track state
        self.loaded_events: list[dict] = []
    
    def name(self) -> str:
        """Return strategy name."""
        return "bespoke_events"
    
    def _ensure_bespoke_file_exists(self) -> None:
        """Create template bespoke_events.json if it doesn't exist."""
        if not self.bespoke_file.exists():
            log_info(
                f"[{self.name()}] Bespoke events file not found, "
                f"creating template: {self.bespoke_file}"
            )
            template_data = {
                "description": (
                    "This file contains manually curated events to add to the timeline. "
                    "Add your own events here following the schema below. "
                    "Delete or modify the example events as needed."
                ),
                "schema": {
                    "title": "string (required)",
                    "description": "string or null",
                    "start_year": "integer (required)",
                    "start_month": "integer 1-12 or null",
                    "start_day": "integer 1-31 or null",
                    "end_year": "integer (required)",
                    "end_month": "integer 1-12 or null",
                    "end_day": "integer 1-31 or null",
                    "is_bc_start": "boolean (required)",
                    "is_bc_end": "boolean (required)",
                    "precision": "string: 'year', 'month', 'day', 'decade', or 'century' (required)",
                    "weight": "integer (days) or null - used for display priority",
                    "category": "string or null",
                    "url": "string or null",
                },
                "events": TEMPLATE_EVENTS
            }
            
            try:
                with open(self.bespoke_file, "w", encoding="utf-8") as f:
                    json.dump(template_data, f, indent=2, ensure_ascii=False)
                    f.write("\n")
                log_info(f"[{self.name()}] Created template file with example events")
            except Exception as e:
                log_error(f"[{self.name()}] Failed to create template file: {e}")
                raise
    
    def fetch(self) -> FetchResult:
        """Load events from bespoke_events.json file.
        
        Returns:
            FetchResult with loaded event count.
        """
        log_info(f"[{self.name()}] Starting fetch phase...")
        
        # Ensure file exists (create template if needed)
        self._ensure_bespoke_file_exists()
        
        # Load events from file
        try:
            with open(self.bespoke_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Extract events array
            if isinstance(data, dict) and "events" in data:
                self.loaded_events = data["events"]
            elif isinstance(data, list):
                # Support simple array format too
                self.loaded_events = data
            else:
                log_error(
                    f"[{self.name()}] Invalid file format: "
                    f"expected dict with 'events' key or array"
                )
                self.loaded_events = []
            
            log_info(
                f"[{self.name()}] Loaded {len(self.loaded_events)} events "
                f"from {self.bespoke_file}"
            )
            
        except FileNotFoundError:
            log_error(f"[{self.name()}] File not found: {self.bespoke_file}")
            self.loaded_events = []
        except json.JSONDecodeError as e:
            log_error(f"[{self.name()}] Invalid JSON in {self.bespoke_file}: {e}")
            self.loaded_events = []
        except Exception as e:
            log_error(f"[{self.name()}] Error loading bespoke events: {e}")
            self.loaded_events = []
        
        return FetchResult(
            strategy_name=self.name(),
            fetch_count=len(self.loaded_events),
            fetch_metadata={
                "source_file": str(self.bespoke_file),
                "file_exists": self.bespoke_file.exists()
            }
        )
    
    def parse(self, fetch_result: FetchResult) -> ParseResult:
        """Validate and prepare loaded events.
        
        Args:
            fetch_result: Result from fetch phase.
            
        Returns:
            ParseResult with validated events.
        """
        log_info(f"[{self.name()}] Starting parse phase...")
        
        valid_events = []
        invalid_count = 0
        
        for i, event in enumerate(self.loaded_events):
            # Validate event schema
            is_valid, error_msg = validate_event_dict(event)
            
            if not is_valid:
                log_error(
                    f"[{self.name()}] Invalid event at index {i}: {error_msg}. "
                    f"Event: {event.get('title', '(no title)')}"
                )
                invalid_count += 1
                continue
            
            # Add debug metadata
            if "_debug_extraction" not in event:
                event["_debug_extraction"] = {
                    "method": "bespoke_events",
                    "source": "manual_curation",
                    "file": str(self.bespoke_file),
                    "index": i
                }
            
            valid_events.append(event)
        
        log_info(
            f"[{self.name()}] Validated {len(valid_events)} events "
            f"({invalid_count} invalid)"
        )
        
        return ParseResult(
            strategy_name=self.name(),
            events=valid_events,
            parse_metadata={
                "total_loaded": len(self.loaded_events),
                "valid_count": len(valid_events),
                "invalid_count": invalid_count
            }
        )
    
    def generate_artifacts(self, parse_result: ParseResult) -> ArtifactResult:
        """Generate JSON artifact from validated events.
        
        Args:
            parse_result: Result from parse phase.
            
        Returns:
            ArtifactResult with artifact path.
        """
        log_info(f"[{self.name()}] Generating artifacts...")
        
        artifact_path = self.output_dir / f"events_{self.name()}_{self.run_id}.json"
        
        artifact_data = {
            "strategy": self.name(),
            "run_id": self.run_id,
            "generated_at_utc": datetime.utcnow().isoformat() + "Z",
            "event_count": len(parse_result.events),
            "metadata": parse_result.parse_metadata,
            "events": parse_result.events
        }
        
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(artifact_data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        
        log_info(f"[{self.name()}] Wrote artifact: {artifact_path}")
        
        return ArtifactResult(
            strategy_name=self.name(),
            artifact_path=artifact_path,
            log_paths=[]
        )
    
    def cleanup_logs(self) -> None:
        """Generate strategy-specific log files.
        
        For bespoke events, we don't have additional diagnostics to log.
        """
        log_info(f"[{self.name()}] No additional logs to generate")
