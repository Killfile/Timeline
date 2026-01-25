"""Event parsing strategies for different event text formats."""

import re
from typing import Optional

from strategies.lgbtq_history_v2.base_classes import EventParsingStrategy, EventCandidate
from historical_event import HistoricalEvent
from ingestion_common import log_info, log_error
from span_parsing.orchestrators.parse_orchestrator_factory import ParseOrchestratorFactory
from span_parsing.orchestrators import ParseOrchestratorTypes

class SimpleDateEventStrategy(EventParsingStrategy):
    """Strategy for parsing simple 'date – description' events."""

    DASH = r'[\-–—]'  # Matches various dash/hyphen characters

    # Patterns for matching date ranges at the beginning of event text
    DATE_PATTERNS = [
        # BCE/CE ranges with circa
        re.compile(r'^(c\. \d{4} BCE ' + DASH + r' c\. \d{4} BCE)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(c\. \d{4} CE ' + DASH + r' c\. \d{4} CE)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(c\. \d{4} BC ' + DASH + r' c\. \d{4} BC)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(c\. \d{4} AD ' + DASH + r' c\. \d{4} AD)\s' + DASH + r'\s(.*)$'),
        
        # BCE/CE ranges without circa
        re.compile(r'^(\d{4} BCE ' + DASH + r' \d{4} BCE)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(\d{4} CE ' + DASH + r' \d{4} CE)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(\d{4} BC ' + DASH + r' \d{4} BC)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(\d{4} AD ' + DASH + r' \d{4} AD)\s' + DASH + r'\s(.*)$'),
        
        # Single years with circa
        re.compile(r'^(c\. \d{4} BCE)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(c\. \d{4} CE)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(c\. \d{4} BC)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(c\. \d{4} AD)\s' + DASH + r'\s(.*)$'),
        
        # Single years without circa
        re.compile(r'^(\d{4} BCE)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(\d{4} CE)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(\d{4} BC)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(\d{4} AD)\s' + DASH + r'\s(.*)$'),
        
        
        # Century references
        re.compile(r'^(\d{1,2}(?:st|nd|rd|th) century BCE)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(\d{1,2}(?:st|nd|rd|th) century CE)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(\d{1,2}(?:st|nd|rd|th) century BC)\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(\d{1,2}(?:st|nd|rd|th) century AD)\s' + DASH + r'\s(.*)$'),

        # Bare year values
        re.compile(r'^(\d{4})\s' + DASH + r'\s(.*)$'),
        re.compile(r'^(\d{3})\s' + DASH + r'\s(.*)$'),


    ]

    def can_parse(self, candidate: EventCandidate) -> bool:
        """Check if this looks like a simple date event using ParseOrchestrators."""
        text = candidate.text.strip()
        log_info(f"SimpleDateEventStrategy.can_parse checking: {repr(text[:100])}")
        
        # Try parsing the entire text with ParseOrchestrators
        date_info = self._parse_date_with_span_parsing(text)
        if date_info:
            log_info("  ParseOrchestrator successfully parsed date")
            return True
        
        log_info("  No date found by ParseOrchestrator")
        return False

    def parse_event(self, candidate: EventCandidate, source_url: str) -> Optional[HistoricalEvent]:
        """Parse simple date event using pattern matching and span parsing."""
        text = candidate.text.strip()
        
        # Try each pattern to find date part and description
        date_text = text
        description = None
        
        
        date_info = self._parse_date_with_span_parsing(date_text)
        if not date_info:
            return None

        # Clean up description (remove citations)
        description = date_text

        # Extract title from description
        title = self._extract_title(description)
        if not title:
            return None

        return HistoricalEvent(
            title=title,
            start_year=date_info['start_year'],
            end_year=date_info['end_year'],
            is_bc_start=date_info['is_bc_start'],
            is_bc_end=date_info['is_bc_end'],
            precision=1.0,  # Assume exact year for now
            weight=1,
            url=source_url,
            span_match_notes=date_info['match_type'],
        )

    def _parse_date_with_span_parsing(self, date_text: str) -> Optional[dict]:
        """Parse date text using the span_parsing library."""
        
        
        # Try different orchestrators
        orchestrators = [
            ParseOrchestratorFactory.get_orchestrator(ParseOrchestratorTypes.INLINE_NO_FALLBACK),
            # ParseOrchestratorFactory.get_orchestrator(ParseOrchestratorTypes.TIME_PERIODS)
        ]
        
        for orchestrator in orchestrators:
            span = orchestrator.parse_span_from_bullet(date_text, 2100)  # year context doesn't matter
            if span:
                return {
                    'start_year': span.start_year,
                    'end_year': span.end_year,
                    'is_bc_start': span.start_year_is_bc,
                    'is_bc_end': span.end_year_is_bc,
                    'match_type': span.match_type,
                }
            else:
                log_info(f"  Orchestrator {orchestrator.__class__.__name__} did not find a span in '{date_text}'")
        
        return None

    def _extract_title(self, description: str) -> str:
        """Extract a concise title from description."""
        if not description:
            return ""

        # Take first sentence or first clause
        sentence_end = description.find('.')
        if sentence_end > 0:
            title = description[:sentence_end + 1].strip()
        else:
            # Take first clause (up to comma or semicolon)
            clause_end = min(
                description.find(',') if description.find(',') > 0 else len(description),
                description.find(';') if description.find(';') > 0 else len(description)
            )
            title = description[:clause_end].strip()

        return title if len(title) > 5 else description[:50].strip()

    def _parse_date(self, date_text: str, is_bc_context: bool) -> dict:
        """Parse date text into year range and BC/AD info."""
        # Check for BCE/BC indicators in the entire text
        is_bc = is_bc_context or bool(re.search(r'\b(BCE|BC)\b', date_text, re.IGNORECASE))
        
        # Check for date ranges first (e.g., "2900 BCE - 2500 BCE", "c. 1775 BCE – c. 1761 BCE")
        range_match = re.search(r'(?:c\.|circa)?\s*(\d{1,4})\s*(?:BCE|BC)?\s*[-–]\s*(?:c\.|circa)?\s*(\d{1,4})\s*(?:BCE|BC)?', date_text, re.IGNORECASE)
        if range_match:
            start_year = int(range_match.group(1))
            end_year = int(range_match.group(2))
            # Check for BC indicators in each part
            start_is_bc = is_bc_context or bool(re.search(r'\b(BCE|BC)\b', range_match.group(0)[:range_match.start(2)], re.IGNORECASE))
            end_is_bc = is_bc_context or bool(re.search(r'\b(BCE|BC)\b', range_match.group(0)[range_match.start(2):], re.IGNORECASE))
            return {
                'start_year': start_year,
                'end_year': end_year,
                'is_bc_start': start_is_bc,
                'is_bc_end': end_is_bc
            }
        
        # Check for century references
        century_match = re.search(r'(\d+)(?:st|nd|rd|th)\s+century', date_text, re.IGNORECASE)
        if century_match:
            century = int(century_match.group(1))
            # Convert century to year range (1st century = years 1-100, etc.)
            if is_bc:
                # For BC centuries, the range is (century*100) BCE - ((century-1)*100 + 1) BCE
                start_year = century * 100
                end_year = (century - 1) * 100 + 1
            else:
                # For AD centuries, use the century range
                start_year = (century - 1) * 100 + 1
                end_year = century * 100
            return {
                'start_year': start_year,
                'end_year': end_year,
                'is_bc_start': is_bc,
                'is_bc_end': is_bc
            }
        
        # Extract single year number (4 digits preferred, then 1-3 digits)
        year_match = re.search(r'(\d{4})', date_text)
        if year_match:
            year = int(year_match.group(1))
        else:
            # Try to extract other year formats (1-3 digits)
            year_match = re.search(r'(\d{1,3})', date_text)
            year = int(year_match.group(1)) if year_match else 0

        return {
            'start_year': year,
            'end_year': year,
            'is_bc_start': is_bc,
            'is_bc_end': is_bc
        }


