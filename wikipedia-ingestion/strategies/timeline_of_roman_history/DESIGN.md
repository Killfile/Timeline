# Phase 1 Design: TableRowDateParser & RomanEvent

**NOTE**: This design reuses the existing `SpanPrecision` class from `span_parsing/span.py` to maintain consistency with the rest of the codebase. We do NOT create a duplicate enum.

## TableRowDateParser Design

### Class Structure & Signatures

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
from span_parsing.span import SpanPrecision  # REUSE existing class

class ConfidenceLevel(Enum):
    """Represents confidence in date source.
    
    NOTE: SpanPrecision is reused from span_parsing/span.py:
    - EXACT (1000.0): Full date with day+month+year
    - APPROXIMATE (100.0): "c. YYYY" or approximate markers  
    - YEAR_ONLY (10.0): Year only
    - MONTH_ONLY (1.0): Month+year
    - SEASON_ONLY (0.25): "Summer", "Winter"
    - CIRCA (1/100): Very uncertain circa dates
    - FALLBACK (0.0): No precision available
    """
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
    precision: float                   # SpanPrecision value (EXACT, YEAR_ONLY, etc.)
    confidence: ConfidenceLevel        # Source reliability
    original_text: str                 # Original cell text (for debugging)

class TableRowDateParser:
    """Parses date cells from Wikipedia Timeline of Roman History table.
    
    Handles:
    - Year-only dates: "753BC", "27 BC", "79 AD"
    - Month+Day: "21 April", "13 January"
    - Month-only: "January", "Summer"
    - Rowspan inheritance: Year spans multiple rows
    - BC/AD transitions: Correct chronological ordering
    - Precision levels: EXACT_DATE vs MONTH_ONLY vs YEAR_ONLY
    """
    
    def __init__(self):
        """Initialize parser with regex patterns."""
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile all regex patterns for date formats.
        
        Patterns in priority order (first match wins):
        1. Full date: "13 January 27 BC" (day month year bc/ad)
        2. Month+Year: "January 44 BC" (month year)
        3. Month+Day: "21 April" (day month, year separate)
        4. Year only: "753BC", "27 BC", "79 AD"
        5. Ranges: "264–146 BC" (use start year)
        6. Approximate: "c. 1000 BC"
        7. Uncertain: "?180s BC"
        8. Seasons: "Summer", "Winter"
        """
        pass  # Implemented in Phase 2
    
    def parse_year_cell(self, year_text: str) -> ParsedDate:
        """Parse year cell to extract year and BC/AD designation.
        
        Args:
            year_text: e.g., "753BC", "27 BC", "79 AD"
        
        Returns:
            ParsedDate with year, is_bc=True/False, confidence=explicit
        
        Raises:
            ValueError: If year cannot be parsed
        """
        pass  # Implemented in Phase 2
    
    def parse_date_cell(self, date_text: str, year: int, is_bc: bool) -> ParsedDate:
        """Parse date cell to extract month/day.
        
        Combines:
        - Year from parse_year_cell()
        - Month/day from date_cell text
        
        Args:
            date_text: e.g., "21 April", "January", "Summer", ""
            year: Year value (negative if BC)
            is_bc: True if BC (year already negative)
        
        Returns:
            ParsedDate with year, month, day, precision (SpanPrecision value), confidence
        
        Edge cases:
        - Empty date_text → year_only, confidence=explicit, precision=SpanPrecision.YEAR_ONLY
        - "January" → month=1, day=None, precision=SpanPrecision.MONTH_ONLY
        - "Summer" → month=None, day=None, precision=SpanPrecision.SEASON_ONLY
        - "21 April" → month=4, day=21, precision=SpanPrecision.EXACT
        """
        pass  # Implemented in Phase 2
    
    def parse_row_pair(
        self,
        year_text: str,
        date_text: str,
        confidence_override: Optional[ConfidenceLevel] = None
    ) -> ParsedDate:
        """Parse a (year_cell, date_cell) pair as a unit.
        
        Convenience method combining parse_year_cell + parse_date_cell.
        
        Args:
            year_text: Year cell text
            date_text: Date cell text
            confidence_override: Override default confidence (for rowspan inheritance)
        
        Returns:
            Complete ParsedDate
        """
        pass  # Implemented in Phase 2
    
    def parse_with_rowspan_context(
        self,
        year_text: str,
        date_text: str,
        rowspan_context: Optional['RowspanContext'] = None
    ) -> ParsedDate:
        """Parse while tracking rowspan inheritance.
        
        Args:
            year_text: Year cell text (may be empty for inherited rows)
            date_text: Date cell text
            rowspan_context: Track inherited year across multiple rows
        
        Returns:
            ParsedDate with appropriate confidence level (explicit vs inferred)
        
        Algorithm:
        1. If year_text is not empty → parse_year_cell()
        2. If year_text is empty and rowspan_context active:
           - Use inherited year from context
           - Set confidence = inferred
           - Update context.remaining_rows -= 1
        3. Parse date_cell
        4. Return complete ParsedDate
        """
        pass  # Implemented in Phase 2
    
    @staticmethod
    def month_name_to_number(month_name: str) -> Optional[int]:
        """Convert month name to number (1-12).
        
        Args:
            month_name: e.g., "January", "Feb", "December"
        
        Returns:
            1-12 or None if not recognized
        """
        pass  # Implemented in Phase 2
    
    @staticmethod
    def determine_confidence_for_date(year: int) -> ConfidenceLevel:
        """Assign confidence level based on year and historical context.
        
        Args:
            year: Year value (negative = BC)
        
        Returns:
            ConfidenceLevel enum
        
        Rules:
        - year < -753: LEGENDARY (before Rome founded)
        - year == 0: LEGENDARY (no year 0, edge case)
        - year > -753: EXPLICIT (historical record)
        """
        pass  # Implemented in Phase 2

@dataclass
class RowspanContext:
    """Track rowspan inheritance across rows."""
    inherited_year: int
    inherited_is_bc: bool
    remaining_rows: int
    source_row_index: int                # Which row introduced this span
    
    def should_inherit(self) -> bool:
        """Check if current row should inherit year."""
        return self.remaining_rows > 0
    
    def consume_row(self) -> bool:
        """Mark row as consumed, return True if consumed."""
        if self.remaining_rows > 0:
            self.remaining_rows -= 1
            return True
        return False
```

### Regex Patterns to Implement

| Format | Pattern | Example | Notes |
|--------|---------|---------|-------|
| Full date | `(\d{1,2})\s+(\w+)\s+(\d+)\s*(BC\|AD\|BCE\|CE)?` | "13 January 27 BC" | Day, month, year |
| Month+Year | `(\w+)\s+(\d+)\s*(BC\|AD)?` | "January 44 BC" | Month name, year |
| Month+Day | `(\d{1,2})\s+(\w+)` | "21 April" | Day, month (year separate) |
| Year only | `(\d+)\s*(BC\|AD\|BCE\|CE)?` | "753BC", "79 AD" | Year ±designation |
| Range (use start) | `(\d+)–(\d+)\s*(BC\|AD)?` | "264–146 BC" | Use start_year only |
| Approximate | `c\.\s+(\d+)\s*(BC\|AD)?` | "c. 1000 BC" | Mark as APPROXIMATE |
| Uncertain | `\?(\d+s?)\s*(BC\|AD)?` | "?180s BC" | Mark as UNCERTAIN |
| Seasons | `(Summer\|Winter\|Spring\|Fall\|Autumn)` | "Summer" | SEASON_ONLY precision |

### Date Parsing Algorithm (Pseudocode)

```python
def parse_date_cell(date_text: str, year: int, is_bc: bool) -> ParsedDate:
    if not date_text.strip():
        # Empty date → year only
        return ParsedDate(
            year=year, month=None, day=None, is_bc=is_bc,
            precision=SpanPrecision.YEAR_ONLY,
            confidence=ConfidenceLevel.EXPLICIT,
            original_text=date_text
        )
    
    # Try patterns in order
    for pattern in [FULL_DATE_PATTERN, MONTH_YEAR_PATTERN, MONTH_DAY_PATTERN, ...]:
        match = pattern.search(date_text)
        if match:
            # Extract components, construct ParsedDate
            # Handle BC/AD designation if present
            # Return with appropriate precision
            break
    
    # If no pattern matched, try season pattern
    if "season" in date_text.lower():
        return ParsedDate(..., precision=SpanPrecision.SEASON_ONLY)
    
    # Fallback: invalid date
    raise ValueError(f"Cannot parse date: {date_text}")
```

### BC/AD Detection & Propagation Rules

1. **Within year cell**: "753BC", "27 BC", "79 AD"
   - Extraction: Regex captures BC/AD suffix
   - Conversion: Convert year to negative if BC
   - Example: "753 BC" → year=-753, is_bc=True

2. **Within date cell**: "13 January 27 BC"
   - Extraction: Regex captures year and BC/AD
   - Override: If date_cell has year+BC/AD, use that
   - Fallback: Use year from year_cell if not specified

3. **Rowspan propagation**: 
   - First row establishes is_bc flag
   - All inherited rows use same is_bc flag
   - Example: "27 BC" rowspan=3 → all 3 rows are 27 BC

4. **Edge case - BC to AD transition**:
   - Not expected in same rowspan
   - If detected: Log warning, use year_cell's designation

---

## RomanEvent Domain Model Design

### Field Mapping to HistoricalEvent Schema

```python
from dataclasses import dataclass
from typing import Optional
from enum import Enum

@dataclass
class RomanEvent:
    """Intermediate representation for Timeline of Roman History events.
    
    Maps to HistoricalEvent database schema with metadata.
    """
    
    # Core date fields
    start_year: int                    # Year (-ve = BC)
    end_year: int                      # Year (-ve = BC)
    start_month: Optional[int]         # 1-12 or None
    start_day: Optional[int]           # 1-31 or None
    
    # Event identification
    title: str                         # 50-70 char summary of description
    description: str                   # Full event text from Wikipedia
    
    # Quality indicators
    span_precision: float              # SpanPrecision value (EXACT, YEAR_ONLY, etc.)
    confidence: ConfidenceLevel        # explicit, inferred, legendary, etc.
    
    # Deduplication
    event_key: str                     # SHA-256(title|start_year|end_year|description)
    
    # Source metadata
    wikipedia_url: str                 # https://en.wikipedia.org/wiki/Timeline_of_Roman_history
    source_table_row: int              # Index in Wikipedia table
    rowspan_inherited: bool            # True if year inherited from parent row
    
    @classmethod
    def from_parsed_date(
        cls,
        parsed_date: ParsedDate,
        description: str,
        wikipedia_url: str,
        row_index: int,
        rowspan_inherited: bool = False
    ) -> 'RomanEvent':
        """Factory method to create RomanEvent from ParsedDate + description.
        
        Args:
            parsed_date: Result from TableRowDateParser
            description: Event description text
            wikipedia_url: Source URL
            row_index: Position in table
            rowspan_inherited: Whether year was inherited
        
        Returns:
            Fully constructed RomanEvent
        """
        pass  # Implemented in Phase 2
    
    def generate_title(self) -> str:
        """Generate title from description (first 50-70 chars).
        
        Algorithm:
        1. Strip whitespace from description
        2. If contains '.': Use text up to first sentence boundary
        3. Otherwise: Use first 50-70 chars ending at word boundary
        4. Capitalize first letter
        5. Add "..." if truncated
        
        Examples:
        - "Rome was founded by Romulus." → "Rome was founded by Romulus."
        - "Battle of Alba Longa. King of Alba Longa, Amulius, ..." → 
          "Battle of Alba Longa."
        - "Very long description..." → "Very long description text that..." (70 chars)
        
        Returns:
            Title string, max ~70 characters
        """
        pass  # Implemented in Phase 2
    
    def compute_event_key(self) -> str:
        """Compute SHA-256 event key for deduplication.
        
        Inputs to hash:
        - title (generated via generate_title)
        - start_year
        - end_year
        - description (full text)
        
        Format: "{title}|{start_year}|{end_year}|{description}"
        
        Returns:
            64-char hex string (SHA-256)
        
        Note: Uses timeline_common.event_key.compute_event_key()
        """
        pass  # Implemented in Phase 2
    
    def to_historical_event_dict(self) -> dict:
        """Convert to database insertion dict.
        
        Maps RomanEvent fields to HistoricalEvent schema:
        
        Output dict keys:
        - title: str (generated)
        - description: str (full)
        - start_year: int
        - end_year: int
        - start_month: int | None
        - start_day: int | None
        - end_month: None (not tracked for Roman history)
        - end_day: None (not tracked for Roman history)
        - is_bc_start: bool (True if start_year < 0)
        - is_bc_end: bool (True if end_year < 0)
        - event_key: str (SHA-256)
        - metadata: JSON string with:
          - span_precision: float (SpanPrecision constant value)
          - confidence: str (ConfidenceLevel enum value)
          - wikipedia_url: str
          - table_row: int
          - rowspan_inherited: bool
        
        Returns:
            dict ready for database insert
        """
        pass  # Implemented in Phase 2
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate event consistency.
        
        Checks:
        1. title is not empty
        2. start_year and end_year both set
        3. If end_year set: end_year >= start_year (chronological)
        4. start_month in 1-12 or None
        5. start_day in 1-31 or None
        6. event_key is 64-char hex string
        7. confidence is valid ConfidenceLevel
        8. span_precision is valid SpanPrecision
        
        Returns:
            (is_valid: bool, error_message: str | None)
        """
        pass  # Implemented in Phase 2
