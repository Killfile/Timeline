"""List of Time Periods ingestion strategy implementation.

This strategy parses the "Technological periods" section from Wikipedia's
"List of time periods" page.

Key characteristics:
- No need to follow links - all data is on one page
- Date ranges are at end of lines in parentheses: (1760-1970)
- Hierarchical structure with varying indent levels
- "present" should be substituted with current calendar year (2026)
- Uses ≈ character as a circa indicator
- Header levels need to be tracked to build context for event titles/descriptions

Example entries:
  • Industrial Age (1760–1970)
  • Machine Age (1880–1945)
   • Age of Oil (1901–present)
   • Jet Age (1940s)
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag


from ingestion_common import (
    LOGS_DIR,
    get_html,
    log_error,
    log_info,
)
from span_parsing.span import Span, SpanEncoder, SpanPrecision
from span_parsing.orchestrators.parse_orchestrator_factory import ParseOrchestratorFactory, ParseOrchestratorTypes
from strategies.strategy_base import (
    ArtifactData,
    FetchResult,
    IngestionStrategy,
    ParseResult,
)
from historical_event import HistoricalEvent


# Constants
TIME_PERIODS_URL = "https://en.wikipedia.org/wiki/List_of_time_periods"
CURRENT_YEAR = 2026  # Substitute for "present"
SECTION_HEADINGS = [
    "Technological periods",
    "African periods",
    "American (continent) periods",
    "Asian periods",
    "European periods",
    "Oceanian periods",
]


class ListOfTimePeriodsStrategy(IngestionStrategy):
    """Strategy for ingesting from Wikipedia's List of Time Periods page."""

    def name(self) -> str:
        return "Major Time Periods"

    def fetch(self) -> FetchResult:
        """Fetch the List of Time Periods page.

        Returns:
            FetchResult with HTML content and metadata.
        """
        log_info(f"Fetching {TIME_PERIODS_URL}")
        
        (html_content, final_url), error = get_html(TIME_PERIODS_URL, context="time_periods_page")
        if error:
            raise RuntimeError(f"Failed to fetch time periods page: {error}")
        
        return FetchResult(
            strategy_name=self.name(),
            fetch_count=1,
            fetch_metadata={
                "url": TIME_PERIODS_URL,
                "html_length": len(html_content),
                "fetched_at": datetime.utcnow().isoformat(),
            }
        )

    def parse(self, fetch_result: FetchResult) -> ParseResult:
        """Parse all configured time period sections.

        Args:
            fetch_result: Result from fetch phase with HTML content.

        Returns:
            ParseResult with extracted events from all sections.
        """
        log_info(f"Parsing {len(SECTION_HEADINGS)} sections: {', '.join(SECTION_HEADINGS)}")
        
        parse_start = datetime.utcnow()
        
        # Re-fetch to get the HTML (in real implementation we'd store it in fetch_result)
        (html_content, final_url), error = get_html(TIME_PERIODS_URL, context="time_periods_page")
        if error:
            log_error(f"Failed to fetch HTML for parsing: {error}")
            return ParseResult(
                strategy_name=self.name(),
                events=[],
                parse_metadata={"error": f"Failed to fetch HTML: {error}"}
            )
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Collect events from all sections
        all_events = []
        sections_found = []
        sections_missing = []
        
        for section_name in SECTION_HEADINGS:
            log_info(f"Processing section: {section_name}")
            section_heading = self._find_section_heading(soup, section_name)
            
            if not section_heading:
                log_error(f"Could not find '{section_name}' section")
                sections_missing.append(section_name)
                continue
            
            # Extract events from this section
            section_events = self._extract_events_from_section(soup, section_heading, section_name)
            all_events.extend(section_events)
            sections_found.append(section_name)
            log_info(f"Extracted {len(section_events)} events from '{section_name}' section")
        
        parse_end = datetime.utcnow()
        elapsed = (parse_end - parse_start).total_seconds()
        
        log_info(f"Total extracted: {len(all_events)} time period events from {len(sections_found)} sections")
        
        # Calculate confidence distribution (time periods are approximate by nature)
        from strategies.strategy_base import normalize_confidence_distribution
        
        confidence_dist = normalize_confidence_distribution({
            "explicit": 0,
            "inferred": 0,
            "approximate": len(all_events),
            "contentious": 0,
            "fallback": 0,
        })
        
        return ParseResult(
            strategy_name=self.name(),
            events=all_events,
            parse_metadata={
                "total_events_found": len(all_events),
                "total_events_parsed": len(all_events),
                "sections_identified": len(sections_found),
                "parsing_start_utc": parse_start.isoformat() + "Z",
                "parsing_end_utc": parse_end.isoformat() + "Z",
                "elapsed_seconds": elapsed,
                "events_per_second": len(all_events) / elapsed if elapsed > 0 else 0,
                "confidence_distribution": confidence_dist,
                "undated_events": {
                    "total_undated": 0,
                    "events": []
                },
            }
        )

    def generate_artifacts(self, parse_result: ParseResult) -> ArtifactData:
        """Prepare artifact data for serialization.

        Args:
            parse_result: Result from parse phase with events.

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
            suggested_filename=f"events_{self.name()}_{self.run_id}.json"
        )

    def cleanup_logs(self) -> None:
        """No special log cleanup needed for this strategy."""
        pass

    # Helper methods
    
    def _find_section_heading(self, soup: BeautifulSoup, heading_text: str) -> Tag | None:
        """Find the heading tag for a specific section.

        Args:
            soup: BeautifulSoup parsed HTML
            heading_text: Text content of the heading to find

        Returns:
            The heading tag, or None if not found
        """
        # Look for h2, h3, h4 headings with matching text
        for tag_name in ['h2', 'h3', 'h4']:
            headings = soup.find_all(tag_name)
            for heading in headings:
                # Get text, removing edit links
                text = heading.get_text(strip=True)
                # Remove [edit] markers
                text = re.sub(r'\[edit\]', '', text).strip()
                if text == heading_text:
                    return heading
        return None

    def _extract_events_from_section(self, soup: BeautifulSoup, section_heading: Tag, section_name: str) -> list[HistoricalEvent]:
        """Extract time period events from the section content.

        Args:
            soup: BeautifulSoup parsed HTML
            section_heading: The heading tag that starts the section
            section_name: Name of the section being parsed

        Returns:
            List of event dictionaries
        """
        events = []

        # Track header context as we drill down
        header_stack = []

        # Iterate document-order from the section heading forward, processing
        # any <ul> elements encountered until we hit the next heading of the
        # same or higher level. This is more robust than walking only
        # immediate siblings because Wikipedia often nests lists inside
        # intermediate containers (links/divs), which previously caused us to
        # miss valid lists (e.g., under 'African periods').
        el = section_heading
        while True:
            el = el.find_next()
            if not el:
                break

            # If we hit another section heading of the same-or-higher level,
            # stop processing this section.
            if isinstance(el, Tag) and el.name in ['h2', 'h3', 'h4']:
                if self._heading_level(el) <= self._heading_level(section_heading):
                    break

            # Process any <ul> we find in document order
            if isinstance(el, Tag) and el.name == 'ul':
                self._process_list(el, events, header_stack, section_name)

        return events

    def _heading_level(self, tag: Tag) -> int:
        """Get numeric level of a heading tag (h2=2, h3=3, etc)."""
        match = re.match(r'h(\d)', tag.name)
        return int(match.group(1)) if match else 0

    def _process_list(self, ul_tag: Tag, events: list[HistoricalEvent], header_stack: list[str], section_name: str) -> None:
        """Process a <ul> list, extracting time periods recursively.

        Args:
            ul_tag: The <ul> tag to process
            events: List to append extracted events to
            header_stack: Stack of parent headers for context
            section_name: Name of the section being parsed
        """
        for li in ul_tag.find_all('li', recursive=False):
            # Get the text content of this list item (excluding nested lists)
            li_text = self._get_li_direct_text(li)
            
            # Check if this is a header item (bold text, no date range)
            is_header = self._is_header_item(li)
            
            if is_header:
                # Push onto header stack
                header_text = self._clean_text(li_text)
                header_stack.append(header_text)
                
                # Process nested lists with this header context
                nested_ul = li.find('ul', recursive=False)
                if nested_ul:
                    self._process_list(nested_ul, events, header_stack, section_name)
                
                # Pop header when done
                header_stack.pop()
            else:
                # This is an event item - extract it
                event = self._extract_event(li, li_text, header_stack, len(events), section_name)
                if event:
                    events.append(event)
                
                # Still check for nested items under this event
                nested_ul = li.find('ul', recursive=False)
                if nested_ul:
                    # Keep same header stack (nested events at same level)
                    self._process_list(nested_ul, events, header_stack, section_name)

    def _get_li_direct_text(self, li: Tag) -> str:
        """Get text directly in the <li>, excluding nested <ul> content."""
        # Clone the li and remove nested ul tags
        li_copy = li.__copy__()
        for nested in li_copy.find_all('ul'):
            nested.decompose()
        return li_copy.get_text(strip=True)

    def _is_header_item(self, li: Tag) -> bool:
        """Determine if a list item is a header (no date range).

        Headers typically don't have date ranges in parentheses at the end.
        """
        li_text = self._get_li_direct_text(li)
        # If there's a date range in parentheses at the end, it's an event not a header
        has_date_range = bool(re.search(r'\([^)]*\d{3,4}[^)]*\)\s*$', li_text))
        return not has_date_range

    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace, [edit] markers, etc."""
        text = re.sub(r'\[edit\]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_event(self, li: Tag, li_text: str, header_stack: list[str], event_index: int, section_name: str) -> HistoricalEvent | None:
        """Extract a single time period event from a list item.

        Args:
            li: The <li> tag
            li_text: Direct text content of the li
            header_stack: Parent headers for context
            event_index: Index of this event in the events list
            section_name: Name of the section being parsed

        Returns:
            HistoricalEvent instance in canonical schema format, or None if parsing fails
        """
        # Extract date range from parentheses at end
        date_match = re.search(r'\(([^)]*\d{3,4}[^)]*)\)\s*$', li_text)
        if date_match:
            name = li_text[:date_match.start()].strip()
        else:
            name = li_text
        
        # Get the name/title (everything before the date parentheses)
        
        name = self._clean_text(name)
        
        # Remove link brackets if present
        name = re.sub(r'\[.*?\]', '', name).strip()
        
        # Parse the date range using the span parsing framework
        print(f"Parsing date range from li_text: {li_text}")
        span = self._parse_date_range(li_text)
        if not span:
            # Error already logged in _parse_date_range
            return None
        
        # Build title with header context
        if header_stack:
            title = f"{' - '.join(header_stack)} - {name}"
        else:
            title = name
        
        # Truncate title if too long (max 500 chars for DB)
        if len(title) > 500:
            title = title[:497] + "..."
        
        # Build description
        description = self._build_description(name, header_stack)
        
        # Truncate description if too long
        if len(description) > 500:
            description = description[:497] + "..."
        
        # Extract Wikipedia link if present
        wiki_link = self._extract_wiki_link(li)
        
        # Create canonical event using HistoricalEvent.from_span_dict helper
        # which flattens the span fields to top level
        span_dict = span.to_dict()
        
        # Debug: Check precision value
        if span_dict.get('precision') == 0 or span_dict.get('precision') is None:
            log_error(f"⚠️  PRECISION ISSUE: Event '{name}' has precision={span_dict.get('precision')}. Span: {span}")
        
        canonical_event = HistoricalEvent.from_span_dict(
            title=title,
            description=description,
            url=wiki_link or TIME_PERIODS_URL,
            span_dict=span_dict,
            category=header_stack[0] if header_stack else section_name,
            pageid=None,  # No pageid for list_of_time_periods entries
            span_match_notes=span.match_type,
            debug_info={
                "event_key": f"time_period_{self.run_id}_{event_index}",
                "original_li_text": li_text,
                "header_stack": header_stack,
                "section_name": section_name,
                "span_match_type": span.match_type,
            }
        )
        
        return canonical_event

    def _parse_date_range(self, date_str: str) -> Span | None:
        """Parse a date range string into a Span object using the span_parsing framework

        Args:
            date_str: The date string to parse

        Returns:
            Span object, or None if parsing fails
        """
        # Preprocess the date string
        original_date_str = date_str
        
        # Substitute "present" with current year
        date_str = re.sub(r'\bpresent\b', str(CURRENT_YEAR), date_str, flags=re.IGNORECASE)
        if date_str is None:
            print(f"🚨 date_str is None after substitution for present: {original_date_str}")
        orchestrator = ParseOrchestratorFactory.get_orchestrator(ParseOrchestratorTypes.TIME_PERIODS)
        span = orchestrator.parse_span_from_bullet(text=date_str, span_year=2000, assume_is_bc=False)
        
        if span:
            return span
        
        # If parsing failed, log the error
        log_error(f"Could not parse date range: {original_date_str}")
        return None

    def _build_description(self, name: str, header_stack: list[str]) -> str:
        """Build a description string from the event name and context."""
        if header_stack:
            context = ' / '.join(header_stack)
            return f"{name} (from {context})"
        return name

    def _extract_wiki_link(self, li: Tag) -> str | None:
        """Extract Wikipedia link from list item if present."""
        link = li.find('a', href=re.compile(r'^/wiki/'))
        if link and 'href' in link.attrs:
            href = link['href']
            return f"https://en.wikipedia.org{href}"
        return None


# For testing as a standalone module
if __name__ == "__main__":
    from pathlib import Path
    import sys
    
    # Test the strategy
    run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path("artifacts")
    
    strategy = ListOfTimePeriodsStrategy(run_id, output_dir)
    
    print(f"Strategy: {strategy.name()}")
    print(f"Run ID: {run_id}")
    print()
    
    # Fetch
    print("Fetching...")
    fetch_result = strategy.fetch()
    print(f"  Fetched: {fetch_result.fetch_count} page(s)")
    print()
    
    # Parse
    print("Parsing...")
    parse_result = strategy.parse(fetch_result)
    print(f"  Extracted: {len(parse_result.events)} events")
    print()
    
    # Show first few events
    for i, event in enumerate(parse_result.events[:5]):
        print(f"Event {i+1}:")
        print(f"  Title: {event['title']}")
        print(f"  Span: {event['span']['start_year']}-{event['span']['end_year']} {event['span']['era']}")
        print()
    
    # Generate artifacts
    print("Generating artifacts...")
    artifact_result = strategy.generate_artifacts(parse_result)
    print(f"  Artifact: {artifact_result.artifact_path}")
    print()
    
    print("Done!")
