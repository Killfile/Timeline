"""Page parsing strategies for different types of timeline pages."""

import re
from typing import Optional
from bs4 import BeautifulSoup, Tag

from strategies.lgbtq_history_v2.base_classes import PageParsingStrategy, PageData
from ingestion_common import log_info, log_error


class MainTimelinePageStrategy(PageParsingStrategy):
    """Strategy for parsing the main Timeline of LGBTQ history page."""

    def can_parse(self, url: str, soup) -> bool:
        """Check if this is the main timeline page."""
        return "Timeline_of_LGBTQ_history" in url and not any(period in url for period in ["19th", "20th", "21st"])

    def parse_page(self, url: str, soup) -> Optional[PageData]:
        """Parse the main timeline page."""
        log_info(f"MainTimelinePageStrategy parsing page: {url}")
        
        title = soup.find('h1', {'id': 'firstHeading'})
        title_text = title.get_text().strip() if title else "Timeline of LGBTQ History"
        log_info(f"Page title: {title_text}")

        # Find the main content area
        content = soup.find('div', {'id': 'mw-content-text'})
        if not content:
            log_error("No content div found")
            return None

        # For the main timeline, we treat sections as hierarchies
        hierarchies = []

        # Find all section headers and their content
        headers = content.find_all(['h2', 'h3', 'h4'], recursive=True)
        log_info(f"Found {len(headers)} headers to process")
        
        for i, header in enumerate(headers):
            header_text = header.get_text().strip()
            log_info(f"Processing header {i+1}: '{header_text}'")

            # Stop at "See also" or similar
            if re.search(r'\bSee also\b', header_text, re.IGNORECASE):
                log_info("Stopping at 'See also' section")
                break

            # Skip non-timeline sections
            if not self._is_timeline_section(header_text):
                log_info("Skipping non-timeline section")
                continue

            # Get content until next header
            section_content = self._get_section_content(header)
            log_info(f"Section has {len(section_content)} content elements")
            
            if section_content:
                # Try to parse date info from header for fallback
                fallback_span = self._parse_header_date(header_text)
                log_info(f"Fallback span for header: {fallback_span}")
                
                hierarchy = {
                    'type': 'section',
                    'header': header_text,
                    'content': section_content,
                    'is_bc_context': 'BCE' in header_text or 'BC' in header_text,
                    'fallback_span': fallback_span
                }
                hierarchies.append(hierarchy)
                log_info(f"Created hierarchy: type={hierarchy['type']}, is_bc_context={hierarchy['is_bc_context']}")

        log_info(f"MainTimelinePageStrategy returning {len(hierarchies)} hierarchies")
        return PageData(url=url, title=title_text, hierarchies=hierarchies)

    def _is_timeline_section(self, header_text: str) -> bool:
        """Check if this header represents a timeline section."""
        # Skip references, external links, etc.
        skip_patterns = [
            r'\bReferences\b', r'\bExternal links\b', r'\bBibliography\b',
            r'\bSources\b', r'\bSee also\b', r'\bNavigation\b'
        ]
        return not any(re.search(pattern, header_text, re.IGNORECASE) for pattern in skip_patterns)

    def _get_section_content(self, header):
        """Get content that follows a header until the next header."""
        content_elements = []
        
        # Start from the element after the header
        current = header.find_next(['ul', 'ol', 'p'])
        
        while current:
            if current.name in ['h2', 'h3', 'h4']:
                break
            if current.name in ['ul', 'ol', 'p']:
                content_elements.append(current)
            current = current.find_next(['ul', 'ol', 'p', 'h2', 'h3', 'h4'])
        
        return content_elements

    def _parse_header_date(self, header_text: str):
        """Parse date information from section header for fallback use."""
        # Use span parsing to extract date info from headers like "18th century BCE"
        from span_parsing.orchestrators.parse_orchestrator_factory import ParseOrchestratorFactory
        from span_parsing.orchestrators import ParseOrchestratorTypes
        
        # Try different orchestrators
        orchestrators = [
            ParseOrchestratorFactory.get_orchestrator(ParseOrchestratorTypes.YEARS),
            ParseOrchestratorFactory.get_orchestrator(ParseOrchestratorTypes.TIME_PERIODS)
        ]
        
        for orchestrator in orchestrators:
            span = orchestrator.parse_span_from_bullet(header_text, 2024)  # year doesn't matter for centuries
            if span:
                return span
        
        return None


