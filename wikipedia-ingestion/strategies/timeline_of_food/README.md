# Timeline of Food Ingestion Strategy

Extracts and parses historical food events from the Wikipedia "Timeline of Food" article, supporting diverse date formats and hierarchical context.

## Features

### Date Format Support

The strategy handles 9+ date format patterns:

- **Explicit Years**: `1847`, `2020`
- **Year Ranges**: `1500–1600`, `8000–5000 BCE`
- **Decades**: `1990s` → 1990-1999, `1800s` → 1800-1809
- **Centuries**: `19th century` → 1801-1900
- **Century Ranges**: `15th-17th centuries` → 1401-1700
- **BC/BCE Notation**: `2500–1500 BCE`, `8000 BCE`
- **Approximate Dates**: `~1450`, `circa 1516` (with approximate flag)
- **Prehistoric Dates**: `250,000 years ago` (anchored to ingestion run year)
- **Embedded Dates**: Extract from descriptions like "(9600 BCE)" or "between 4000 and 3000 BCE"

### Hierarchical Section Context

Events inherit date ranges from section headers when no explicit date is found:

```
## 8000–5000 BCE
- Early grain cultivation (inherits 8000-5000 BCE range)
- Archaeological evidence (inherits 8000-5000 BCE range)
```

### Content Extraction

**From Bullet Points**:
```html
<ul>
<li><b>1847</b> – One of America's first candy-making machines invented...</li>
</ul>
```

**From Tables**:
```html
<table>
<tr>
<td>1847</td>
<td>First candy-making machine invented...</td>
</tr>
</table>
```

Tables use the first column (date) with description from subsequent columns.

### Confidence Levels

Events are marked with confidence based on how the date was determined:

- **explicit**: Direct date found (year, range, century, decade)
- **approximate**: Date marked with `~` or `circa` prefix
- **inferred**: Date inherited from section header context
- **contentious**: Date marked as disputed/uncertain
- **fallback**: Date inferred from distant section context

### BC/AD Handling

- **Negative Years**: BC dates stored as negative (e.g., -8000 = 8000 BC)
- **BC Flags**: `is_bc_start` and `is_bc_end` set for BC dates
- **Year 0 Validation**: Enforces no year 0 rule (1 BC → 1 AD)
- **Range Validation**: Correctly handles BC ranges (8000 BC → 5000 BC)

### Ancient Date Handling

Dates >10,000 BC receive special treatment:

- **Precision Reduction**: Multiplied by 0.5 (minimum 0.1)
- **Parsing Notes**: Documents the precision adjustment
- **Rationale**: Reflects archaeological uncertainty for very ancient dates

## Implementation Structure

```
strategies/timeline_of_food/
├── food_event.py                 # FoodEvent dataclass with validation
├── hierarchical_strategies.py     # TextSection parsing from HTML
├── date_extraction_strategies.py  # EventParser for bullet/table extraction
├── timeline_of_food_strategy.py   # Main ingestion strategy
├── tests/
│   ├── test_food_event.py        # FoodEvent tests
│   ├── test_hierarchical_strategies.py
│   ├── test_date_extraction_strategies.py
│   ├── test_user_story_3.py      # BC/AD, embedded dates, ancient dates
│   ├── test_timeline_of_food_strategy.py
│   └── fixtures/
│       ├── sample_html.py        # Real Wikipedia HTML samples
│       └── expected_events.json   # Test case expectations
├── tools/
│   ├── integration_validation.py  # Verify 3,500+ events, >95% success
│   └── performance_validation.py  # Measure fetch/parse/load time
└── README.md (this file)
```

## Usage

### Running the Ingestion Strategy

```bash
python ingest_wikipedia.py timeline_of_food
```

This will:
1. Fetch the Wikipedia article from HTTP cache or network
2. Parse sections and extract events
3. Generate JSON artifact file
4. Load events into database

### Running Integration Validation

Verify that 3,500+ events are extracted with >95% date parsing success:

```bash
python wikipedia-ingestion/strategies/timeline_of_food/tools/integration_validation.py
```

Expected output:
```
Check 1: Event count validation
  Extracted: 3,500+ events
  Target: 3,500+ events
  Result: ✓ PASS

Check 2: Date parsing success rate
  Success rate: >95%
  Target: >95%
  Result: ✓ PASS

Check 3: Date format diversity
  Format types found: 8+
  Result: ✓ PASS

Check 5: BC/AD date handling
  BC flag consistency: ✓ PASS

Check 6: Ancient date (>10K BC) handling
  Precision handling: ✓ PASS
```

