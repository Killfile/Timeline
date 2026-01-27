"""Timeline of Food ingestion strategy.

This module implements the IngestionStrategy interface for extracting food history
events from the Wikipedia "Timeline of Food" article.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import requests
from bs4 import BeautifulSoup

from strategies.strategy_base import (
    IngestionStrategy,
    FetchResult,
    ParseResult,
    ArtifactData,
)
from historical_event import HistoricalEvent

from .food_event import FoodEvent
from .hierarchical_strategies import TextSectionParser, TextSection
from .date_extraction_strategies import EventParser


logger = logging.getLogger(__name__)


class TimelineOfFoodStrategy(IngestionStrategy):
    """Ingestion strategy for Wikipedia Timeline of Food article.
    
    Implements the three-phase ingestion process:
    1. Fetch: HTTP GET Wikipedia article with caching
    2. Parse: Extract sections and events using hierarchical parsing
    3. Generate artifacts: Create JSON artifact file with all events
    """
    
    WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/Timeline_of_food"
    CACHE_FILENAME = "timeline_of_food.html"
    STRATEGY_NAME = "TimelineOfFood"
    
    def __init__(self, run_id: str, output_dir: Path):
        """Initialize the Timeline of Food strategy.
        
        Args:
            run_id: Unique identifier for this ingestion run
            output_dir: Directory for writing artifacts and logs
        """
        super().__init__(run_id, output_dir)
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_path = self.cache_dir / self.CACHE_FILENAME
        
        self.section_parser = TextSectionParser()
        self.event_parser = EventParser()
        
        # Storage for parsed data
        self.html_content: Optional[str] = None
        self.sections: list[TextSection] = []
        self.events: list[FoodEvent] = []
    
    def name(self) -> str:
        """Return the strategy name for logging and artifact naming."""
        return "timeline_of_food"
    
    def fetch(self) -> FetchResult:
        """Fetch the Wikipedia article HTML.
        
        Downloads the article from Wikipedia with caching support.
        If cache file exists, loads from cache. Otherwise, makes HTTP request.
        
        Returns:
            FetchResult with metadata about the fetch operation
        
        Raises:
            requests.HTTPError: If HTTP request fails (404, 5xx, etc.)
            requests.Timeout: If request times out
            requests.RequestException: For other network errors
        """
        logger.info(f"Fetching Timeline of Food article from {self.WIKIPEDIA_URL}")
        
        # Check cache first
        if self.cache_path.exists():
            logger.info(f"Loading from cache: {self.cache_path}")
            self.html_content = self.cache_path.read_text(encoding='utf-8')
            
            return FetchResult(
                strategy_name=self.STRATEGY_NAME,
                fetch_count=1,
                fetch_metadata={
                    "url": self.WIKIPEDIA_URL,
                    "http_status": 200,
                    "cache_hit": True,
                    "cache_file": str(self.cache_path),
                    "content_length_bytes": len(self.html_content),
                    "fetch_timestamp_utc": datetime.utcnow().isoformat() + "Z",
                }
            )
        
        # Make HTTP request
        try:
            response = requests.get(
                self.WIKIPEDIA_URL,
                headers={"User-Agent": "Wikipedia Ingestion Bot"},
                timeout=10
            )
            response.raise_for_status()
            
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"Article not found: {self.WIKIPEDIA_URL}")
                raise RuntimeError(f"Wikipedia article not found (404): {self.WIKIPEDIA_URL}") from e
            else:
                logger.error(f"HTTP error fetching article: {e}")
                raise RuntimeError(f"HTTP error {e.response.status_code}: {e}") from e
        
        except requests.Timeout:
            logger.error(f"Request timed out: {self.WIKIPEDIA_URL}")
            raise RuntimeError(f"Request timed out after 10 seconds") from None
        
        except requests.RequestException as e:
            logger.error(f"Network error fetching article: {e}")
            raise RuntimeError(f"Network error: {e}") from e
        
        # Save to cache
        self.html_content = response.text
        self.cache_path.write_text(self.html_content, encoding='utf-8')
        logger.info(f"Saved to cache: {self.cache_path}")
        
        return FetchResult(
            strategy_name=self.STRATEGY_NAME,
            fetch_count=1,
            fetch_metadata={
                "url": self.WIKIPEDIA_URL,
                "http_status": response.status_code,
                "cache_hit": False,
                "cache_file": str(self.cache_path),
                "content_type": response.headers.get("Content-Type", ""),
                "content_length_bytes": len(self.html_content),
                "fetch_timestamp_utc": datetime.utcnow().isoformat() + "Z",
            }
        )
    
    def parse(self, fetch_result: FetchResult) -> ParseResult:
        """Parse the fetched HTML to extract events.
        
        Orchestrates the parsing process:
        1. Parse hierarchical sections
        2. For each section, extract bullet point events
        3. Parse dates from event text using orchestrator
        4. Create FoodEvent instances
        
        Args:
            fetch_result: Result from fetch() phase
        
        Returns:
            ParseResult with extracted events and metadata
        """
        if not self.html_content:
            raise RuntimeError("No HTML content available. Call fetch() first.")
        
        logger.info("Parsing Timeline of Food article")
        parse_start = datetime.utcnow()
        
        # Parse sections
        self.sections = self.section_parser.parse_sections(self.html_content)
        logger.info(f"Found {len(self.sections)} sections")
        
        # Extract events from each section
        soup = BeautifulSoup(self.html_content, 'html.parser')
        
        for section in self.sections:
            section_events = self._extract_events_from_section(soup, section)
            self.events.extend(section_events)
        
        parse_end = datetime.utcnow()
        elapsed = (parse_end - parse_start).total_seconds()
        
        # Convert to HistoricalEvent instances
        historical_events = [event.to_historical_event() for event in self.events]
        
        # Calculate confidence distribution
        confidence_dist = self._calculate_confidence_distribution()
        
        # Get undated event summary
        undated_summary = self.event_parser.get_undated_summary()
        
        logger.info(f"Parsed {len(historical_events)} events in {elapsed:.2f}s")
        logger.info(f"Undated events: {undated_summary['total_undated']}")
        
        return ParseResult(
            strategy_name=self.STRATEGY_NAME,
            events=historical_events,
            parse_metadata={
                "total_events_found": len(self.events) + undated_summary['total_undated'],
                "total_events_parsed": len(self.events),
                "sections_identified": len(self.sections),
                "parsing_start_utc": parse_start.isoformat() + "Z",
                "parsing_end_utc": parse_end.isoformat() + "Z",
                "elapsed_seconds": elapsed,
                "events_per_second": len(self.events) / elapsed if elapsed > 0 else 0,
                "confidence_distribution": confidence_dist,
                "undated_events": undated_summary,
            }
        )
    
    def _extract_events_from_section(self, soup: BeautifulSoup, section: TextSection) -> list[FoodEvent]:
        """Extract events from a specific section.
        
        Args:
            soup: BeautifulSoup parsed HTML
            section: TextSection to extract events from
        
        Returns:
            List of FoodEvent instances
        """
        events = []
        
        # Find the h2 header with this section name (convert spaces to underscores for id)
        section_id = section.name.replace(' ', '_').replace('–', '-')
        header = soup.find('h2', id=section_id)
        
        if not header:
            # Try alternative: find by text content
            all_h2s = soup.find_all('h2')
            for h2 in all_h2s:
                if h2.get_text(strip=True) == section.name:
                    header = h2
                    break
        
        if not header:
            logger.warning(f"Could not find header for section: {section.name}")
            return events
        
        # Get the parent div (mw-heading) and then find siblings
        header_container = header.parent
        if header_container and header_container.name == 'div':
            siblings_to_search = header_container.find_next_siblings()
        else:
            siblings_to_search = header.find_next_siblings()
        
        # Find all bullet points and tables following this header
        for sibling in siblings_to_search:
            # Stop at next header container
            if sibling.name == 'div' and 'mw-heading' in sibling.get('class', []):
                break
            
            # Process list items (bullet points)
            if sibling.name == 'ul':
                for li in sibling.find_all('li', recursive=False):
                    bullet_html = str(li)
                    bullet_text = li.get_text(strip=True)
                    
                    result = self.event_parser.parse_bullet_point(
                        bullet_html,
                        section,
                        source_format="bullet"
                    )
                    
                    if result.event:
                        events.append(result.event)
            
            # Process table rows (19th-20th centuries use tables)
            elif sibling.name == 'table':
                table_events = self._extract_events_from_table(sibling, section)
                events.extend(table_events)
        
        return events
    
    def _extract_events_from_table(self, table: BeautifulSoup, section: TextSection) -> list[FoodEvent]:
        """Extract events from a Wikipedia table.
        
        Wikipedia tables for Timeline of Food typically have:
        - First column: Year/date
        - Second column: Event description
        
        Tries to parse date from first column and use it; falls back to description
        parsing if necessary.
        
        Args:
            table: BeautifulSoup table element
            section: TextSection context for this table
        
        Returns:
            List of FoodEvent instances
        """
        events = []
        rows = table.find_all('tr')
        
        # Skip header row if present
        start_idx = 1 if rows and rows[0].find('th') else 0
        
        for row in rows[start_idx:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue
            
            # Extract year/date from first cell
            year_cell = cells[0].get_text(strip=True)
            
            # Extract description from second cell
            description_cell = cells[1]
            description_html = str(description_cell)
            description_text = description_cell.get_text(strip=True)
            
            if not description_text:
                continue
            
            # Try to parse the date from the first column
            # If successful, use that date; otherwise fall back to description parsing
            table_span = None
            if year_cell:
                table_span = self.event_parser.orchestrator.parse_span_from_bullet(
                    year_cell,
                    span_year=section.date_range_start if section.date_range_start > 0 else 2000,
                    assume_is_bc=section.is_bc_start
                )
            
            # If we have a table date, use it with the description
            # Otherwise let parse_bullet_point try to extract date from description
            if table_span:
                # Create event using table date + description
                event = self._create_table_event(
                    table_span, 
                    description_text,
                    section,
                    year_cell
                )
                if event:
                    events.append(event)
            else:
                # Fall back to description-based parsing
                result = self.event_parser.parse_bullet_point(
                    description_html,
                    section,
                    source_format="table"
                )
                
                if result.event:
                    events.append(result.event)
        
        return events
    
    def _create_table_event(
        self,
        table_span: object,
        description_text: str,
        section: TextSection,
        year_cell_text: str
    ) -> FoodEvent | None:
        """Create a FoodEvent from a table row using extracted date span.
        
        Args:
            table_span: Span object from date parsing
            description_text: Event description from second column
            section: Section context
            year_cell_text: Original year cell text for match notes
        
        Returns:
            FoodEvent instance or None if creation fails
        """
        try:
            # Check if span is valid
            if not hasattr(table_span, 'start_year') or table_span.start_year is None:
                return None
            
            # Determine if date is approximate (circa, ~, etc.)
            is_circa = (
                table_span.match_type and 
                "CIRCA" in table_span.match_type.upper() 
                if table_span.match_type else False
            )
            
            # Determine confidence level
            if is_circa:
                confidence = "approximate"
            elif table_span.start_year == table_span.end_year:
                confidence = "explicit"
            else:
                confidence = "explicit"
            
            # Create the event
            event = FoodEvent(
                event_key="",  # Will be generated in __post_init__
                date_explicit=table_span.start_year if table_span.start_year == table_span.end_year else None,
                date_range_start=table_span.start_year,
                date_range_end=table_span.end_year,
                is_bc_start=table_span.start_year_is_bc,
                is_bc_end=table_span.end_year_is_bc,
                confidence_level=confidence,
                title="",  # Will be generated from description
                description=description_text,
                food_category="Food History",
                section_name=section.name,
                section_date_range_start=section.date_range_start,
                section_date_range_end=section.date_range_end,
                wikipedia_links=[],
                external_references=[],
                source_format="table",
                parsing_notes=f"Table row date extracted from first column: {year_cell_text}",
                span_match_notes=table_span.match_type if table_span.match_type else "Table column date",
                precision=self.event_parser._calculate_precision(table_span),
            )
            
            return event
        except Exception as e:
            logger.warning(f"Failed to create table event: {e}")
            return None
    
    def _calculate_confidence_distribution(self) -> dict:
        """Calculate distribution of confidence levels across events.
        
        Returns:
            Dictionary mapping confidence levels to counts
        """
        distribution = {
            "explicit": 0,
            "inferred": 0,
            "approximate": 0,
            "contentious": 0,
            "fallback": 0,
        }
        
        for event in self.events:
            confidence = event.confidence_level
            if confidence in distribution:
                distribution[confidence] += 1
        
        return distribution
    
    def generate_artifacts(self, parse_result: ParseResult) -> ArtifactData:
        """Generate JSON artifact file with all events.
        
        Args:
            parse_result: Result from parse() phase
        
        Returns:
            ArtifactData with events and metadata
        """
        logger.info("Generating artifacts")
        
        artifact_data = ArtifactData(
            strategy_name=self.STRATEGY_NAME,
            run_id=self.run_id,
            generated_at_utc=datetime.utcnow().isoformat() + "Z",
            event_count=len(parse_result.events),
            events=parse_result.events,
            metadata=parse_result.parse_metadata,
            suggested_filename=f"timeline_of_food_{self.run_id}.json"
        )
        
        logger.info(f"Generated artifact with {artifact_data.event_count} events")
        return artifact_data
    
    def cleanup_logs(self) -> None:
        """Generate strategy-specific log files.
        
        For Timeline of Food, log undated event summary.
        """
        undated_summary = self.event_parser.get_undated_summary()
        if undated_summary['total_undated'] > 0:
            logger.info(f"Undated events summary: {undated_summary['total_undated']} events without parseable dates")
            for event_info in undated_summary['events'][:10]:  # Log first 10
                logger.info(f"  - {event_info['section']}: {event_info['text']}")
