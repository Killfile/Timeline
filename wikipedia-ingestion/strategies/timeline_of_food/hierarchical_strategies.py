"""Hierarchical section parsing for Timeline of Food article.

This module provides functionality to parse the hierarchical structure of the
Wikipedia "Timeline of Food" article, extracting major sections and their
implied date ranges.
"""

from dataclasses import dataclass
import re
from bs4 import BeautifulSoup, Tag
from typing import Optional

from span_parsing.span import Span
from span_parsing.orchestrators.food_timeline_parse_orchestrator import FoodTimelineParseOrchestrator


@dataclass
class TextSection:
    """Hierarchical section in the Timeline of Food article.
    
    Represents a major section (e.g., "4000-2000 BCE", "19th century") with
    its inferred date range and position in the document.
    """
    
    name: str  # E.g., "4000-2000 BCE", "19th century"
    level: int  # Header level (2 for ##, 3 for ###, etc.)
    
    # Inferred date range from section heading
    date_range_start: int
    date_range_end: int
    date_is_explicit: bool  # True if dates in heading (e.g., "4000-2000 BCE")
    date_is_range: bool  # True if heading contains range
    
    # Position in document
    position: int  # Ordinal position (0-based)
    
    # Optional fields with defaults
    is_bc_start: bool = False  # True if start date is BC
    is_bc_end: bool = False  # True if end date is BC
    event_count: int = 0  # Number of events in this section
    inferred_date_range: Optional[tuple[int, int]] = None  # Final range after inheritance (signed years)