class CenturyTimelinePageStrategy(PageParsingStrategy):
    """Strategy for parsing century-specific timeline pages (19th, 20th, 21st century)."""

    def can_parse(self, url: str, soup) -> bool:
        """Check if this is a century timeline page."""
        return any(period in url for period in ["19th_century", "20th_century", "21st_century"])

    def parse_page(self, url: str, soup) -> Optional[PageData]:
        """Parse a century timeline page."""
        title = soup.find('h1', {'id': 'firstHeading'})
        title_text = title.get_text().strip() if title else "Century Timeline"

        # Find the main content area
        content = soup.find('div', {'id': 'mw-content-text'})
        if not content:
            return None

        # For century pages, we need to extract year headers and their associated content
        # Find all h3 headers (including those wrapped in mw-heading divs)
        hierarchies = []
        
        # Find all h3 elements, including those inside mw-heading divs
        h3_elements = []
        for h3 in content.find_all('h3', recursive=True):
            # Skip if it's inside a table of contents or other non-content areas
            if not self._is_in_content_area(h3, content):
                continue
            h3_elements.append(h3)
        
        log_info(f"Found {len(h3_elements)} h3 elements on century page")
        
        # Group h3 elements with their following ul elements
        for i, h3 in enumerate(h3_elements):
            header_text = h3.get_text().strip()
            log_info(f"Processing h3 {i}: '{header_text}'")
            
            # Stop at "See also" or similar
            if re.search(r'\bSee also\b', header_text, re.IGNORECASE):
                log_info("Stopping at 'See also' section")
                break
            
            # Find the ul that follows this h3
            year_ul = self._find_following_ul(h3)
            if year_ul:
                log_info(f"Found ul following h3 '{header_text}'")
                hierarchies.append({
                    'type': 'year_section',
                    'header': header_text,
                    'year_element': h3,
                    'content': [year_ul],
                    'century': self._extract_century(url)
                })
            else:
                log_info(f"No ul found following h3 '{header_text}'")

        # If no hierarchies were found, fall back to the old approach
        if not hierarchies:
            log_info("No year sections found, falling back to collecting all content")
            main_content = []
            elements = content.find_all(recursive=False)
            
            for element in elements:
                if element.name in ['h2', 'h3', 'h4']:
                    header_text = element.get_text().strip()
                    if re.search(r'\bSee also\b', header_text, re.IGNORECASE):
                        break
                main_content.append(element)
            
            if main_content:
                hierarchies.append({
                    'type': 'century_timeline',
                    'content': main_content,
                    'century': self._extract_century(url)
                })

        return PageData(url=url, title=title_text, hierarchies=hierarchies)

    def _is_in_content_area(self, element: Tag, content_div: Tag) -> bool:
        """Check if an element is in the main content area (not in TOC, etc.)."""
        # For now, just check that it's not in a TOC
        parent = element.parent
        while parent:
            if parent.get('class') and 'toc' in parent.get('class', []):
                return False
            if parent == content_div:
                break
            parent = parent.parent
        return True

    def _find_following_ul(self, h3_element: Tag) -> Optional[Tag]:
        """Find the ul element that follows an h3 year header."""
        # Use find_next to find the next ul element
        next_ul = h3_element.find_next('ul')
        if next_ul:
            # Check if there's another h3 between this h3 and the ul
            next_h3 = h3_element.find_next(['h2', 'h3', 'h4'])
            if next_h3 and next_ul.sourceline > next_h3.sourceline:
                # The ul comes after another header, so it's not for this h3
                return None
            return next_ul
        return None

    def _extract_century(self, url: str) -> str:
        """Extract century from URL."""
        if "19th_century" in url:
            return "19th"
        elif "20th_century" in url:
            return "20th"
        elif "21st_century" in url:
            return "21st"
        return "unknown"


class ArticlePageStrategy(PageParsingStrategy):
    """Strategy for parsing general article pages that contain timeline information."""

    def can_parse(self, url: str, soup) -> bool:
        """Check if this is a general article page."""
        # This is a fallback strategy - it can parse any Wikipedia page
        return True

    def parse_page(self, url: str, soup) -> Optional[PageData]:
        """Parse a general article page."""
        title = soup.find('h1', {'id': 'firstHeading'})
        title_text = title.get_text().strip() if title else "Article Page"

        # Find the main content area
        content = soup.find('div', {'id': 'mw-content-text'})
        if not content:
            return None

        # For article pages, treat the entire content as one hierarchy
        # But we need to stop at "See also"
        hierarchies = []

        # Collect all content until "See also"
        main_content = []
        elements = content.find_all(recursive=False)

        for element in elements:
            if element.name in ['h2', 'h3', 'h4']:
                header_text = element.get_text().strip()
                if re.search(r'\bSee also\b', header_text, re.IGNORECASE):
                    break
            main_content.append(element)

        if main_content:
            hierarchies.append({
                'type': 'article',
                'content': main_content,
                'title': title_text
            })

        return PageData(url=url, title=title_text, hierarchies=hierarchies)


class PageParsingStrategyFactory:
    """Factory for selecting appropriate page parsing strategies."""

    def __init__(self):
        """Initialize with available strategies in order of preference."""
        self.strategies = [
            CenturyTimelinePageStrategy(),  # Most specific first
            MainTimelinePageStrategy(),     # Then main timeline
            ArticlePageStrategy(),          # Fallback for any page
        ]

    def get_strategy(self, url: str, soup) -> Optional[PageParsingStrategy]:
        """Get the appropriate page parsing strategy."""
        for strategy in self.strategies:
            if strategy.can_parse(url, soup):
                return strategy
        return None