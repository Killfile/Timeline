"""LGBTQ History v2 Strategy - Complete rewrite with proper architecture."""

import re
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
from pathlib import Path

from bs4 import BeautifulSoup

from ingestion_common import log_info, log_error, get_html
from strategies.strategy_base import IngestionStrategy, FetchResult, ParseResult, ArtifactData
from strategies.lgbtq_history_v2.page_parsing_strategies import PageParsingStrategyFactory
from strategies.lgbtq_history_v2.hierarchy_parsing_strategies import HierarchyParsingStrategyFactory
from strategies.lgbtq_history_v2.event_parsing_strategies import EventParsingStrategyFactory
from historical_event import HistoricalEvent


class LgbtqHistoryV2Strategy(IngestionStrategy):
    """LGBTQ History v2 Strategy with proper architectural separation."""

    ROOT_TIMELINE_URL = "https://en.wikipedia.org/wiki/Timeline_of_LGBTQ_history"

    def __init__(self, run_id: str, output_dir: Path):
        """Initialize the strategy with required factories."""
        super().__init__(run_id, output_dir)
        self.page_strategy_factory = PageParsingStrategyFactory()
        self.hierarchy_strategy_factory = HierarchyParsingStrategyFactory()
        self.event_strategy_factory = EventParsingStrategyFactory()

    def name(self) -> str:
        """Return the strategy name."""
        return "lgbtq_history_v2"

    def fetch(self) -> FetchResult:
        """Step 1: Collect all page URLs to parse."""
        log_info("Starting LGBTQ History v2 fetch phase")

        # Collect all page URLs
        page_urls = self._collect_page_urls()
        log_info(f"Found {len(page_urls)} pages to parse: {list(page_urls)}")

        return FetchResult(
            strategy_name=self.name(),
            fetch_count=len(page_urls),
            fetch_metadata={
                "page_urls": list(page_urls)
            }
        )

    def parse(self, fetch_result: FetchResult) -> ParseResult:
        """Step 2: Parse each page for events."""
        log_info("Starting LGBTQ History v2 parse phase")

        page_urls = fetch_result.fetch_metadata["page_urls"]
        all_events = []

        for url in page_urls:
            try:
                events = self._parse_page_events(url)
                all_events.extend(events)
                log_info(f"Parsed {len(events)} events from {url}")
            except Exception as e:
                log_error(f"Failed to parse page {url}: {e}")

        log_info(f"Total events parsed: {len(all_events)}")
        return ParseResult(
            strategy_name=self.name(),
            events=all_events,
            parse_metadata={
                "pages_parsed": len(page_urls),
                "total_events": len(all_events)
            }
        )

    def generate_artifacts(self, parse_result: ParseResult) -> ArtifactData:
        """Generate artifact data."""
        from datetime import datetime

        return ArtifactData(
            strategy_name=self.name(),
            run_id=self.run_id,
            generated_at_utc=datetime.utcnow().isoformat() + "Z",
            event_count=len(parse_result.events),
            events=parse_result.events,
            metadata=parse_result.parse_metadata,
            suggested_filename=f"events_{self.name()}_{self.run_id}.json"
        )

    def cleanup_logs(self) -> None:
        """No special log cleanup needed."""
        pass

    def _collect_page_urls(self) -> Set[str]:
        """Step 1: Collect all page URLs that contain timeline events."""
        urls = {self.ROOT_TIMELINE_URL}  # Always include the root timeline

        # Fetch the root timeline page
        soup = self._fetch_page(self.ROOT_TIMELINE_URL)
        if not soup:
            return urls

        # Find all "Main article:" links
        main_article_elements = soup.find_all(string=lambda text: text and 'Main article:' in text.strip())
        for text_element in main_article_elements:
            # The text is in a div, find the link within the same parent
            parent = text_element.parent
            if parent:
                link = parent.find('a')
                if link:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(self.ROOT_TIMELINE_URL, href)
                        # Only include Wikipedia pages
                        if urlparse(full_url).netloc == 'en.wikipedia.org':
                            urls.add(full_url)

        return urls

    def _parse_page_events(self, url: str) -> List[HistoricalEvent]:
        """Step 2: Parse events from a single page."""
        soup = self._fetch_page(url)
        if not soup:
            return []

        # Get the appropriate page parsing strategy
        page_strategy = self.page_strategy_factory.get_strategy(url, soup)
        if not page_strategy:
            log_error(f"No page parsing strategy found for {url}")
            return []

        # Parse the page structure
        page_data = page_strategy.parse_page(url, soup)
        if not page_data:
            return []

        events = []

        # For each hierarchy in the page, parse events
        for hierarchy in page_data.hierarchies:
            hierarchy_events = self._parse_hierarchy_events(hierarchy, url)
            events.extend(hierarchy_events)

        return events

    def _parse_hierarchy_events(self, hierarchy, source_url: str) -> List[HistoricalEvent]:
        """Parse events from a single hierarchy structure."""
        log_info(f"Parsing hierarchy events from {source_url}")
        log_info(f"Hierarchy type: {type(hierarchy)}, keys: {list(hierarchy.keys()) if hasattr(hierarchy, 'keys') else 'no keys'}")
        
        # Get the appropriate hierarchy parsing strategy
        hierarchy_strategy = self.hierarchy_strategy_factory.get_strategy(hierarchy)
        if not hierarchy_strategy:
            log_error(f"No hierarchy parsing strategy found for {type(hierarchy)}")
            return []

        log_info(f"Using hierarchy strategy: {hierarchy_strategy.__class__.__name__}")

        # Parse the hierarchy into event candidates
        event_candidates = hierarchy_strategy.parse_hierarchy(hierarchy)
        log_info(f"Hierarchy parsing returned {len(event_candidates)} candidates")

        events = []
        for i, candidate in enumerate(event_candidates):
            log_info(f"Processing candidate {i+1}/{len(event_candidates)}: '{candidate.text[:100]}...'")
            
            # Get the appropriate event parsing strategy
            event_strategy = self.event_strategy_factory.get_strategy(candidate)
            if event_strategy:
                log_info(f"Using {event_strategy.__class__.__name__} for candidate")
                event = event_strategy.parse_event(candidate, source_url)
                if event:
                    events.append(event)
                    log_info(f"Successfully parsed event: '{event.title} [{event.start_year} - {event.end_year}]'")
                else:
                    log_info("Event strategy returned None")
            else:
                log_info("No event parsing strategy found for candidate")

        log_info(f"_parse_hierarchy_events returning {len(events)} events")
        return events

    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page and return parsed BeautifulSoup."""
        try:
            (html_pair, fetch_err) = get_html(url, context="lgbtq_v2")
            html_content, final_url = html_pair
            
            if fetch_err or not html_content or not html_content.strip():
                log_error(f"Failed to fetch page {url}: {fetch_err}")
                return None
                
            return BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            log_error(f"Failed to fetch page {url}: {e}")
        return None