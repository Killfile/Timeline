"""Hierarchy parsing strategies for different content organization patterns."""

import re
from typing import List, Optional
from bs4 import BeautifulSoup, Tag

from strategies.lgbtq_history_v2.base_classes import HierarchyParsingStrategy, EventCandidate
from ingestion_common import log_info, log_error
from span_parsing.orchestrators.parse_orchestrator_factory import ParseOrchestratorFactory
from span_parsing.orchestrators import ParseOrchestratorTypes
from span_parsing.span import Span

class SimpleListHierarchyStrategy(HierarchyParsingStrategy):
    """Strategy for parsing simple list hierarchies (no nesting)."""

    def can_parse(self, hierarchy) -> bool:
        """Check if this hierarchy contains simple lists."""
        return hierarchy.get('type') in ['section', 'article']

    def parse_hierarchy(self, hierarchy) -> List[EventCandidate]:
        """Parse simple list hierarchy into event candidates."""
        log_info(f"SimpleListHierarchyStrategy parsing hierarchy: type={hierarchy.get('type')}, header='{hierarchy.get('header', '')}'")
        log_info(f"  Hierarchy keys: {list(hierarchy.keys())}")
        log_info(f"  Content elements: {len(hierarchy.get('content', []))}")
        
        candidates = []
        content = hierarchy.get('content', [])
        is_bc_context = hierarchy.get('is_bc_context', False)
        fallback_span = hierarchy.get('fallback_span')
        
        log_info(f"  is_bc_context: {is_bc_context}")
        log_info(f"  fallback_span: {fallback_span}")

        inline_orchestrator = ParseOrchestratorFactory.get_orchestrator(ParseOrchestratorTypes.INLINE_NO_FALLBACK)
        era_orchestrator = ParseOrchestratorFactory.get_orchestrator(ParseOrchestratorTypes.TIME_PERIODS)

        for i, element in enumerate(content):
            log_info(f"  Processing content element {i}: {type(element)}")
            if isinstance(element, Tag):
                # Find all list items in this element
                list_items = element.find_all('li', recursive=True)
                log_info(f"    Found {len(list_items)} list items")
                for j, li in enumerate(list_items):
                    text = li.get_text().strip()
                    log_info(f"    List item {j}: '{text[:100]}...' (len={len(text)})")
                    if text and len(text) > 10:  # Skip very short items
                        # Check if this looks like a timeline event (contains dates or BCE/CE)

                        span:Span = inline_orchestrator.parse_span_from_bullet(text, 2100)

                        has_date_pattern = span is not None
                        log_info(f"      Has date pattern: {span}")
                        if has_date_pattern:
                            candidate = EventCandidate(
                                text=text,
                                context={
                                    'hierarchy_type': 'simple_list',
                                    'is_bc_context': span.start_year_is_bc,
                                    'section_header': hierarchy.get('header', ''),
                                    'article_title': hierarchy.get('title', ''),
                                    'fallback_span': fallback_span
                                }
                            )
                            candidates.append(candidate)
                            log_info(f"      Created candidate with context: {candidate.context}")
                        else:
                            log_info("      Skipped - no date pattern")

                # Also look for paragraphs and other text-containing elements
                # that might contain timeline events
                text_elements = element.find_all(['p', 'div'], recursive=True)
                log_info(f"    Found {len(text_elements)} text elements (p/div)")
                for k, text_elem in enumerate(text_elements):
                    text = text_elem.get_text().strip()
                    log_info(f"    Text element {k}: '{text[:100]}...' (len={len(text)})")
                    # Look for text that contains years or BCE/CE indicators
                    span:Span = era_orchestrator.parse_span_from_bullet(text, 2100)
                    has_date_content = span is not None
                    
                    
                    log_info(f"      Has date content: {span}")
                    if has_date_content:
                        candidate = EventCandidate(
                            text=text,
                            context={
                                'hierarchy_type': 'simple_list',
                                'is_bc_context': span.start_year_is_bc,
                                'section_header': hierarchy.get('header', ''),
                                'article_title': hierarchy.get('title', ''),
                                'content_type': 'paragraph',
                                'fallback_span': fallback_span
                            }
                        )
                        candidates.append(candidate)
                        log_info(f"      Created paragraph candidate with context: {candidate.context}")
                    else:
                        log_info("      Skipped paragraph - no date content")

        log_info(f"SimpleListHierarchyStrategy returning {len(candidates)} candidates")
        return candidates


