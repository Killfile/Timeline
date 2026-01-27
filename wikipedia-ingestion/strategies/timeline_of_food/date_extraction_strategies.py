"""Date extraction strategies for Timeline of Food events.

This module provides functionality to parse bullet point events and extract dates
using the FoodTimelineParseOrchestrator.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup, Tag

from span_parsing.orchestrators.food_timeline_parse_orchestrator import FoodTimelineParseOrchestrator
from span_parsing.span import Span
from .food_event import FoodEvent
from .hierarchical_strategies import TextSection


logger = logging.getLogger(__name__)


@dataclass
class EventParseResult:
    """Result of parsing a single event bullet point."""
    
    event: FoodEvent | None  # Parsed event (None if parsing failed)
    has_date: bool  # True if date was successfully extracted
    error_message: str | None = None  # Error description if parsing failed


class EventParser:
    """Parser for extracting events from bullet points.
    
    Uses FoodTimelineParseOrchestrator to parse dates and creates FoodEvent
    instances with proper date ranges and confidence levels.
    """
    
    def __init__(self, anchor_year: int | None = None):
        """Initialize the event parser with date extraction orchestrator.
        
        anchor_year sets the reference year for relative formats (e.g., "years ago").
        Defaults to current UTC year when not provided.
        """
        self.orchestrator = FoodTimelineParseOrchestrator()
        self.anchor_year = anchor_year or datetime.utcnow().year
        self.undated_events: list[dict] = []  # Track events without dates
    
    def parse_bullet_point(
        self,
        bullet_text: str,
        section: TextSection,
        source_format: str = "bullet"
    ) -> EventParseResult:
        """Parse a single bullet point event.
        
        Args:
            bullet_text: Raw text of the bullet point
            section: TextSection containing this event (for context)
            source_format: Format of the source ("bullet" | "table" | "mixed")
        
        Returns:
            EventParseResult with parsed event or error information
        """
        # Clean bullet text
        clean_text = self._clean_bullet_text(bullet_text)
        
        if not clean_text:
            return EventParseResult(
                event=None,
                has_date=False,
                error_message="Empty bullet text after cleaning"
            )
        
        # Extract date using orchestrator
        span = self.orchestrator.parse_span_from_bullet(
            clean_text,
            span_year=self.anchor_year,
            assume_is_bc=section.is_bc_start
        )

        # Determine if we need to fall back to section context
        used_section_fallback = False
        fallback_start = None
        fallback_end = None
        fallback_is_bc_start = False
        fallback_is_bc_end = False

        if not span and section.inferred_date_range:
            fallback_start, fallback_end = section.inferred_date_range
            # Respect signed years or explicit BC flags on the section
            fallback_is_bc_start = fallback_start < 0 or section.is_bc_start
            fallback_is_bc_end = fallback_end < 0 or section.is_bc_end
            used_section_fallback = True
        
        # Extract Wikipedia links
        wiki_links = self._extract_wiki_links(bullet_text)
        
        # Extract citation references
        citations = self._extract_citations(bullet_text)
        
        # Contentious/disputed marker detection
        is_contentious = bool(re.search(r"\b(contentious|disputed)\b", clean_text, flags=re.IGNORECASE))

        # Determine confidence level
        confidence = self._determine_confidence(span, section, used_section_fallback, is_contentious)

        parsing_notes = None
        if is_contentious:
            parsing_notes = "contentious/disputed date reference"

        # Log how the date was resolved (explicit/decade/section fallback)
        self._log_date_resolution(
            clean_text,
            section,
            span,
            used_section_fallback,
            fallback_start,
            fallback_end,
        )
        
        # Log undated events without usable section context
        if not span and not used_section_fallback:
            self._log_undated_event(clean_text, section)
            # Don't create event for undated items
            return EventParseResult(
                event=None,
                has_date=False,
                error_message="No date found in text"
            )
        
        # Build normalized date fields (span or section fallback)
        if span:
            start_year = span.start_year
            end_year = span.end_year
            is_bc_start = span.start_year_is_bc
            is_bc_end = span.end_year_is_bc
            is_circa = span.match_type and "CIRCA" in span.match_type.upper() if span.match_type else False
            span_match_notes = span.match_type if span.match_type else "UNKNOWN"
            precision_val = self._calculate_precision(span)
        else:
            start_year = fallback_start or 0
            end_year = fallback_end or 0
            is_bc_start = fallback_is_bc_start
            is_bc_end = fallback_is_bc_end
            is_circa = False
            span_match_notes = "SECTION_FALLBACK"
            precision_val = 0.3
        
        event = FoodEvent(
            event_key="",  # Will be generated in __post_init__
            source="Timeline of Food",
            date_explicit=start_year if start_year == end_year else None,
            date_range_start=start_year,
            date_range_end=end_year,
            is_bc_start=is_bc_start,
            is_bc_end=is_bc_end,
            is_date_approximate=is_circa,
            is_date_range=start_year != end_year,
            confidence_level=confidence,
            title="",  # Will be generated from description
            description=clean_text,
            section_name=section.name,
            section_date_range_start=section.date_range_start,
            section_date_range_end=section.date_range_end,
            wikipedia_links=wiki_links,
            external_references=citations,
            source_format=source_format,
            span_match_notes=span_match_notes,
            parsing_notes=parsing_notes,
            precision=precision_val,
        )
        
        return EventParseResult(
            event=event,
            has_date=True,
            error_message=None
        )
    
    def _clean_bullet_text(self, text: str) -> str:
        """Clean bullet point text for parsing.
        
        Removes HTML tags, normalizes whitespace, removes bullet markers.
        
        Args:
            text: Raw bullet text (may contain HTML)
        
        Returns:
            Cleaned text string
        """
        # Parse as HTML to extract text content
        soup = BeautifulSoup(text, 'html.parser')
        
        # Remove citation superscripts
        for sup in soup.find_all('sup'):
            sup.decompose()
        
        # Get text content
        clean = soup.get_text()
        
        # Normalize whitespace
        clean = " ".join(clean.split())
        
        # Remove leading bullet markers (-, •, *, etc.)
        clean = re.sub(r'^[\-\•\*\◦\▪\→]\s*', '', clean)
        
        return clean.strip()
    
    def _extract_wiki_links(self, html_text: str) -> list[str]:
        """Extract Wikipedia links from HTML text.
        
        Args:
            html_text: Text potentially containing HTML <a> tags
        
        Returns:
            List of Wikipedia article titles
        """
        soup = BeautifulSoup(html_text, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Match Wikipedia article links like /wiki/Article_Name
            if href.startswith('/wiki/') and ':' not in href:
                article_name = href[6:]  # Remove /wiki/ prefix
                links.append(article_name)
        
        return links
    
    def _extract_citations(self, text: str) -> list[int]:
        """Extract citation reference numbers from text.
        
        Args:
            text: Text containing citation markers like [1], [2]
        
        Returns:
            List of citation numbers
        """
        # Match [1], [2], etc.
        matches = re.findall(r'\[(\d+)\]', text)
        return [int(m) for m in matches]
    
    def _determine_confidence(self, span: Optional[Span], section: TextSection, used_section_fallback: bool = False, is_contentious: bool = False) -> str:
        """Determine confidence level for the date extraction.
        
        Args:
            span: Parsed date span (None if no date found)
            section: Section context
            used_section_fallback: True if section context supplied the date
            is_contentious: True if text contains contentious/disputed markers
        
        Returns:
            Confidence level: "explicit" | "inferred" | "approximate" | "contentious" | "fallback"
        """
        if is_contentious:
            return "contentious"
        if used_section_fallback:
            return "inferred"
        if not span:
            return "fallback"
        
        # Check if match type (string) indicates approximate/circa
        if span.match_type and "CIRCA" in span.match_type.upper():
            return "approximate"
        
        # YEARS_AGO must be checked before YEAR (since "YEAR" is in "YEARS_AGO")
        if span.match_type and "YEARS_AGO" in span.match_type.upper():
            return "approximate"

        if span.match_type and "DECADE" in span.match_type.upper():
            return "explicit"
        
        # Check if match type is a year format (explicit)
        if span.match_type and "YEAR" in span.match_type.upper():
            return "explicit"
        
        # Century formats are approximate
        if span.match_type and "CENTURY" in span.match_type.upper():
            return "approximate"
        
        # Default to explicit for matched dates
        return "explicit"

    def _log_date_resolution(
        self,
        text: str,
        section: TextSection,
        span: Optional[Span],
        used_section_fallback: bool,
        fallback_start: int | None,
        fallback_end: int | None,
    ) -> None:
        """Log how the date was resolved for observability.

        Args:
            text: Cleaned event text
            section: Section context
            span: Parsed span if available
            used_section_fallback: Whether section range was used
            fallback_start: Section fallback start year
            fallback_end: Section fallback end year
        """
        preview = text[:80]

        if used_section_fallback:
            logger.info(
                "Section-inferred date applied %s-%s for '%s' in section '%s'",
                fallback_start,
                fallback_end,
                preview,
                section.name,
            )
            return

        if not span:
            return

        match = (span.match_type or "UNKNOWN").upper()
        if "DECADE" in match:
            logger.info(
                "Decade-parsed date %s-%s for '%s' in section '%s'",
                span.start_year,
                span.end_year,
                preview,
                section.name,
            )
        else:
            logger.debug(
                "Explicit date parsed via %s for '%s' in section '%s'",
                span.match_type or "UNKNOWN",
                preview,
                section.name,
            )
    
    def _calculate_precision(self, span: Span) -> float:
        """Calculate numeric precision value from span.
        
        Higher values indicate more precise dates.
        
        Args:
            span: Parsed date span
        
        Returns:
            Precision value (0.0 to 1.0)
        """
        # Span.precision is already a float, so return it directly
        # If it's an enum, get its numeric value
        if hasattr(span.precision, 'value'):
            return float(span.precision.value)
        
        # Otherwise use it as-is
        return float(span.precision)
    
    def _log_undated_event(self, text: str, section: TextSection) -> None:
        """Log an event that has no parseable date.
        
        Args:
            text: Event description text
            section: Section context
        """
        undated_info = {
            "text": text[:100],  # First 100 chars
            "section": section.name,
            "section_date_range": f"{section.date_range_start}-{section.date_range_end}"
        }
        
        self.undated_events.append(undated_info)
        logger.warning(f"Undated event in section '{section.name}': {text[:50]}...")
    
    def get_undated_summary(self) -> dict:
        """Get summary of undated events encountered during parsing.
        
        Returns:
            Dictionary with undated event statistics
        """
        return {
            "total_undated": len(self.undated_events),
            "events": self.undated_events
        }
