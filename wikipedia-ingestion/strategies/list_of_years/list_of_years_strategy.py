"""List of Years ingestion strategy implementation.

This strategy wraps the existing ingestion_list_of_years functionality
and adapts it to the new multi-strategy architecture.

Key changes from the original:
- Inherits from IngestionStrategy base class
- Separates fetch, parse, and artifact generation phases
- Generates JSON artifacts instead of inserting directly to DB
- Maintains all existing discovery, parsing, and extraction logic
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

# Support both module and script imports
try:
    from .ingestion_common import (
        LIST_OF_YEARS_URL,
        LOGS_DIR,
        RUN_ID,
        _get_html,
        log_error,
        log_info,
    )
    from .ingestion_list_of_years import (
        _discover_yearish_links_from_list_of_years,
        _extract_events_section_items_with_report,
        _infer_page_era_from_html,
        _merge_exclusions,
        _parse_scope_from_title,
        _parse_year,
        _process_event_item,
        _process_year_page,
        _should_include_page,
        _write_exclusions_report,
    )
    from span_parsing.orchestrators.years_parse_orchestrator import YearsParseOrchestrator
    from .span_parsing.span import SpanEncoder
    from .strategy_base import (
        ArtifactResult,
        FetchResult,
        IngestionStrategy,
        ParseResult,
    )
except ImportError:  # pragma: no cover
    from ingestion_common import (
        LIST_OF_YEARS_URL,
        LOGS_DIR,
        RUN_ID,
        _get_html,
        log_error,
        log_info,
    )
    from ingestion_list_of_years import (
        _discover_yearish_links_from_list_of_years,
        _extract_events_section_items_with_report,
        _infer_page_era_from_html,
        _merge_exclusions,
        _parse_scope_from_title,
        _parse_year,
        _process_event_item,
        _process_year_page,
        _should_include_page,
        _write_exclusions_report,
    )
    from span_parsing.orchestrators.years_parse_orchestrator import YearsParseOrchestrator
    from span_parsing.span import SpanEncoder
    from strategy_base import (
        ArtifactResult,
        FetchResult,
        IngestionStrategy,
        ParseResult,
    )


class ListOfYearsStrategy(IngestionStrategy):
    """Ingestion strategy for Wikipedia's List of years.
    
    Discovers year/decade/century pages from the List_of_years index,
    fetches each page, and extracts events from the "Events" section.
    """
    
    def __init__(self, run_id: str, output_dir: Path):
        """Initialize strategy.
        
        Args:
            run_id: Unique identifier for this ingestion run
            output_dir: Directory for artifacts and logs
        """
        super().__init__(run_id, output_dir)
        
        # Track state across phases
        self.pages: list[dict] = []
        self.exclusions_agg_counts: dict[str, int] = {}
        self.exclusions_agg_samples: dict[str, list[dict]] = {}
        self.visited_page_keys: set[tuple] = set()
    
    def name(self) -> str:
        """Return strategy name."""
        return "list_of_years"
    
    def fetch(self) -> FetchResult:
        """Fetch and discover year pages from Wikipedia's List of years.
        
        Returns:
            FetchResult with discovered pages and metadata.
        """
        log_info(f"[{self.name()}] Starting fetch phase...")
        
        # Load the List of years index page
        (index_pair, index_err) = _get_html(LIST_OF_YEARS_URL, context="list_of_years")
        index_html, _index_url = index_pair
        if index_err or not index_html.strip():
            log_error(f"Failed to load List_of_years page: {index_err}")
            return FetchResult(
                strategy_name=self.name(),
                fetch_count=0,
                fetch_metadata={"error": str(index_err)}
            )
        
        # Parse min/max year configuration
        min_year_str = os.getenv("WIKI_MIN_YEAR")
        max_year_str = os.getenv("WIKI_MAX_YEAR")
        min_year = _parse_year(min_year_str)
        max_year = _parse_year(max_year_str)
        
        # Discover year pages
        self.pages = _discover_yearish_links_from_list_of_years(
            index_html, limit=None, min_year=min_year, max_year=max_year
        )
        
        # Filter pages based on min/max year thresholds
        if min_year or max_year:
            self.pages = [
                p for p in self.pages
                if _should_include_page(
                    p.get("scope", {}).get("start_year", 0),
                    p.get("scope", {}).get("is_bc", False),
                    min_year,
                    max_year
                )
            ]
        
        min_desc = f"from {min_year_str}" if min_year_str else "from earliest"
        max_desc = f"to {max_year_str}" if max_year_str else "to latest"
        log_info(f"Discovered {len(self.pages)} year/decade pages ({min_desc} {max_desc})")
        
        return FetchResult(
            strategy_name=self.name(),
            fetch_count=len(self.pages),
            fetch_metadata={
                "min_year": min_year,
                "max_year": max_year,
                "index_url": LIST_OF_YEARS_URL
            }
        )
    
    def parse(self, fetch_result: FetchResult) -> ParseResult:
        """Parse discovered pages and extract events.
        
        Args:
            fetch_result: Result from fetch phase.
            
        Returns:
            ParseResult with extracted events.
        """
        log_info(f"[{self.name()}] Starting parse phase...")
        
        all_events = []
        seen_event_keys: set[tuple] = set()
        
        for page in self.pages:
            # Process the year page (this fetches HTML and extracts items)
            page_result = _process_year_page(
                page,
                self.visited_page_keys,
                self.exclusions_agg_counts,
                self.exclusions_agg_samples
            )
            
            if page_result is None:
                continue
            
            # Process each event item from this page
            for item in page_result.extracted_items:
                event = _process_event_item(
                    item,
                    page_result.scope,
                    page_result.scope_is_bc,
                    page_result.page_assume_is_bc,
                    page_result.canonical_url,
                    page_result.pageid,
                    page_result.title
                )
                
                if event is None:
                    continue
                
                # Deduplicate events within this strategy
                import re
                normalized_title = re.sub(r"\s+", " ", event["title"].strip().lower())
                event_key = (
                    normalized_title,
                    int(event["start_year"]),
                    int(event["end_year"]),
                    bool(event["is_bc_start"]),
                )
                
                if event_key in seen_event_keys:
                    continue
                seen_event_keys.add(event_key)
                
                all_events.append(event)
        
        log_info(f"[{self.name()}] Parsed {len(all_events)} events")
        
        return ParseResult(
            strategy_name=self.name(),
            events=all_events,
            parse_metadata={
                "pages_processed": len(self.visited_page_keys),
                "exclusions": self.exclusions_agg_counts
            }
        )
    

    def generate_artifacts(self, parse_result: ParseResult) -> ArtifactResult:
        """Generate JSON artifact from parsed events.
        
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
            json.dump(artifact_data, f, indent=2, ensure_ascii=False, cls=SpanEncoder)
            f.write("\n")
        
        log_info(f"[{self.name()}] Wrote artifact: {artifact_path}")
        
        return ArtifactResult(
            strategy_name=self.name(),
            artifact_path=artifact_path,
            log_paths=[]
        )
    
    def cleanup_logs(self) -> None:
        """Generate strategy-specific log files.
        
        Writes exclusion report to JSON file.
        """
        log_info(f"[{self.name()}] Generating logs...")
        
        try:
            _write_exclusions_report(
                self.exclusions_agg_counts,
                self.exclusions_agg_samples
            )
            log_info(f"[{self.name()}] Exclusions report generated")
        except Exception as e:
            log_error(f"[{self.name()}] Failed to generate exclusions report: {e}")
