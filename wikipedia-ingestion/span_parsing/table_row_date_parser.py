"""Table Row Date Parser for Timeline of Roman History

Parses date cells from Wikipedia Timeline of Roman History table.

Handles:
- Year-only dates: "753BC", "27 BC", "79 AD"
- Month+Day: "21 April", "13 January"
- Month-only: "January", "Summer"
- Rowspan inheritance: Year spans multiple rows
- BC/AD transitions: Correct chronological ordering
- Precision levels: EXACT vs MONTH_ONLY vs YEAR_ONLY via SpanPrecision
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum
import re
from span_parsing.span import SpanPrecision


class ConfidenceLevel(Enum):
    """Represents confidence in date source."""
    EXPLICIT = "explicit"              # Explicitly stated in table
    INFERRED = "inferred"              # Inherited via rowspan
    LEGENDARY = "legendary"            # Pre-753 BC (mythological)
    APPROXIMATE = "approximate"        # "c." or range markers
    UNCERTAIN = "uncertain"            # "?" or conflict markers
    CONTENTIOUS = "contentious"        # Multiple sources conflict
    FALLBACK = "fallback"              # Default/guessed


@dataclass
class ParsedDate:
    """Result of parsing a date cell."""
    year: int                          # Year (-ve = BC)
    month: Optional[int]               # 1-12 or None
    day: Optional[int]                 # 1-31 or None
    is_bc: bool                        # True if BC (year already negative)
    precision: float                   # SpanPrecision value
    confidence: ConfidenceLevel        # Source reliability
    original_text: str                 # Original cell text (for debugging)


@dataclass
class RowspanContext:
    """Track rowspan inheritance across rows."""
    inherited_year: int
    inherited_is_bc: bool
    remaining_rows: int
    source_row_index: int              # Which row introduced this span
    
    def should_inherit(self) -> bool:
        """Check if current row should inherit year."""
        return self.remaining_rows > 0
    
    def consume_row(self) -> bool:
        """Mark row as consumed, return True if consumed."""
        if self.remaining_rows > 0:
            self.remaining_rows -= 1
            return True
        return False


class TableRowDateParser:
    """Parses date cells from Wikipedia Timeline of Roman History table."""
    
    # Month name mappings
    MONTH_NAMES = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    }
    
    SEASON_NAMES = {'spring', 'summer', 'fall', 'autumn', 'winter'}
    
    def __init__(self):
        """Initialize parser with regex patterns."""
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile all regex patterns for date formats."""
        # Full date: "13 January 27 BC" (day month year bc/ad)
        self.full_date_pattern = re.compile(
            r'^(?:(\d{1,2})\s+)?(\w+)\s+(\d+)\s*(BC|AD|BCE|CE)?$',
            re.IGNORECASE
        )
        
        # Year with designation: "753BC", "27 BC", "79 AD"
        self.year_pattern = re.compile(
            r'^(\d+)\s*(BC|AD|BCE|CE)?$',
            re.IGNORECASE
        )
        
        # Approximate date: "c. 1000 BC"
        self.approx_pattern = re.compile(
            r'^c\.?\s*(\d+)\s*(BC|AD|BCE|CE)?$',
            re.IGNORECASE
        )
        
        # Uncertain date: "?180s BC"
        self.uncertain_pattern = re.compile(
            r'^\?(\d+s?)\s*(BC|AD|BCE|CE)?$',
            re.IGNORECASE
        )
        
        # Range: "264–146 BC" (use start year only)
        self.range_pattern = re.compile(
            r'^(\d+)–(\d+)\s*(BC|AD|BCE|CE)?$',
            re.IGNORECASE
        )
    
    def parse_year_cell(self, year_text: str) -> ParsedDate:
        """Parse year cell to extract year and BC/AD designation.
        
        Args:
            year_text: e.g., "753BC", "27 BC", "79 AD"
        
        Returns:
            ParsedDate with year, is_bc, confidence=explicit
        
        Raises:
            ValueError: If year cannot be parsed
        """
        if not year_text or not year_text.strip():
            raise ValueError("Year cell cannot be empty")
        
        year_text = year_text.strip()

        # Normalize prefix designations like "AD 14" -> "14 AD"
        prefix_match = re.match(r'^(AD|BC|BCE|CE)\s+(\d+)$', year_text, re.IGNORECASE)
        if prefix_match:
            designation = prefix_match.group(1)
            year_text = f"{prefix_match.group(2)} {designation}"
        
        # Try range pattern first (use start year)
        match = self.range_pattern.match(year_text)
        if match:
            year = int(match.group(1))
            designation = match.group(3) or ""
            is_bc = designation.upper() in ('BC', 'BCE')
            if is_bc:
                year = -year
            confidence = (ConfidenceLevel.LEGENDARY 
                         if year <= -753 else ConfidenceLevel.EXPLICIT)
            return ParsedDate(
                year=year, month=None, day=None, is_bc=is_bc,
                precision=SpanPrecision.YEAR_ONLY,
                confidence=confidence,
                original_text=year_text
            )
        
        # Try year pattern
        match = self.year_pattern.match(year_text)
        if match:
            year = int(match.group(1))
            designation = match.group(2) or ""
            is_bc = designation.upper() in ('BC', 'BCE')
            if is_bc:
                year = -year
            
            # Check if legendary (753 BC and before, or at year 0)
            confidence = (ConfidenceLevel.LEGENDARY 
                         if year <= -753 or year == 0 else ConfidenceLevel.EXPLICIT)
            
            return ParsedDate(
                year=year, month=None, day=None, is_bc=is_bc,
                precision=SpanPrecision.YEAR_ONLY,
                confidence=confidence,
                original_text=year_text
            )
        
        raise ValueError(f"Cannot parse year: {year_text}")
    
    def parse_date_cell(self, date_text: str, year: int, is_bc: bool) -> ParsedDate:
        """Parse date cell to extract month/day.
        
        Args:
            date_text: e.g., "21 April", "January", "Summer", ""
            year: Year value (negative if BC)
            is_bc: True if BC
        
        Returns:
            ParsedDate with year, month, day, precision, confidence
        """
        if not date_text or not date_text.strip():
            # Empty date → year only
            return ParsedDate(
                year=year, month=None, day=None, is_bc=is_bc,
                precision=SpanPrecision.YEAR_ONLY,
                confidence=ConfidenceLevel.EXPLICIT,
                original_text=date_text
            )
        
        date_text = date_text.strip()
        
        # Check for season
        date_lower = date_text.lower()
        if date_lower in self.SEASON_NAMES:
            return ParsedDate(
                year=year, month=None, day=None, is_bc=is_bc,
                precision=SpanPrecision.SEASON_ONLY,
                confidence=ConfidenceLevel.EXPLICIT,
                original_text=date_text
            )
        
        # Try full date pattern (day month [year] [BC/AD])
        match = self.full_date_pattern.match(date_text)
        if match:
            day = int(match.group(1)) if match.group(1) else None
            month_str = match.group(2)
            year_in_cell = int(match.group(3)) if match.group(3) else year
            designation = match.group(4) or ""
            
            month = self.month_name_to_number(month_str)
            if not month:
                raise ValueError(f"Cannot parse month: {month_str}")
            
            # If year is in cell, use it with BC/AD from cell
            if match.group(3):
                is_bc_from_cell = designation.upper() in ('BC', 'BCE')
                if is_bc_from_cell:
                    year_in_cell = -year_in_cell
                year = year_in_cell
                is_bc = is_bc_from_cell
            
            precision = (SpanPrecision.EXACT if day 
                        else SpanPrecision.MONTH_ONLY)
            
            return ParsedDate(
                year=year, month=month, day=day, is_bc=is_bc,
                precision=precision,
                confidence=ConfidenceLevel.EXPLICIT,
                original_text=date_text
            )
        
        # Try approximate pattern
        match = self.approx_pattern.match(date_text)
        if match:
            year_approx = int(match.group(1))
            designation = match.group(2) or ""
            is_bc_approx = designation.upper() in ('BC', 'BCE')
            if is_bc_approx:
                year_approx = -year_approx
            
            return ParsedDate(
                year=year_approx, month=None, day=None, is_bc=is_bc_approx,
                precision=SpanPrecision.APPROXIMATE,
                confidence=ConfidenceLevel.APPROXIMATE,
                original_text=date_text
            )
        
        # Try uncertain pattern
        match = self.uncertain_pattern.match(date_text)
        if match:
            year_uncertain = int(match.group(1).rstrip('s'))
            designation = match.group(2) or ""
            is_bc_uncertain = designation.upper() in ('BC', 'BCE')
            if is_bc_uncertain:
                year_uncertain = -year_uncertain
            
            return ParsedDate(
                year=year_uncertain, month=None, day=None, is_bc=is_bc_uncertain,
                precision=SpanPrecision.APPROXIMATE,
                confidence=ConfidenceLevel.UNCERTAIN,
                original_text=date_text
            )
        
        # Try simple month name
        month = self.month_name_to_number(date_text)
        if month:
            return ParsedDate(
                year=year, month=month, day=None, is_bc=is_bc,
                precision=SpanPrecision.MONTH_ONLY,
                confidence=ConfidenceLevel.EXPLICIT,
                original_text=date_text
            )

        # Try month + day pattern (e.g., "April 21")
        words = date_text.split()
        if len(words) >= 2:
            month = self.month_name_to_number(words[0])
            if month:
                try:
                    day = int(words[1])
                    if 1 <= day <= 31:
                        return ParsedDate(
                            year=year, month=month, day=day, is_bc=is_bc,
                            precision=SpanPrecision.EXACT,
                            confidence=ConfidenceLevel.EXPLICIT,
                            original_text=date_text
                        )
                except ValueError:
                    # If the second token is not an integer day, this pattern does not match;
                    # fall through so that other parsing strategies (e.g., "21 April") can run.
                    pass
        
        # Try day + month pattern separately (e.g., "21 April")
        # Look for pattern: number followed by month name
        words = date_text.split()
        if len(words) >= 2:
            try:
                day = int(words[0])
                if 1 <= day <= 31:
                    month = self.month_name_to_number(words[1])
                    if month:
                        return ParsedDate(
                            year=year, month=month, day=day, is_bc=is_bc,
                            precision=SpanPrecision.EXACT,
                            confidence=ConfidenceLevel.EXPLICIT,
                            original_text=date_text
                        )
            except (ValueError, IndexError):
                pass
        
        # If all fails, treat as year-only with original text
        return ParsedDate(
            year=year, month=None, day=None, is_bc=is_bc,
            precision=SpanPrecision.YEAR_ONLY,
            confidence=ConfidenceLevel.FALLBACK,
            original_text=date_text
        )
    
    def parse_row_pair(
        self,
        year_text: str,
        date_text: str,
        confidence_override: Optional[ConfidenceLevel] = None
    ) -> ParsedDate:
        """Parse a (year_cell, date_cell) pair as a unit.
        
        Args:
            year_text: Year cell text
            date_text: Date cell text
            confidence_override: Override default confidence
        
        Returns:
            Complete ParsedDate
        """
        parsed_year = self.parse_year_cell(year_text)
        parsed_date = self.parse_date_cell(date_text, parsed_year.year, parsed_year.is_bc)
        
        # Merge: use date's month/day if present, use year from year cell
        result = ParsedDate(
            year=parsed_year.year,
            month=parsed_date.month,
            day=parsed_date.day,
            is_bc=parsed_year.is_bc,
            precision=parsed_date.precision,
            confidence=parsed_date.confidence,
            original_text=f"{year_text} | {date_text}"
        )

        # Preserve legendary confidence from year parsing
        if parsed_year.confidence == ConfidenceLevel.LEGENDARY:
            result.confidence = ConfidenceLevel.LEGENDARY
        
        # Apply confidence override if provided
        if confidence_override:
            result.confidence = confidence_override
        
        return result
    
    def parse_with_rowspan_context(
        self,
        year_text: str,
        date_text: str,
        rowspan_context: Optional[RowspanContext] = None
    ) -> ParsedDate:
        """Parse while tracking rowspan inheritance.
        
        Args:
            year_text: Year cell text (may be empty for inherited rows)
            date_text: Date cell text
            rowspan_context: Track inherited year across multiple rows
        
        Returns:
            ParsedDate with appropriate confidence level
        """
        if year_text and year_text.strip():
            # Explicit year in this row
            parsed = self.parse_year_cell(year_text)
            return self.parse_date_cell(date_text, parsed.year, parsed.is_bc)
        
        # No explicit year - check for inheritance
        if rowspan_context:
            if rowspan_context.should_inherit():
                # Still have rows to consume
                rowspan_context.consume_row()
            
            # Use inherited year regardless of whether we're still consuming
            parsed_date = self.parse_date_cell(
                date_text,
                rowspan_context.inherited_year,
                rowspan_context.inherited_is_bc
            )
            # Override confidence for inherited dates
            parsed_date.confidence = ConfidenceLevel.INFERRED
            return parsed_date
        
        # No year at all - fallback
        raise ValueError("Cannot parse: no year provided and no rowspan context")
    
    @staticmethod
    def month_name_to_number(month_name: str) -> Optional[int]:
        """Convert month name to number (1-12).
        
        Args:
            month_name: e.g., "January", "Feb", "December"
        
        Returns:
            1-12 or None if not recognized
        """
        if not month_name:
            return None
        return TableRowDateParser.MONTH_NAMES.get(month_name.lower())
    
    @staticmethod
    def determine_confidence_for_date(year: int) -> ConfidenceLevel:
        """Assign confidence level based on year and historical context.
        
        Args:
            year: Year value (negative = BC)
        
        Returns:
            ConfidenceLevel enum
        """
        # Legendary: 753 BC and before (year <= -753) or year 0 (doesn't exist)
        if year <= -753 or year == 0:
            return ConfidenceLevel.LEGENDARY
        return ConfidenceLevel.EXPLICIT
