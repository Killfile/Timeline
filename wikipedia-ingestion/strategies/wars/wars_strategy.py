"""Wars ingestion strategy.

This strategy discovers war period pages from Wikipedia's `Timeline_of_wars` page,
then extracts wars from tables on the linked period-specific pages.

The strategy follows this process:
1. Fetch the main "Timeline of wars" index page
2. Extract links to period-specific war list pages (before 1000, 1000-1499, etc.)
3. For each linked page, fetch and parse war tables
4. Extract structured war events from table rows

Table format expected:
| Start Year | End Year | War Name | Belligerents | Notes |
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Use absolute imports for IDE navigation support
from ingestion_common import (
    LOGS_DIR,
    RUN_ID,
    WIKIPEDIA_BASE,
    _canonicalize_wikipedia_url,
    _resolve_page_identity,
    get_html,
    log_error,
    log_info,
)
from strategies.strategy_base import (
    ArtifactData,
    FetchResult,
    IngestionStrategy,
    ParseResult,
)
from historical_event import HistoricalEvent
from span_parsing.span import SpanEncoder, SpanPrecision
from strategies.wars.war_row_parser_factory import WarRowParserFactory


# ===== Constants =====

# URL for the main Timeline of wars page
TIMELINE_OF_WARS_URL = "https://en.wikipedia.org/wiki/Timeline_of_wars"

_DASH_RE = re.compile(r"[\u2012\u2013\u2014\u2212-]")


# ===== Data Classes =====

@dataclass
class WarPeriodPage:
    """Metadata for a discovered war period page."""
    title: str
    url: str
    period_range: str  # e.g., "1900–1944"


from strategies.wars.war_event import WarEvent


@dataclass
class ProcessedWarPage:
    """Result of processing a single war period page."""
    wars: list[WarEvent]
    period_range: str
    canonical_url: str
    pageid: int | None
    title: str


# ===== Strategy Class =====

class WarsStrategy(IngestionStrategy):
    """Ingestion strategy for Wikipedia's Timeline of wars.

    Discovers period-specific war pages from the Timeline_of_wars index,
    fetches each page, and extracts wars from tables.
    """

    def __init__(self, run_id: str, output_dir: Path):
        """Initialize strategy.

        Args:
            run_id: Unique identifier for this ingestion run
            output_dir: Directory for artifacts and logs
        """
        super().__init__(run_id, output_dir)

        # Track state across phases
        self.period_pages: list[WarPeriodPage] = []
        self.visited_page_keys: set[tuple] = set()

        # Initialize row parser factory
        self.parser_factory = WarRowParserFactory()

    def name(self) -> str:
        """Return strategy name."""
        return "Wikipedia Wars"

    def fetch(self) -> FetchResult:
        """Fetch and discover war period pages from Wikipedia's Timeline of wars.

        Returns:
            FetchResult with discovered pages and metadata.
        """
        log_info(f"[{self.name()}] Starting fetch phase...")

        # Load the Timeline of wars index page
        (index_pair, index_err) = get_html(TIMELINE_OF_WARS_URL, context="timeline_of_wars")
        index_html, _index_url = index_pair
        if index_err or not index_html.strip():
            log_error(f"Failed to load Timeline_of_wars page: {index_err}")
            return FetchResult(
                strategy_name=self.name(),
                fetch_count=0,
                fetch_metadata={"error": str(index_err)}
            )

        # Discover war period pages
        self.period_pages = self._discover_war_period_links(index_html)

        log_info(f"Discovered {len(self.period_pages)} war period pages")

        return FetchResult(
            strategy_name=self.name(),
            fetch_count=len(self.period_pages),
            fetch_metadata={
                "index_url": TIMELINE_OF_WARS_URL
            }
        )

    def parse(self, fetch_result: FetchResult) -> ParseResult:
        """Parse discovered pages and extract wars.

        Args:
            fetch_result: Result from fetch phase.

        Returns:
            ParseResult with extracted events.
        """
        log_info(f"[{self.name()}] Starting parse phase...")

        all_events = []
        seen_event_keys: set[tuple] = set()

        for page in self.period_pages:
            # Process the war period page
            page_result = self._process_war_period_page(page)

            if page_result is None:
                continue

            # Convert wars to HistoricalEvent instances
            for war in page_result.wars:
                event = self._war_to_historical_event(war, page_result.canonical_url, page_result.title)

                if event is None:
                    continue

                # Deduplicate events within this strategy
                normalized_title = re.sub(r"\s+", " ", event.title.strip().lower())
                event_key = (
                    normalized_title,
                    int(event.start_year),
                    int(event.end_year),
                    bool(event.is_bc_start),
                )

                if event_key in seen_event_keys:
                    continue
                seen_event_keys.add(event_key)

                all_events.append(event)

        log_info(f"[{self.name()}] Parsed {len(all_events)} war events")

        return ParseResult(
            strategy_name=self.name(),
            events=all_events,
            parse_metadata={
                "pages_processed": len(self.visited_page_keys)
            }
        )

    def generate_artifacts(self, parse_result: ParseResult) -> ArtifactData:
        """Prepare artifact data for serialization.

        Args:
            parse_result: Result from parse phase.

        Returns:
            ArtifactData ready for serialization.
        """
        log_info(f"[{self.name()}] Preparing artifact data...")

        return ArtifactData(
            strategy_name=self.name(),
            run_id=self.run_id,
            generated_at_utc=datetime.utcnow().isoformat() + "Z",
            event_count=len(parse_result.events),
            events=parse_result.events,
            metadata=parse_result.parse_metadata,
            suggested_filename=f"events_{self.name().replace(' ', '_').lower()}_{self.run_id}.json"
        )

    def cleanup_logs(self) -> None:
        """Generate strategy-specific log files."""
        log_info(f"[{self.name()}] No additional logs to generate")

    # ===== Helper Methods =====

    def _discover_war_period_links(self, index_html: str) -> list[WarPeriodPage]:
        """Extract links to war period pages from the timeline index.

        Args:
            index_html: HTML content of the timeline index page

        Returns:
            List of discovered war period pages
        """
        soup = BeautifulSoup(index_html, 'html.parser')
        period_pages = []

        # Find all links that match the pattern "List of wars: <period>"
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().strip()

            # Match patterns like "List of wars: 1900–1944" or "List of wars: before 1000"
            if text.startswith("List of wars:"):
                # Extract the period range from the link text
                period_match = re.search(r"List of wars:\s*(.+)$", text)
                if period_match:
                    period_range = period_match.group(1).strip()

                    # Convert to full URL if it's a relative link
                    full_url = urljoin(WIKIPEDIA_BASE, href)

                    period_pages.append(WarPeriodPage(
                        title=text,
                        url=full_url,
                        period_range=period_range
                    ))

        return period_pages

    def _process_war_period_page(self, page: WarPeriodPage) -> ProcessedWarPage | None:
        """Process a single war period page and extract wars.

        Args:
            page: War period page metadata

        Returns:
            Processed page result or None if processing failed
        """
        # Avoid processing the same page multiple times
        page_key = (page.url, page.period_range)
        if page_key in self.visited_page_keys:
            return None
        self.visited_page_keys.add(page_key)

        log_info(f"Processing war period page: {page.title}")

        # Fetch the page HTML
        (html_pair, fetch_err) = get_html(page.url, context=f"war_period_{page.period_range}")
        html_content, actual_url = html_pair

        if fetch_err or not html_content.strip():
            log_error(f"Failed to fetch war period page {page.url}: {fetch_err}")
            return None

        # Canonicalize URL and get page identity
        canonical_url = _canonicalize_wikipedia_url(actual_url)
        page_identity = _resolve_page_identity(canonical_url)

        # Extract wars from tables
        wars = self._extract_wars_from_tables(html_content, canonical_url, page.title)

        return ProcessedWarPage(
            wars=wars,
            period_range=page.period_range,
            canonical_url=canonical_url,
            pageid=page_identity["pageid"] if page_identity else None,
            title=page.title
        )

    def _extract_wars_from_tables(self, html_content: str, source_url: str, source_title: str) -> list[WarEvent]:
        """Extract war events from HTML tables.

        Args:
            html_content: HTML content of the war period page
            source_url: Source URL for attribution
            source_title: Source page title

        Returns:
            List of extracted war events
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        wars = []

        # Find all tables in the page
        tables = soup.find_all('table')

        for table in tables:
            # Look for tables with war data (they typically have headers with years)
            headers = table.find_all(['th', 'td'])
            if not headers:
                continue

            # Check if this looks like a war table by examining headers
            header_texts = [h.get_text().strip().lower() for h in headers[:5]]
            if not any('year' in text or text in ['start', 'end', 'date'] for text in header_texts):
                continue

            # Extract rows
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header row
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:  # Need at least start year, end year, and name
                    continue

                try:
                    war = self._parse_war_row(cells, source_url, source_title)
                    if war:
                        wars.append(war)
                except Exception as e:
                    log_error(f"Failed to parse war row: {e}")
                    continue

        return wars

    def _parse_war_row(self, cells: list, source_url: str, source_title: str) -> WarEvent | None:
        """Parse a single table row into a WarEvent using strategy pattern.

        Args:
            cells: Table cells from the row
            source_url: Source URL for attribution
            source_title: Source page title

        Returns:
            WarEvent instance or None if parsing failed
        """
        if len(cells) < 3:
            return None

        # Extract cell texts
        cell_texts = [cell.get_text().strip() for cell in cells]

        # Use strategy pattern to find appropriate parser
        parser = self.parser_factory.get_parser(cell_texts)
        if parser is None:
            log_error(f"No parser found for row with cells: {cell_texts[:3]}...")
            return None

        # Parse the row using the selected strategy
        return parser.parse_row(cell_texts, source_url, source_title)

    def _war_to_historical_event(self, war: WarEvent, source_url: str, source_title: str) -> HistoricalEvent | None:
        """Convert a WarEvent to a HistoricalEvent.

        Args:
            war: War event to convert
            source_url: Source URL
            source_title: Source page title

        Returns:
            HistoricalEvent instance or None if conversion failed
        """
        try:
            # Create description from belligerents and notes
            description_parts = []
            if war.belligerents:
                description_parts.append(f"Belligerents: {', '.join(war.belligerents)}")
            if war.notes:
                description_parts.append(war.notes)

            description = ". ".join(description_parts) if description_parts else ""

            # Determine if this is BC (negative years)
            is_bc = war.start_year < 0

            # Calculate weight (duration in days)
            # Convert BC years to timeline years for calculation
            def to_timeline_year(year: int, is_bc: bool) -> int:
                if is_bc:
                    return -year + 1
                return year
            
            start_timeline = to_timeline_year(abs(war.start_year), war.start_year < 0)
            end_timeline = to_timeline_year(abs(war.end_year), war.end_year < 0)
            
            # Calculate approximate days (minimum 1 year = 365 days)
            year_diff = max(1, end_timeline - start_timeline + 1)
            weight = year_diff * 365

            return HistoricalEvent(
                title=war.title,
                description=description,
                start_year=abs(war.start_year),
                end_year=abs(war.end_year),
                is_bc_start=is_bc,
                is_bc_end=is_bc,
                category="War",  # All events from this strategy are wars
                url=source_url,
                precision=SpanPrecision.YEAR_ONLY,
                weight=weight,
                span_match_notes=f"War period extracted from table on {source_title}"
            )
        except Exception as e:
            log_error(f"Failed to convert war to historical event: {e}")
            return None