### Running Performance Validation

Measure fetch, parse, and load times:

```bash
python wikipedia-ingestion/strategies/timeline_of_food/tools/performance_validation.py
```

Expected targets:
- **Total Time**: <30 seconds
- **Throughput**: >100 events/second

### Running Unit Tests

All tests (78 tests across 4 test files):

```bash
pytest wikipedia-ingestion/strategies/timeline_of_food/tests/ -v
```

Specific test files:

```bash
# Food event model tests
pytest wikipedia-ingestion/strategies/timeline_of_food/tests/test_food_event.py -v

# User Story 3 features (BC/AD, embedded dates, ancient dates)
pytest wikipedia-ingestion/strategies/timeline_of_food/tests/test_user_story_3.py -v

# Date extraction from bullets and tables
pytest wikipedia-ingestion/strategies/timeline_of_food/tests/test_date_extraction_strategies.py -v

# Main strategy integration tests
pytest wikipedia-ingestion/strategies/timeline_of_food/tests/test_timeline_of_food_strategy.py -v
```

## Data Model

### FoodEvent

```python
@dataclass
class FoodEvent:
    # Identity
    event_key: str                  # MD5(date + title + "Timeline of Food")
    source: str = "Timeline of Food"
    
    # Date Information
    date_explicit: int | None       # Year if explicitly stated
    date_range_start: int | None    # Start of inferred range
    date_range_end: int | None      # End of inferred range
    is_bc_start: bool = False       # True if start date is BC
    is_bc_end: bool = False         # True if end date is BC
    is_date_approximate: bool = False  # True for ~1450 format
    is_date_range: bool = False     # True for range format
    confidence_level: str = "explicit"  # Quality measure
    
    # Content
    title: str                      # First 50-70 chars of description
    description: str                # Full event text
    food_category: str | None       # Extracted category if identifiable
    
    # Context
    section_name: str               # E.g., "4000-2000 BCE"
    section_date_range_start: int   # Section's implied start
    section_date_range_end: int     # Section's implied end
    
    # References
    wikipedia_links: list[str]      # Wiki links in description
    external_references: list[int]  # Citation indices
    source_format: str              # "bullet" | "table" | "mixed"
    
    # Quality
    parsing_notes: str | None       # Issues or assumptions
    span_match_notes: str           # How date was matched
    precision: float = 1.0          # Precision value [0-1]
```

### HistoricalEvent (Database)

FoodEvent converts to HistoricalEvent for database storage:

```python
@dataclass
class HistoricalEvent:
    year: int | None                # Single year or range start
    year_end: int | None            # Range end (if applicable)
    is_bc: bool                     # True if year is BC
    title: str
    description: str
    category: str
    confidence: str                 # Confidence level
    source: str
    source_key: str                 # For deduplication
    metadata: dict                  # Additional data
```

## API Contracts

### FoodTimelineParseOrchestrator

Entry point for date parsing. Tries parsers in priority order:

```python
def parse_span_from_bullet(
    text: str,
    page_year: int = 2024
) -> Span | None:
    """Parse date from text, try all parsers in priority order."""
    # Tries: YearRange → Century → Decade → Years Ago → Circa/Tilde
```

**Input**: Raw text from bullet point or table cell
**Output**: Span object with (start_year, end_year, match_type) or None

### EventParser

Parses bullet points and tables to extract events:

```python
def parse_bullet_point(
    bullet_text: str,
    orchestrator: FoodTimelineParseOrchestrator,
    section_context: TextSection | None = None
) -> FoodEvent:
    """Parse a single bullet point or table cell."""
```

**Features**:
- Extracts title from first part of text
- Parses date from orchestrator
- Falls back to embedded date extraction
- Inherits section context if no date found
- Detects contentious/disputed marking

### TimelineOfFoodStrategy

Main orchestrator for ingestion:

```python
def fetch() -> str:
    """HTTP GET Wikipedia article with caching."""

def parse(html: str) -> dict:
    """Extract and parse all events."""
    
def generate_artifacts(events: list[FoodEvent]) -> dict:
    """Create JSON artifact file."""
```

## Testing Strategy

### Test Coverage

- **food_event.py**: 9 tests (title, event_key, conversion)
- **hierarchical_strategies.py**: 8 tests (section extraction)
- **date_extraction_strategies.py**: 34 tests (bullet/table parsing)
- **timeline_of_food_strategy.py**: 33 tests (full integration)
- **test_user_story_3.py**: 22 tests (BC/AD, embedded, ancient dates)
- **Total**: 78 tests, >80% coverage

