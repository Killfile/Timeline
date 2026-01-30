"""Timeline of Roman History ingestion strategy.

This module implements the IngestionStrategy interface for extracting historical events
from the Wikipedia "Timeline of Roman History" article. The article uses tables with
year and date columns that require special rowspan handling.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from bs4 import BeautifulSoup, Tag

from ingestion_common import get_html, log_info, log_error
from strategies.strategy_base import (
    IngestionStrategy,
    FetchResult,
    ParseResult,
    ArtifactData,
)
from span_parsing.table_row_date_parser import TableRowDateParser, RowspanContext
from span_parsing.roman_event import RomanEvent


logger = logging.getLogger(__name__)


class TimelineOfRomanHistoryStrategy(IngestionStrategy):
    """Ingestion strategy for Wikipedia Timeline of Roman History article.
    
    Implements the three-phase ingestion process:
    1. Fetch: HTTP GET Wikipedia article with caching
    2. Parse: Extract events from tables using TableRowDateParser
    3. Generate artifacts: Create JSON artifact file with all events
    """
    
    WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
    CACHE_FILENAME = "timeline_of_roman_history.html"
    STRATEGY_NAME = "TimelineOfRomanHistory"
    
    def __init__(self, run_id: str, output_dir: Path):
        """Initialize the Timeline of Roman History strategy.
        
        Args:
            run_id: Unique identifier for this ingestion run
            output_dir: Directory for writing artifacts and logs
        """
        super().__init__(run_id, output_dir)
        
        self.date_parser = TableRowDateParser()
        
        # Storage for parsed data
        self.html_content: Optional[str] = None
        self.canonical_url: Optional[str] = None
        self.roman_events: list[RomanEvent] = []
        self.parse_errors: list[dict] = []
        self.skipped_rows: int = 0
    
    @staticmethod
    def _extract_text(element: Tag) -> str:
        """Extract text from a BeautifulSoup element with proper spacing.
        
        Uses get_text(separator=' ') to ensure spaces are added between
        nested HTML elements (e.g., <br/>, <b>, <i>), preventing text
        from being concatenated without spaces.
        
        Args:
            element: BeautifulSoup Tag to extract text from
        
        Returns:
            Normalized text with proper spacing between elements
        """
        # Use separator to add spaces between text nodes, then normalize multiple spaces
        text = element.get_text(separator=' ', strip=True)
        # Collapse multiple whitespace into single spaces
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def name(self) -> str:
        """Return the strategy name for logging and artifact naming."""
        return "timeline_of_roman_history"
    
    def fetch(self) -> FetchResult:
        """Fetch the Wikipedia article HTML using shared cache framework.
        
        Uses ingestion_common.get_html() for consistent HTTP caching,
        retry logic, and content validation across all strategies.
        
        Returns:
            FetchResult with metadata about the fetch operation
        
        Raises:
            RuntimeError: If fetch fails
        """
        log_info(f"Fetching Timeline of Roman History from {self.WIKIPEDIA_URL}")
        
        (html, final_url), error = get_html(
            self.WIKIPEDIA_URL, 
            context="timeline_of_roman_history"
        )
        
        if error or not html.strip():
            log_error(f"Failed to fetch Timeline of Roman History: {error}")
            raise RuntimeError(f"Failed to fetch article: {error}")
        
        self.html_content = html
        self.canonical_url = final_url
        
        return FetchResult(
            strategy_name=self.STRATEGY_NAME,
            fetch_count=1,
            fetch_metadata={
                "url": self.WIKIPEDIA_URL,
                "final_url": final_url,
                "content_length_bytes": len(self.html_content),
                "fetch_timestamp_utc": datetime.utcnow().isoformat() + "Z",
            }
        )
    
    def parse(self, fetch_result: FetchResult) -> ParseResult:
        """Parse the fetched HTML to extract events from tables.
        
        The Timeline of Roman History article uses tables with:
        - Year column (may have rowspan)
        - Date column (month/day or empty)
        - Event column (description)
        
        Args:
            fetch_result: Result from fetch() phase
        
        Returns:
            ParseResult with extracted events and metadata
        """
        if not self.html_content:
            raise RuntimeError("No HTML content available. Call fetch() first.")
        
        log_info("Parsing Timeline of Roman History article")
        parse_start = datetime.utcnow()
        
        soup = BeautifulSoup(self.html_content, 'html.parser')
        
        # Find all tables in the article
        tables = soup.find_all('table', class_='wikitable')
        log_info(f"Found {len(tables)} tables to parse")
        
        total_rows_processed = 0
        
        for table_idx, table in enumerate(tables):
            log_info(f"Processing table {table_idx + 1}/{len(tables)}")
            rows_in_table = self._parse_table(table, table_idx)
            total_rows_processed += rows_in_table
        
        parse_end = datetime.utcnow()
        elapsed = (parse_end - parse_start).total_seconds()
        
        # Convert RomanEvents to HistoricalEvents
        historical_events = [
            event.to_historical_event(
                url=self.canonical_url or self.WIKIPEDIA_URL,
                span_match_notes=event.original_text or ""
            )
            for event in self.roman_events
        ]
        
        # Calculate confidence distribution
        confidence_dist = self._calculate_confidence_distribution()
        
        log_info(
            f"[{self.name()}] Parsed {len(historical_events)} events "
            f"from {total_rows_processed} rows in {elapsed:.2f}s"
        )
        log_info(f"[{self.name()}] Skipped {self.skipped_rows} malformed rows")
        
        return ParseResult(
            strategy_name=self.STRATEGY_NAME,
            events=historical_events,
            parse_metadata={
                "parse_duration_seconds": elapsed,
                "total_tables": len(tables),
                "total_rows_processed": total_rows_processed,
                "events_extracted": len(historical_events),
                "skipped_rows": self.skipped_rows,
                "parse_errors": self.parse_errors,
                "confidence_distribution": confidence_dist,
            }
        )
    
    def _parse_table(self, table: Tag, table_idx: int) -> int:
        """Parse a single table to extract events.
        
        Args:
            table: BeautifulSoup table element
            table_idx: Index of the table for logging
        
        Returns:
            Number of rows processed
        """
        rows = table.find_all('tr')
        # Initialize rowspan context with no inheritance initially
        rowspan_context = RowspanContext(
            inherited_year=0,
            inherited_is_bc=False,
            remaining_rows=0,
            source_row_index=-1
        )
        rows_processed = 0
        
        for row_idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            
            # Skip header rows
            if not cells or all(cell.name == 'th' for cell in cells):
                continue
            
            # Determine if we need to handle rowspan inheritance
            # Check if first cell is actually present or inherited via rowspan
            has_year_cell = len(cells) >= 1 and cells[0].name == 'td'
            
            # If we're inheriting from a rowspan and there's no year cell, the date is in cells[0]
            if rowspan_context.should_inherit() and (len(cells) < 3 or not has_year_cell):
                # This row is part of a rowspan - use inherited year
                year_text = str(rowspan_context.inherited_year)
                if rowspan_context.inherited_is_bc:
                    year_text = f"{rowspan_context.inherited_year} BC"
                date_text = self._extract_text(cells[0]) if len(cells) > 0 else ""
                event_text = " ".join(
                    self._extract_text(cell) for cell in cells[1:]
                ).strip()
                log_info(
                    f"Inherited year {year_text} for row {row_idx} in table {table_idx}"
                )
                rowspan_context.consume_row()
            elif len(cells) < 2:
                log_info(
                    f"Skipping row {row_idx} in table {table_idx}: "
                    f"only {len(cells)} columns"
                )
                self.skipped_rows += 1
                continue
            else:
                # Normal row with year and date cells
                year_text = self._extract_text(cells[0])
                date_text = self._extract_text(cells[1]) if len(cells) > 1 else ""
                event_text = " ".join(
                    self._extract_text(cell) for cell in cells[2:]
                ).strip()
                
                # Check if year cell has rowspan attribute
                if cells[0].get('rowspan'):
                    try:
                        rowspan_count = int(cells[0].get('rowspan'))
                        # Parse the year to get the actual value
                        temp_parsed = self.date_parser.parse_year_cell(year_text)
                        # Update rowspan context for subsequent rows
                        rowspan_context = RowspanContext(
                            inherited_year=abs(temp_parsed.year),
                            inherited_is_bc=temp_parsed.is_bc,
                            remaining_rows=rowspan_count - 1,  # -1 because current row is included in count
                            source_row_index=row_idx
                        )
                    except (ValueError, TypeError) as e:
                        log_error(f"Invalid rowspan value: {e}")
            
            try:
                # Parse the row using TableRowDateParser
                parsed_date = self.date_parser.parse_row_pair(
                    year_text=year_text,
                    date_text=date_text,
                )
                
                if not event_text:
                    log_info(
                        f"Skipping row {row_idx} in table {table_idx}: "
                        "no event description"
                    )
                    self.skipped_rows += 1
                    continue
                
                # Create RomanEvent
                roman_event = RomanEvent(
                    title=event_text[:100],  # Truncate title
                    description=event_text,
                    year=parsed_date.year,
                    is_bc=parsed_date.is_bc,
                    month=parsed_date.month,
                    day=parsed_date.day,
                    confidence=parsed_date.confidence,
                    precision=parsed_date.precision,
                    original_text=event_text,
                    category=None,  # Will be enriched later if needed
                )
                
                self.roman_events.append(roman_event)
                rows_processed += 1
                
            except Exception as e:
                error_msg = f"Error parsing row {row_idx} in table {table_idx}: {str(e)}"
                log_error(error_msg)
                self.parse_errors.append({
                    "table_idx": table_idx,
                    "row_idx": row_idx,
                    "error": str(e),
                    "cell_count": len(cells),
                })
                self.skipped_rows += 1
                continue
        
        return rows_processed
    
    def _calculate_confidence_distribution(self) -> dict:
        """Calculate distribution of confidence levels across events.
        
        Returns:
            Dictionary with confidence level counts
        """
        from collections import Counter
        confidence_counts = Counter(event.confidence.value for event in self.roman_events)
        return dict(confidence_counts)
    
    def generate_artifacts(self, parse_result: ParseResult) -> ArtifactData:
        """Generate JSON artifact file with all events.
        
        Args:
            parse_result: Result from parse() phase
        
        Returns:
            ArtifactData with events and metadata
        """
        log_info("Generating artifacts")
        
        artifact_data = ArtifactData(
            strategy_name=self.STRATEGY_NAME,
            run_id=self.run_id,
            generated_at_utc=datetime.utcnow().isoformat() + "Z",
            event_count=len(parse_result.events),
            events=parse_result.events,
            metadata=parse_result.parse_metadata,
            suggested_filename=f"timeline_of_roman_history_{self.run_id}.json"
        )
        
        log_info(f"Generated artifact with {artifact_data.event_count} events")
        return artifact_data
    
    def cleanup_logs(self) -> None:
        """Generate strategy-specific log files.
        
        Creates additional diagnostic logs for debugging and analysis.
        """
        log_info(f"[{self.name()}] Cleanup complete")
        
        # Write parse errors log if there were any errors
        if self.parse_errors:
            errors_file = self.output_dir / f"parse_errors_{self.run_id}.json"
            import json
            with open(errors_file, 'w') as f:
                json.dump({
                    "strategy": self.STRATEGY_NAME,
                    "run_id": self.run_id,
                    "total_errors": len(self.parse_errors),
                    "errors": self.parse_errors
                }, f, indent=2)
            log_info(f"Wrote parse errors to {errors_file}")