class NestedYearHierarchyStrategy(HierarchyParsingStrategy):
    """Strategy for parsing nested year hierarchies (year -> events)."""

    def can_parse(self, hierarchy) -> bool:
        """Check if this hierarchy contains nested year structures."""
        return hierarchy.get('type') in ['century_timeline', 'year_section']

    def parse_hierarchy(self, hierarchy) -> List[EventCandidate]:
        """Parse nested year hierarchy into event candidates."""
        hierarchy_type = hierarchy.get('type')
        log_info(f"NestedYearHierarchyStrategy parsing hierarchy: type={hierarchy_type}, century={hierarchy.get('century')}")
        
        if hierarchy_type == 'year_section':
            return self._parse_year_section(hierarchy)
        elif hierarchy_type == 'century_timeline':
            return self._parse_century_timeline(hierarchy)
        else:
            log_info(f"Unknown hierarchy type: {hierarchy_type}")
            return []

    def _parse_year_section(self, hierarchy) -> List[EventCandidate]:
        """Parse a year section with a specific year header and ul content."""
        candidates = []
        header = hierarchy.get('header', '')
        year_element = hierarchy.get('year_element')
        content = hierarchy.get('content', [])
        century = hierarchy.get('century', '')
        
        log_info(f"Parsing year section: header='{header}', content_elements={len(content)}")
        
        # Extract year from header
        year_text = self._extract_year_from_header(header)
        if not year_text:
            log_info(f"Could not extract year from header: '{header}'")
            return candidates
        
        log_info(f"Extracted year: {year_text}")
        
        # Process the ul content
        for element in content:
            if isinstance(element, Tag) and element.name == 'ul':
                log_info(f"Processing ul with {len(element.find_all('li'))} li elements")
                year_events = self._parse_year_events(element, year_text)
                candidates.extend(year_events)
                log_info(f"Added {len(year_events)} events for year {year_text}")
        
        return candidates

    def _parse_century_timeline(self, hierarchy) -> List[EventCandidate]:
        """Parse the old-style century timeline (fallback)."""
        log_info(f"  Hierarchy content elements: {len(hierarchy.get('content', []))}")
        
        candidates = []
        content = hierarchy.get('content', [])
        century = hierarchy.get('century', '')

        for i, element in enumerate(content):
            log_info(f"  Processing content element {i}: {type(element)} - {getattr(element, 'name', 'no name')}")
            if isinstance(element, Tag):
                # Look for h3 headers followed by ul elements (year -> events)
                if element.name == 'h3':
                    year_text = element.get_text().strip()
                    log_info(f"    Found h3 header: '{year_text}'")
                    if year_text.isdigit() and len(year_text) == 4:
                        log_info(f"    Valid year header: {year_text}")
                        # This is a year header, find the following ul
                        year_ul = self._find_following_ul(element)
                        if year_ul:
                            log_info(f"    Found following ul for year {year_text}")
                            # Parse events under this year
                            year_events = self._parse_year_events(year_ul, year_text)
                            candidates.extend(year_events)
                            log_info(f"    Added {len(year_events)} events for year {year_text}")
                        else:
                            log_info(f"    No following ul found for year {year_text}")
                            # No ul found, this might be a standalone year header
                            pass
                elif element.name == 'div' and element.get('class') and 'mw-heading' in element.get('class', []):
                    # Check if this div contains an h3
                    h3_inside = element.find('h3')
                    if h3_inside:
                        year_text = h3_inside.get_text().strip()
                        log_info(f"    Found h3 inside mw-heading div: '{year_text}'")
                        if year_text.isdigit() and len(year_text) == 4:
                            log_info(f"    Valid year header in div: {year_text}")
                            # This is a year header, find the following ul
                            year_ul = self._find_following_ul(h3_inside)
                            if year_ul:
                                log_info(f"    Found following ul for year {year_text}")
                                # Parse events under this year
                                year_events = self._parse_year_events(year_ul, year_text)
                                candidates.extend(year_events)
                                log_info(f"    Added {len(year_events)} events for year {year_text}")
                            else:
                                log_info(f"    No following ul found for year {year_text}")
                else:
                    log_info(f"    Element is not h3 or mw-heading div, it's {element.name}")
                    
                    # Check if there's a "See also" section in this element
                    see_also_h2 = element.find('h2', id='See_also')
                    if not see_also_h2:
                        # Try finding by text
                        for h2 in element.find_all('h2'):
                            if re.search(r'\bSee also\b', h2.get_text(), re.IGNORECASE):
                                see_also_h2 = h2
                                break
                    
                    if see_also_h2:
                        log_info(f"    Found 'See also' section in element, will exclude content after it")
                    
                    # If the element itself is a ul, process its li children
                    # Otherwise, look for ul elements within it (recursively)
                    uls_to_process = []
                    if element.name == 'ul':
                        uls_to_process.append(element)
                    else:
                        # Look for ul elements recursively, but only process top-level ones
                        # (ones that are not inside another ul)
                        all_uls = element.find_all('ul', recursive=True)
                        for ul in all_uls:
                            # Skip uls that come after "See also" section
                            if see_also_h2 and self._comes_after(ul, see_also_h2):
                                log_info(f"    Skipping ul that comes after 'See also' section")
                                continue
                            # Check if this ul is inside another ul
                            parent_ul = ul.find_parent('ul')
                            if not parent_ul or parent_ul not in all_uls:
                                uls_to_process.append(ul)
                    
                    log_info(f"    Found {len(uls_to_process)} top-level ul elements to process")
                    
                    for ul in uls_to_process:
                        # Get only direct children li elements of this ul
                        nested_lis = ul.find_all('li', recursive=False)
                        log_info(f"    Found {len(nested_lis)} li elements in this ul")

                        for j, li in enumerate(nested_lis):
                            log_info(f"      Processing li {j}: '{li.get_text()[:50]}...'")
                            # Check if this li contains a ul (nested structure)
                            nested_ul = li.find('ul', recursive=False)
                            if nested_ul:
                                log_info(f"        Found nested ul in li {j}")
                                # This is a year container with nested events
                                year_text = self._extract_year_from_li(li)
                                if year_text:
                                    log_info(f"        Extracted year {year_text} from li")
                                    # Parse nested events
                                    nested_events = self._parse_nested_events(nested_ul, year_text)
                                    candidates.extend(nested_events)
                                    log_info(f"        Added {len(nested_events)} nested events for year {year_text}")
                                else:
                                    log_info(f"        Could not extract year from li {j}")
                            else:
                                log_info(f"        No nested ul in li {j}")
                                # This is a regular list item
                                text = li.get_text().strip()
                                if text and len(text) > 10:
                                    log_info(f"        Creating regular candidate: '{text[:50]}...'")
                                    candidates.append(EventCandidate(
                                        text=text,
                                        context={
                                            'hierarchy_type': 'nested_year',
                                            'century': century,
                                            'has_nested': False
                                        }
                                    ))
                                else:
                                    log_info(f"        Skipping short text: '{text}'")

        log_info(f"NestedYearHierarchyStrategy returning {len(candidates)} candidates")
        return candidates

    def _extract_year_from_header(self, header_text: str) -> str:
        """Extract year from a header text like '1807'."""
        # The header should just be the year
        if header_text.isdigit() and len(header_text) == 4:
            return header_text
        return ""

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

    def _parse_year_events(self, ul: Tag, year: str) -> List[EventCandidate]:
        """Parse events under a year header."""
        log_info(f"_parse_year_events called with year {year}")
        candidates = []
        lis = ul.find_all('li', recursive=False)
        log_info(f"  Found {len(lis)} li elements in ul")

        for i, li in enumerate(lis):
            text = li.get_text().strip()
            log_info(f"    Processing li {i}: '{text[:100]}...'")
            if text and len(text) > 5:  # Skip very short items
                # Format as "year – event text" for parsing
                full_text = f"{year} – {text}"
                log_info(f"    Formatted as: '{full_text[:100]}...'")
                candidate = EventCandidate(
                    text=full_text,
                    context={
                        'hierarchy_type': 'nested_year',
                        'year': year,
                        'has_nested': False,
                        'is_year_event': True
                    }
                )
                candidates.append(candidate)
                log_info(f"    Created candidate with year context: {candidate.context}")
            else:
                log_info(f"    Skipping short text: '{text}'")

        log_info(f"_parse_year_events returning {len(candidates)} candidates")
        return candidates

    def _extract_year_from_li(self, li: Tag) -> str:
        """Extract year from the first line of a li element."""
        text = li.get_text()
        first_line = text.split('\n')[0].strip()

        # Try to extract 4-digit year
        import re
        year_match = re.search(r'(\d{4})', first_line)
        return year_match.group(1) if year_match else ""

    def _parse_nested_events(self, ul: Tag, year: str) -> List[EventCandidate]:
        """Parse nested events under a year."""
        candidates = []
        nested_lis = ul.find_all('li', recursive=False)

        for li in nested_lis:
            text = li.get_text().strip()
            if text and len(text) > 5:  # Skip very short items
                # Format as "year – event text" for parsing
                full_text = f"{year} – {text}"
                candidates.append(EventCandidate(
                    text=full_text,
                    context={
                        'hierarchy_type': 'nested_year',
                        'year': year,
                        'has_nested': True,
                        'is_nested_event': True
                    }
                ))

        return candidates
    
    def _comes_after(self, element1: Tag, element2: Tag) -> bool:
        """Check if element1 comes after element2 in document order."""
        # Use sourceline if available (BeautifulSoup provides this)
        if hasattr(element1, 'sourceline') and hasattr(element2, 'sourceline'):
            if element1.sourceline and element2.sourceline:
                return element1.sourceline > element2.sourceline
        
        # Fallback: check if element2 is an ancestor of element1
        if element2 in element1.parents:
            return False  # element1 is inside element2, so it doesn't come after
        
        # Check if they share a common ancestor and compare positions
        # Get all parents of both elements
        parents1 = list(element1.parents)
        parents2 = list(element2.parents)
        
        # Find common ancestor
        common_ancestor = None
        for p1 in parents1:
            if p1 in parents2:
                common_ancestor = p1
                break
        
        if common_ancestor:
            # Find which child of the common ancestor contains each element
            child1 = element1
            while child1.parent != common_ancestor:
                child1 = child1.parent
            child2 = element2
            while child2.parent != common_ancestor:
                child2 = child2.parent
            
            # Get all children of common ancestor
            children = list(common_ancestor.children)
            try:
                idx1 = children.index(child1)
                idx2 = children.index(child2)
                return idx1 > idx2
            except (ValueError, AttributeError):
                pass
        
        # If we can't determine order, assume it doesn't come after
        return False


class HierarchyParsingStrategyFactory:
    """Factory for selecting appropriate hierarchy parsing strategies."""

    def __init__(self):
        """Initialize with available strategies."""
        self.strategies = [
            SimpleListHierarchyStrategy(),
            NestedYearHierarchyStrategy(),
        ]

    def get_strategy(self, hierarchy) -> HierarchyParsingStrategy:
        """Get the appropriate hierarchy parsing strategy."""
        for strategy in self.strategies:
            if strategy.can_parse(hierarchy):
                return strategy
        return None