### Test Fixtures

**sample_html.py**: Real HTML snippets covering:
- All date format types
- Table formats
- Section headers with implicit ranges
- Mixed content scenarios
- Edge cases (BC/AD, ancient dates, contentious)

**expected_events.json**: Expected parse results for fixture HTML, including:
- Correct year/range extraction
- Confidence level assignment
- Parsing notes generation
- Flag settings

### Running Tests with Coverage

```bash
pytest wikipedia-ingestion/strategies/timeline_of_food/tests/ \
  --cov=wikipedia-ingestion.strategies.timeline_of_food \
  --cov-report=html \
  -v
```

## Key Implementation Notes

### Table Parsing

Tables use **first column for date extraction**, subsequent columns for description:

```python
# In _extract_events_from_table():
date_cell = cells[0]  # First column contains date
description = " ".join(cells[1:])  # Rest is description

# Parse date from first column with full orchestrator
date_span = orchestrator.parse_span_from_bullet(date_cell)
```

### Decade Notation

DecadeParser handles "####s" pattern:

- `1990s` → 1990-1999 (start year + 9 years)
- `1800s` → 1800-1809 (start year + 9 years)
- `2000s` → 2000-2009
- Edge case: `1000s` → 1000-1009 (not 1000-1999)

### BC Range Notation Fix

YearRangeParser handles trailing BC/BCE markers:

- Input: `2500–1500 BCE`
- Detection: BC marker on second number
- Action: Apply BC flag to BOTH years
- Result: -2500 to -1500 (with is_bc_start=True, is_bc_end=True)

### Embedded Date Extraction

Three patterns tried in order:

1. **Parenthetical**: `(9600 BCE)` → -9600
2. **Range Phrase**: `between 4000 and 3000 BCE` → -4000 to -3000
3. **Comma-Separated**: `, 1750,` → 1750

Falls back to embedded extraction if main orchestrator returns None.

### Ancient Date Validation

For dates >10,000 BC:

```python
if start_year <= -10000:
    # Reduce precision
    precision = max(0.1, precision * 0.5)
    # Add note
    parsing_notes += "; ancient date (>10K BC) - precision reduced"
```

Rationale: Archaeological uncertainty increases with age.

### Years-Ago Anchoring

YearsAgoParser anchors to `page_year` (ingestion run year):

```python
# Input: "250,000 years ago" with page_year=2024
# Output: year = 2024 - 250000 = -248000 (stored as BC date)
```

This allows consistent historical comparison regardless of when ingestion runs.

## Troubleshooting

### Issue: Low date parsing success rate

**Possible causes**:
1. New date format not recognized by any parser
2. Section headers not properly extracted
3. Contentious/disputed marking preventing parse

**Solution**:
1. Review `span_match_notes` on unparsed events
2. Check `parsing_notes` for error messages
3. Add new parser to FoodTimelineParseOrchestrator

### Issue: BC date conversion errors

**Check**:
1. Verify `is_bc_start` and `is_bc_end` flags are set
2. Confirm negative years are used for BC
3. Validate year 0 is not present (1 BC → 1 AD)

**Common error**: Mixed BC/AD without proper handling:
```python
# ✗ WRONG: Start BC, end AD
date_range_start = -500  # 500 BC
date_range_end = 500     # 500 AD

# ✓ RIGHT: Either all BC or all AD
date_range_start = -500  # 500 BC
date_range_end = -100    # 100 BC
```

### Issue: Performance degradation

**Metrics to check**:
- HTTP fetch time (should use cache, <2s)
- HTML parsing time (should be <5s)
- Event extraction time (should be <20s total)

**Optimization**:
- Enable HTTP caching: `ingestion_common.get_html()`
- Check database connection timing
- Profile with `performance_validation.py`

## Future Enhancements

Potential improvements for future versions:

1. **LLM Category Classification**: Use LLM to extract food categories from descriptions
2. **Citation Tracking**: Map events to specific Wikipedia citations
3. **Cross-Reference Validation**: Check for conflicting dates across sources
4. **Incremental Updates**: Support re-ingestion with deduplication
5. **Confidence Scoring**: Machine learning-based confidence prediction
6. **Temporal Relationships**: Extract "before/after" relationships between events

## References

- **Wikipedia Article**: https://en.wikipedia.org/wiki/Timeline_of_food_and_drink
- **Date Format Specification**: `/specs/001-timeline-of-food/spec.md`
- **Implementation Plan**: `/specs/001-timeline-of-food/plan.md`
- **Data Model**: `/specs/001-timeline-of-food/data-model.md`