class TextSectionParser:
    """Parser for extracting hierarchical sections from HTML.
    
    Uses BeautifulSoup to parse Wikipedia article HTML and extract major sections
    with their implied date ranges using the FoodTimelineParseOrchestrator.
    """
    
    def __init__(self):
        """Initialize the section parser with date extraction orchestrator."""
        self.orchestrator = FoodTimelineParseOrchestrator()
    
    def parse_sections(self, html: str) -> list[TextSection]:
        """Parse all major sections from the article HTML.
        
        Args:
            html: Raw HTML content from Wikipedia article
        
        Returns:
            List of TextSection objects representing the article structure
        """
        soup = BeautifulSoup(html, 'html.parser')
        sections = []
        position = 0
        
        # Track latest section seen at each level for inheritance
        last_section_at_level: dict[int, TextSection] = {}
        
        # Process headers in document order (h2-h4)
        for header in soup.find_all(re.compile(r'^h[2-4]$')):
            
            section_name = header.get_text(strip=True)
            if not section_name or self._is_meta_section_by_name(section_name):
                continue
            
            level = int(header.name[-1])
            
            # Parse date range from section name
            date_info = self._parse_section_date(section_name)
            
            # Count events (most relevant for h2, but safe for all)
            event_count = self._count_events_in_section_by_header(header) if level == 2 else 0
            
            section = TextSection(
                name=section_name,
                level=level,
                date_range_start=date_info['start'],
                date_range_end=date_info['end'],
                date_is_explicit=date_info['is_explicit'],
                date_is_range=date_info['is_range'],
                position=position,
                is_bc_start=date_info['is_bc_start'],
                is_bc_end=date_info['is_bc_end'],
                event_count=event_count,
                inferred_date_range=date_info['inferred_span']
            )
            
            # If this is a child header (h3/h4) with no digits, drop fallback dates so it can inherit
            if level > 2 and not re.search(r"\d", section_name):
                section.inferred_date_range = None
                section.date_range_start = 0
                section.date_range_end = 0
                section.date_is_explicit = False
                section.date_is_range = False
                section.is_bc_start = False
                section.is_bc_end = False

            # Inherit date range from nearest ancestor if none parsed
            if section.inferred_date_range is None:
                parent_levels = [lvl for lvl in last_section_at_level if lvl < level]
                if parent_levels:
                    parent_level = max(parent_levels)
                    parent_section = last_section_at_level[parent_level]
                    section.inferred_date_range = parent_section.inferred_date_range
                    section.is_bc_start = parent_section.is_bc_start
                    section.is_bc_end = parent_section.is_bc_end
                    section.date_range_start = parent_section.date_range_start
                    section.date_range_end = parent_section.date_range_end
                    section.date_is_explicit = False
                    section.date_is_range = parent_section.date_range_start != parent_section.date_range_end
            
            sections.append(section)
            last_section_at_level[level] = section
            position += 1
        
        return sections
    
    def _is_meta_section_by_name(self, section_name: str) -> bool:
        """Check if section name indicates a meta/navigation section to skip.
        
        Args:
            section_name: Section heading text
        
        Returns:
            True if this is a meta section (Contents, References, etc.)
        """
        section_lower = section_name.lower()
        meta_sections = [
            'contents', 'references', 'external links', 'see also',
            'notes', 'further reading', 'bibliography', 'sources'
        ]
        return section_lower in meta_sections
    
    def _parse_section_date(self, section_name: str) -> dict:
        """Parse date range from section name using orchestrator.
        
        Args:
            section_name: Section heading text (e.g., "4000-2000 BCE")
        
        Returns:
            Dictionary with keys: start, end, is_explicit, is_range, is_bc_start, is_bc_end, inferred_span
        """
        # Try a header-specific range regex first to capture "4000-2000 BCE" style headings
        range_match = re.match(r"^\s*(\d{1,4})\s*[–—−-]\s*(\d{1,4})\s*(BCE|BC|CE|AD)?\s*$", section_name, flags=re.IGNORECASE)
        if range_match:
            start_val = int(range_match.group(1))
            end_val = int(range_match.group(2))
            era = (range_match.group(3) or "").upper()
            is_bc = era in {"BC", "BCE"}
            is_range = True
            start_signed = self._to_signed_year(start_val, is_bc)
            end_signed = self._to_signed_year(end_val, is_bc)
            return {
                'start': start_signed,
                'end': end_signed,
                'is_explicit': True,
                'is_range': is_range,
                'is_bc_start': is_bc,
                'is_bc_end': is_bc,
                'inferred_span': (start_signed, end_signed),
            }

        # Try to parse date using orchestrator
        span = self.orchestrator.parse_span_from_bullet(section_name, span_year=2000, assume_is_bc=False)

        if span:
            start = self._to_signed_year(span.start_year, span.start_year_is_bc)
            end = self._to_signed_year(span.end_year, span.end_year_is_bc)
            return {
                'start': start,
                'end': end,
                'is_explicit': True,
                'is_range': span.start_year != span.end_year,
                'is_bc_start': span.start_year_is_bc,
                'is_bc_end': span.end_year_is_bc,
                'inferred_span': (start, end),
            }
        
        # Fallback for sections without parseable dates (e.g., "Prehistoric times")
        return {
            'start': 0,
            'end': 0,
            'is_explicit': False,
            'is_range': False,
            'is_bc_start': False,
            'is_bc_end': False,
            'inferred_span': None,
        }

    @staticmethod
    def _to_signed_year(year: int, is_bc: bool) -> int:
        """Convert year and BC flag to signed integer (BC → negative)."""
        return -year if is_bc else year
    
    def _count_events_in_section_by_header(self, header: Tag) -> int:
        """Count bullet point events following this header.
        
        Args:
            header: BeautifulSoup Tag object for the h2 header
        
        Returns:
            Number of list items found in the section
        """
        count = 0
        
        # Get the parent div (mw-heading) and then find siblings
        header_container = header.parent
        if header_container and header_container.name == 'div':
            siblings_to_search = header_container.find_next_siblings()
        else:
            siblings_to_search = header.find_next_siblings()
        
        # Find the next sibling elements until the next header
        for sibling in siblings_to_search:
            # Stop at next header container
            if sibling.name == 'div' and 'mw-heading' in sibling.get('class', []):
                break
            
            # Count list items
            if sibling.name == 'ul':
                count += len(sibling.find_all('li', recursive=False))
        
        return count