class UndatedEventStrategy(SimpleDateEventStrategy):
    """Strategy for parsing events that don't have explicit dates but can infer them from context."""

    def can_parse(self, candidate: EventCandidate) -> bool:
        """Check if this is an undated event that we can parse using context."""
        text = candidate.text.strip()
        log_info(f"UndatedEventStrategy.can_parse checking: '{text[:100]}...'")
        
        if not text or len(text) < 10:
            log_info(f"  REJECTED: Text too short ({len(text)} chars)")
            return False

        # Skip obvious non-events
        skip_indicators = [
            'see also', 'references', 'external links', 'bibliography',
            'sources', 'navigation', 'categories', 'lgbtq portal',
            'lgbt social movements', 'timeline of', 'history of',
            '^ ',  # Lines starting with spaces are often continuations
        ]

        text_lower = text.lower()
        for indicator in skip_indicators:
            if indicator in text_lower:
                log_info(f"  REJECTED: Contains skip indicator '{indicator}'")
                return False

        # Check if we have context that can provide a date
        context = candidate.context
        log_info(f"  Context keys: {list(context.keys())}")
        
        if context.get('article_title') and '19th' in context.get('article_title', ''):
            log_info(f"  ACCEPTED: Article title contains '19th': {context.get('article_title')}")
            return True
        if context.get('century') in ['19th', '20th', '21st']:
            log_info(f"  ACCEPTED: Century context: {context.get('century')}")
            return True

        # For main timeline, check if text contains date information
        if (re.search(r'\b\d{1,4}\s*(BC|AD|BCE|CE)\b', text, re.IGNORECASE) or
            re.search(r'\bcirca\b', text, re.IGNORECASE) or
            re.search(r'\b\d{1,4}(st|nd|rd|th)\s+century\b', text, re.IGNORECASE) or
            re.search(r'\b\d{4}\b', text)):
            log_info("  ACCEPTED: Text contains date-like patterns")
            return True

        log_info("  REJECTED: No date context or patterns found")
        return False

    def parse_event(self, candidate: EventCandidate, source_url: str) -> Optional[HistoricalEvent]:
        """Parse undated event using context."""
        text = candidate.text.strip()
        context = candidate.context


        date_info = self._infer_date_from_context(context)

        # Clean up text (remove citations)
        text = re.sub(r'\[\d+\]', '', text).strip()

        # Extract title
        title = self._extract_title(text)
        if not title:
            return None

        return HistoricalEvent(
            title=title,
            start_year=date_info['start_year'],
            end_year=date_info['end_year'],
            is_bc_start=date_info['is_bc_start'],
            is_bc_end=date_info['is_bc_end'],
            precision=0.1,  # Low precision since date is inferred
            weight=1,
            url=source_url,
            span_match_notes=f"Parsed undated event from {context.get('hierarchy_type', 'unknown')} hierarchy, inferred date from context",
            description=text,
            category="LGBTQ History"
        )

    def _extract_title(self, text: str) -> str:
        """Extract title from undated event text."""
        if not text:
            return ""

        # Try to extract the first complete sentence
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        if sentences and len(sentences[0]) > 10:
            title = sentences[0].strip()
            # Clean up common issues
            title = re.sub(r'^\s*[-•]\s*', '', title)  # Remove leading bullets
            return title

        # Fallback: take first meaningful clause
        words = text.split()
        if len(words) > 3:
            # Take first 15-20 words as title, but try to end at a reasonable point
            title_words = words[:min(15, len(words))]
            title = ' '.join(title_words)
            
            # Try to end at a comma, semicolon, or reasonable break
            for punct in [',', ';', ' and ', ' or ', ' but ', ' which ', ' that ']:
                if punct in title:
                    title = title.split(punct)[0] + punct.rstrip()
                    break
            
            if title[-1] not in '.!':
                title += '.'
            return title

        return text[:80].strip()

    def _try_extract_date_from_text(self, text: str) -> Optional[dict]:
        """Try to extract a date from the text itself."""
        # Use the same date parsing logic as the main strategy
        date_info = self._parse_date(text, False)  # is_bc_context=False for now
        
        # If we got a valid date (not 0), return it
        if date_info['start_year'] != 0:
            return date_info
        
        return None

    def _infer_date_from_context(self, context: dict) -> dict:
        """Infer date from context information."""
        # Check article title for century
        article_title = context.get('article_title', '')
        if '19th' in article_title:
            # For 19th century, try to extract more specific dates from the text
            # Default to mid-century if we can't be more specific
            return {'start_year': 1801, 'end_year': 1900, 'is_bc_start': False, 'is_bc_end': False}
        elif '20th' in article_title:
            return {'start_year': 1901, 'end_year': 2000, 'is_bc_start': False, 'is_bc_end': False}
        elif '21st' in article_title:
            return {'start_year': 2001, 'end_year': 2026, 'is_bc_start': False, 'is_bc_end': False}

        # Check century from hierarchy
        century = context.get('century')
        if century == '19th':
            return {'start_year': 1801, 'end_year': 1900, 'is_bc_start': False, 'is_bc_end': False}
        elif century == '20th':
            return {'start_year': 1901, 'end_year': 2000, 'is_bc_start': False, 'is_bc_end': False}
        elif century == '21st':
            return {'start_year': 2001, 'end_year': 2026, 'is_bc_start': False, 'is_bc_end': False}

        # Default fallback
        return {'start_year': 1900, 'end_year': 1900, 'is_bc_start': False, 'is_bc_end': False}


