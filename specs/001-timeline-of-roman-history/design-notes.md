# Timeline of Roman History - Design Notes

## Overview

This document outlines the technical design and implementation strategy for importing the [Timeline of Roman History](https://en.wikipedia.org/wiki/Timeline_of_Roman_history) Wikipedia page into the Timeline database.

## Key Challenges

### 1. HTML Rowspan-Based Data Inheritance

**Problem**: Wikipedia's table uses `rowspan` attributes where year cells span multiple rows. Rows without explicit year cells must inherit the year from the parent cell.

```
| Year  | Event 1              |
| (spans 3 rows)  | Event 2  |
|       | Event 3              |
|       | Event 4              |
```

**Solution**: Implement `RowspanContext` tracking that:
- Identifies year cells with rowspan > 1
- Tracks remaining row count for inherited years
- Assigns inherited year with `confidence="inferred"` confidence level
- Logs warnings when inheriting years across multiple rows

### 2. Date Format Variations

The Wikipedia table contains at least 8 date format variations:

1. **Exact dates**: "27 April 753 BC"
2. **Month+Year**: "January 44 BC" 
3. **Year only**: "27 BC", "68 AD"
4. **Centuries**: "15th century" → `1401-1500`
5. **Approximate dates**: "c. 1000 BC" → `confidence="approximate"`
6. **Ranges**: "509–510 BC" → Use start year as canonical
7. **Legendary dates**: Marked with uncertainty → `confidence="legendary"`
8. **Uncertain dates**: "?180s AD" → `confidence="uncertain"`

**Solution**: Implement `TableRowDateParser` with:
- Multiple regex patterns for each format
- SpanPrecision enum for metadata (EXACT_DATE, MONTH_ONLY, YEAR_ONLY, etc.)
- Separate confidence field for source reliability (explicit, inferred, legendary, etc.)
- Month-only dates converted to SpanPrecision.MONTH_ONLY

### 3. BC/AD Chronological Ordering

**Challenge**: BC dates go backward (200 BC → 100 BC → 1 BC → 1 AD → 100 AD)

**Solution**: 
- Store BC years as negative integers in database
- Example: `200 BC = -200`, `1 AD = 1`
- Sort chronologically by numeric year value
- Display logic handles formatting in frontend

### 4. Byzantine Empire Continuity

**Challenge**: Timeline includes Byzantine Empire events. Should they be included?

**Decision**: YES - Include all events, as Byzantine Empire is historical continuation of Eastern Roman Empire. Tag with `civilization="Byzantine"` if needed for filtering.

## Architecture

### Shared Module: timeline_common

To resolve circular dependencies between `api/` and `wikipedia-ingestion/`, event key computation moved to shared module:

```
timeline_common/
├── __init__.py
├── event_key.py           # SHA-256 deterministic key computation
└── tests/
    └── test_event_key.py  # 100% coverage, 32 tests
```

**Import Path**: `from timeline_common.event_key import compute_event_key`

### Strategy Architecture

```
TimelineOfRomanHistoryStrategy (IngestionStrategy interface)
├── fetch()              # HTTP fetch with caching
│   └── Uses ingestion_common.get_html()
├── parse()              # HTML to RomanEvent objects
│   ├── TableRowDateParser (date extraction)
│   ├── RowspanContext (year inheritance)
│   └── RomanEvent data class
└── generate_artifact()  # RomanEvent[] → database inserts
    └── Uses database_ingestion.insert_historical_events()
```

### Core Components

#### RomanEvent (Data Class)

```python
@dataclass
class RomanEvent:
    title: str                           # Event title
    start_year: int                      # Start year (-ve = BC)
    end_year: int                        # End year
    start_month: Optional[int]           # 1-12 or None
    start_day: Optional[int]             # 1-31 or None
    description: str                     # Full event text
    span_precision: SpanPrecision        # EXACT_DATE, MONTH_ONLY, YEAR_ONLY, etc.
    confidence: str                      # explicit, inferred, legendary, uncertain
    event_key: str                       # SHA-256 for deduplication (computed)
```

#### TableRowDateParser

Parses date cells using multiple regex patterns in priority order:

1. Exact dates: `r"(\d{1,2})\s+(\w+)\s+(\d+)(?:\s+(BC|AD|BCE|CE))?"` → day, month, year
2. Month+year: `r"(\w+)\s+(\d+(?:\s+)?(BC|AD|BCE|CE)?)"` → month, year
3. Year only: `r"(\d+)\s+(BC|AD|BCE|CE)"` → year
4. Century: `r"(\d+)(?:st|nd|rd|th)\s+century"` → year_start, year_end
5. Approximate: `r"c\.\s+(\d+)(?:\s+(BC|AD))?"` → year, confidence="approximate"
6. Range: `r"(\d+)–(\d+)\s+(BC)"` → start_year, end_year (use start as canonical)
7. Uncertain: `r"\?(\d+s?)\s+(BC|AD|BCE|CE)"` → year, confidence="uncertain"
8. Legendary: Pattern for dates before historical records → confidence="legendary"

#### RowspanContext

Tracks multi-row year inheritance:

```python
@dataclass
class RowspanContext:
    inherited_year: int                  # Year from parent cell
    remaining_rows: int                  # Rows still inheriting
    
    def should_inherit(self) -> bool:
        return self.remaining_rows > 0
    
    def consume_row(self) -> bool:
        """Return True if row should inherit, update counter."""
        if self.remaining_rows > 0:
            self.remaining_rows -= 1
            return True
        return False
```

## Extraction Algorithm

### Phase 1: HTML to Table Rows

1. Fetch HTML via `get_html()` (with caching and retry)
2. Parse with BeautifulSoup
3. Locate `<table>` element (main events table)
4. Extract rows maintaining rowspan context

### Phase 2: Row Parsing with Rowspan Handling

For each `<tr>` in table:

```
1. Check for year cell with rowspan > 1
   → Store in RowspanContext(year, rowspan - 1)
   
2. If rowspan context active and current row has no year cell
   → Use inherited year, log "Year inherited from row N"
   → Decrement RowspanContext.remaining_rows
   
3. Extract event cells
4. Parse dates using TableRowDateParser
5. Create RomanEvent with confidence levels:
   - explicit: Dates explicitly in table
   - inferred: Inherited from rowspan parent
   - legendary: Pre-753 BC dates (before Rome founded)
   - approximate: Dates marked "c."
   - uncertain: Dates marked "?"
```

### Phase 3: Event Deduplication & Storage

1. Compute event_key via SHA-256(`{title}|{start_year}|{end_year}|{description}`)
2. Check existing keys in DB (enrichment persistence)
3. Insert into `historical_events` table
4. Track enrichment association via event_key

## Edge Cases

### Legendary Period Events (Before 753 BC)

Examples:
- Founding of Rome: 753 BC
- Romulus and Remus: Legendary
- Pre-historical events with uncertain dates

**Handling**: Include all events, set `confidence="legendary"` for pre-historical periods. Allow frontend filtering by confidence level.

### Multi-Year Events

Example: "Punic Wars" spanning 264-146 BC

**Handling**: Use start_year (264 BC) as canonical year for table sorting. Store end_year for duration calculation. Parse ranges via regex: `r"(\d+)–(\d+)\s+(BC)"`

### Month-Only Dates

Example: "January 44 BC" (Caesar assassination) but specific day unknown

**Handling**: 
- Extract month (1-12)
- Set start_day = None
- Set span_precision = SpanPrecision.MONTH_ONLY
- Confidence remains "explicit" (explicitly stated in table)

### Embedded Date Ranges

Example: Event text says "November 29–30, 1974" but table year is canonical

**Handling**: Ignore ranges in event text, use table year only. Date canonicality rule: **Table year is canonical, text ranges are ignored.**

## Testing Strategy

### Unit Tests

1. **TableRowDateParser**: 40+ tests covering all 8 date formats
2. **RowspanContext**: 15+ tests for inheritance logic
3. **RomanEvent**: 10+ tests for validation
4. **Integration**: 20+ tests for end-to-end extraction

### Test Data

Use fixtures from actual Wikipedia table:

```python
# sample_rows.py
LEGENDARY_PERIOD = """
<tr><td rowspan="3">Legendary</td><td>Founding of Rome</td></tr>
<tr><td>Romulus and Remus</td></tr>
<tr><td>Reign of Kings period</td></tr>
"""

EARLY_REPUBLIC = """
<tr><td>509 BC</td><td>Fall of Tarquins, Republic established</td></tr>
"""

BYZANTINE_ERA = """
<tr><td>1453 AD</td><td>Fall of Constantinople, End of Eastern Roman Empire</td></tr>
"""
```

### Coverage Target

- Minimum 95% code coverage for parser modules
- 100% coverage for event_key (achieved: 32 tests, all passing)
- All edge cases covered

## Implementation Phases

### Phase 0: Infrastructure (CURRENT - In Progress)
- ✅ Create timeline_common module
- ✅ Move event_key.py to timeline_common
- ✅ Create unit tests (32 tests, 100% coverage)
- ✅ Update imports (api/ and wikipedia-ingestion/)
- 🔲 Verify pytest discovery

### Phase 1: Research & Design
- Research Wikipedia table structure
- Identify date format patterns
- Design TableRowDateParser
- Design RowspanContext algorithm

### Phase 2: Core Components
- Implement RomanEvent data class
- Implement TableRowDateParser with regex patterns
- Implement RowspanContext tracking
- Create comprehensive unit tests

### Phase 3: Strategy Implementation
- Implement TimelineOfRomanHistoryStrategy
- Integrate with database_ingestion
- Implement error handling and logging

### Phase 4: Integration & Validation
- End-to-end testing with actual Wikipedia data
- Performance validation
- Documentation and deployment

## Verification Checklist

- [ ] timeline_common module created and tested (100% coverage)
- [ ] Backward compatibility maintained (api/ re-exports work)
- [ ] pytest discovers timeline_common/tests/
- [ ] All 32 event_key tests pass
- [ ] database_ingestion imports from timeline_common
- [ ] TableRowDateParser handles all 8 date formats
- [ ] RowspanContext correctly inherits years
- [ ] RomanEvent validates BC date ordering
- [ ] Byzantine era events included
- [ ] Legendary confidence level applied to pre-753 BC
- [ ] Month-only dates converted to SpanPrecision.MONTH_ONLY
- [ ] E2E test with actual Wikipedia table passes
- [ ] Coverage ≥95% for all new modules

## References

- [Timeline of Roman History (Wikipedia)](https://en.wikipedia.org/wiki/Timeline_of_Roman_history)
- [Specification](./SPEC.md) - Full specification document
- [timeline_common/event_key.py](../../timeline_common/event_key.py) - SHA-256 event key computation
- [database_ingestion.py](../../wikipedia-ingestion/database_ingestion.py) - Database insert logic
- [ingestion_common.py](../../wikipedia-ingestion/ingestion_common.py) - HTTP caching and shared utilities