```

### Title Generation Algorithm

```
Input: "Romulus, first king of Rome, celebrates the first Roman triumph 
        after a military victory."

Algorithm:
1. Find first sentence boundary (., !, or ?)
   → "Romulus, first king of Rome, celebrates the first Roman triumph"
   
2. If sentence > 70 chars, truncate at word boundary
   → Check if ends at multiple periods/special cases
   
3. If no clear sentence: use first 70 chars ending at word boundary
   
4. Capitalize first letter, preserve rest
   
5. Add "..." if truncated (not if ends with .)

Output: "Romulus, first king of Rome, celebrates the first Roman triumph"
        (63 chars - kept full sentence as it fit in limit)
```

### Confidence Assignment Rules

| Scenario | Rule | Confidence |
|----------|------|------------|
| Explicit date in table | Table cell has date | `explicit` |
| Year inherited from rowspan | Year from parent row | `inferred` |
| Year < -753 (before Rome) | Legendary period | `legendary` |
| Date marked "c." (circa) | Approximate indicator | `approximate` |
| Date marked "?" | Uncertainty indicator | `uncertain` |
| Multiple rowspan parents | Conflicting sources (rare) | `contentious` |
| Default/fallback | Used when parsing fails | `fallback` |

### Event Key Computation

**Implementation**: Use `timeline_common.event_key.compute_event_key()`

**Inputs**:
```python
event_key = compute_event_key(
    title=self.title,              # Generated title (first 50-70 chars)
    start_year=self.start_year,    # Year (-ve if BC)
    end_year=self.end_year,        # Year
    description=self.description   # Full event text
)
```

**Example**:
```
title = "Rome was founded"
start_year = -753
end_year = -753
description = "Rome was founded by Romulus according to legend"

payload = "Rome was founded|-753|-753|Rome was founded by Romulus..."
event_key = SHA256(payload) = "abc123def456..."
```

**Purpose**:
- Deterministic deduplication across reimports
- Enables enrichment persistence (event categories, images, etc.)
- Survives table structure changes (as long as core fields unchanged)

### Phase 2 Implementation Order

1. **Phase 2.1**: TableRowDateParser implementation & unit tests
2. **Phase 2.2**: RomanEvent implementation & unit tests
3. **Phase 2.3**: Integration tests combining both components