class MainArticleEventStrategy(EventParsingStrategy):
    """Strategy for parsing 'Main article:' entries."""

    MAIN_ARTICLE_PATTERN = re.compile(r'Main article:\s*(.+)', re.IGNORECASE)

    def can_parse(self, candidate: EventCandidate) -> bool:
        """Check if this is a main article entry."""
        return self.MAIN_ARTICLE_PATTERN.search(candidate.text)

    def parse_event(self, candidate: EventCandidate, source_url: str) -> Optional[HistoricalEvent]:
        """Parse main article entry - this is just a reference, not an event."""
        # Main article entries are references to other pages, not events themselves
        # We'll handle these at the page level, not as individual events
        return None


class ColonEndingHeaderStrategy(EventParsingStrategy):
    """Strategy for parsing entries that end with ':' (headers)."""

    COLON_PATTERN = re.compile(r'^(.+?):\s*$')

    def can_parse(self, candidate: EventCandidate) -> bool:
        """Check if this ends with ':'."""
        text_no_citations = re.sub(r'\[\d+\]', '', candidate.text.strip())
        ends_with_colon = text_no_citations.rstrip().endswith(':')
        is_short = len(text_no_citations) < 50
        return ends_with_colon and is_short

    def parse_event(self, candidate: EventCandidate, source_url: str) -> Optional[HistoricalEvent]:
        """Parse colon-ending entry - this is typically a header, not an event."""
        # Colon-ending entries are usually section headers or categories
        # They don't represent individual events
        return None


class EventParsingStrategyFactory:
    """Factory for selecting appropriate event parsing strategies."""

    def __init__(self):
        """Initialize with available strategies in order of preference."""
        self.strategies = [
            MainArticleEventStrategy(),  # Check for main articles first
            ColonEndingHeaderStrategy(),  # Then colon-ending entries
            SimpleDateEventStrategy(),   # Then simple date entries
            UndatedEventStrategy(),      # Finally undated entries with context
        ]

    def get_strategy(self, candidate: EventCandidate) -> Optional[EventParsingStrategy]:
        """Get the appropriate event parsing strategy."""
        log_info(f"Selecting strategy for candidate: '{candidate.text[:100]}...'")
        log_info(f"  Context: {candidate.context}")
        
        for strategy in self.strategies:
            can_parse = strategy.can_parse(candidate)
            log_info(f"  Checking {strategy.__class__.__name__}: {'YES' if can_parse else 'NO'}")
            if can_parse:
                log_info(f"  Selected strategy: {strategy.__class__.__name__}")
                return strategy
        
        log_info("  No strategy found - candidate will be skipped")
        return None