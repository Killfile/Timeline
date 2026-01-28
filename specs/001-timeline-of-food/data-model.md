# Phase 1: Data Model Design - Timeline of Food

**Date**: 2026-01-25  
**Phase**: Design & Contracts

---

## Domain Model

### Core Entity: FoodEvent

Extends the standard `HistoricalEvent` from the ingestion system. Represents a single food-related historical event.

```python
@dataclass
class FoodEvent:
    """Food-related historical event with rich date handling."""
    
    # Basic identity (inherited from HistoricalEvent pattern)
    event_key: str              # Deterministic key for deduplication
    source: str = "Timeline of Food"
    
    # Date information (flexible to handle varied formats)
    date_explicit: int | None           # Year if explicitly stated (e.g., 1516)
    date_range_start: int | None        # Start of inferred range (e.g., 1500 for "16th century")
    date_range_end: int | None          # End of inferred range
    is_date_approximate: bool = False   # True if "~" or "circa" format
    is_date_range: bool = False         # True if range format (e.g., "8000-5000 BCE")
    confidence_level: str = "explicit"  # "explicit" | "inferred" | "approximate" | "contentious" | "fallback"
    
    # Event content
    title: str                  # Short event title (first ~50 chars)
    description: str            # Full event description
    food_category: str | None   # Extracted category if identifiable (e.g., "Cheese", "Bread")
    
    # Hierarchical context (section where event was found)
    section_name: str           # E.g., "4000-2000 BCE", "19th century"
    section_date_range_start: int  # Section's implied date range
    section_date_range_end: int
    
    # References and metadata
    wikipedia_links: list[str] = field(default_factory=list)  # Wiki links found in description
    external_references: list[int] = field(default_factory=list)  # Citation indices [1], [2], etc.
    source_format: str = "bullet"  # "bullet" | "table" | "mixed"
    
    # Data quality tracking
    parsing_notes: str | None = None  # Any parsing issues or assumptions
    
    def to_historical_event(self) -> HistoricalEvent:
        """Convert to standard HistoricalEvent for database storage."""
        return HistoricalEvent(
            event_key=self.event_key,
            source=self.source,
            date_year=self.date_explicit or self.section_date_range_start,
            date_range_start=self.date_range_start or self.section_date_range_start,
            date_range_end=self.date_range_end or self.section_date_range_end,
            title=self.title,
            description=self.description,
            category="Food",  # Always "Food" for this strategy
        )
```

### Supporting Entity: TextSection

Represents a major section in the Wikipedia article (provides hierarchical context).

```python
@dataclass
class TextSection:
    """Hierarchical section in the Timeline of Food article."""
    
    name: str                       # E.g., "4000-2000 BCE", "19th century"
    level: int                      # Header level (2 for ##, 3 for ###, etc.)
    
    # Inferred date range from section heading
    date_range_start: int
    date_range_end: int
    date_is_explicit: bool          # True if dates in heading (e.g., "4000-2000 BCE")
    date_is_range: bool             # True if heading contains range
    
    # Position in document
    position: int                   # Ordinal position (0-based)
    
    # Content
    event_count: int                # Number of events in this section
```

### Supporting Entity: Span (from span_parsing library)

**Use existing `span_parsing.span.Span` class** instead of creating new date extraction.

The `Span` class (from `span_parsing/span.py`) provides:

```python
# Existing Span class (reference only - do not redefine)
class Span:
    """Standardized date span representation."""
    start: int          # Start year (negative for BC)
    end: int            # End year (negative for BC)
    precision: str      # Precision level
    circa: bool         # True if approximate
    # ... other properties
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        
    def get_midpoint(self) -> int:
        """Calculate midpoint year."""
```

**Mapping Span → FoodEvent confidence**:
- `Span` parsed successfully → `confidence='explicit'`
- `Span.circa == True` → `confidence='approximate'`
- No `Span` (fallback to section) → `confidence='fallback'`

---

## Data Flow Diagram

```
Wikipedia HTML
    ↓
[Fetch Phase]
    ↓
HTML Cache File (artifact)
    ↓
[Parse Phase]
    ├─→ Extract Sections → TextSection objects
    ├─→ For each bullet/table row:
    │   ├─→ Extract date → DateExtraction
    │   ├─→ Extract text → title + description
    │   ├─→ Extract links → wikipedia_links
    │   └─→ Create FoodEvent
    └─→ JSON Artifact File
       ↓
[Load Phase]
    ├─→ Validate events
    ├─→ Convert FoodEvent → HistoricalEvent
    └─→ INSERT into database
```

---

## Parsing States & Transitions

### Hierarchical Parsing State Machine

```
START
  ↓
[Read Section Header] → TextSection
  ↓
[Read Event Line]
  ├─→ Is bullet? → [Extract Date] → [Extract Text] → FoodEvent → QUEUE
  ├─→ Is table row? → [Parse Table] → FoodEvent → QUEUE
  ├─→ Is subsection? → [Save current section] → [Push new section]
  └─→ Is empty/metadata? → [Skip]
  ↓
[More content?] → Loop back
  ↓
[End of article]
  ↓
END

Queued FoodEvents → JSON artifact
```

### Date Extraction State Machine (using span_parsing)

```
Raw Text: "5th century BCE"
  ↓
[ParseOrchestratorFactory.get_orchestrator(ParseOrchestratorTypes.FOOD_TIMELINE)]  # NEW
  ↓
[FoodTimelineParseOrchestrator.parse("5th century BCE")]  # NEW orchestrator
  ├→ Tries year_range_parser (no match)
  ├→ Tries year_with_era_parser (no match)
  ├→ Tries century_parser (MATCH)  # NEW parser
  └→ Returns Span(start=-500, end=-401, precision='century', circa=False)
  ↓
Span object → Map to FoodEvent fields
```

**Parser Priority in FoodTimelineParseOrchestrator** (highest to lowest):
1. Exact dates: `year_with_era_parser`, `year_only_parser`
2. Circa dates: `circa_year_parser`, `tilde_circa_year_parser` (NEW), `parenthesized_circa_year_range_parser`
3. Year ranges: `year_range_parser`, `multi_year_parser`
4. **Centuries**: `century_range_parser` (NEW), `century_parser` (NEW), `century_with_modifier_parser` (NEW)
5. **Years ago**: `years_ago_parser` (NEW)
6. Decades: `parenthesized_decade_range_parser`, `parenthesized_decade_parser`
7. Fallback: `fallback_parser`

---

## Database Schema

These entities map to the existing PostgreSQL schema via `HistoricalEvent`:

```sql
-- Existing table (no changes needed)
CREATE TABLE IF NOT EXISTS historical_events (
    event_key TEXT PRIMARY KEY,
    source TEXT,
    title TEXT,
    description TEXT,
    category TEXT,
    date_year INTEGER,
    date_range_start INTEGER,
    date_range_end INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Enrichments can track confidence/parsing notes via separate table if needed:
-- CREATE TABLE IF NOT EXISTS event_metadata (
--     event_key TEXT PRIMARY KEY REFERENCES historical_events(event_key),
--     confidence_level TEXT,
--     parsing_notes TEXT,
--     source_format TEXT,
--     ...
-- );
-- For now: Store parsing notes in description field or logs
```

**Mapping FoodEvent → HistoricalEvent**:

| FoodEvent Field | HistoricalEvent Field | Notes |
|-----------------|----------------------|-------|
| event_key | event_key | Deterministic deduplication |
| title | title | Short event summary |
| description | description | Full event text |
| date_explicit \| section_date_range_start | date_year | Primary date field |
| date_range_start \| section_date_range_start | date_range_start | Range start |
| date_range_end \| section_date_range_end | date_range_end | Range end |
| (none) | category | Always "Food" |
| source | source | Always "Timeline of Food" |

**Event Key Formula**:
```python
event_key = hashlib.md5(
    f"{date_year}_{title[:50]}_{source}".encode()
).hexdigest()

# Example: 
# Title: "Figs cultivated in the Jordan Valley"
# Year: 9300
# Source: "Timeline of Food"
# → event_key = "7f2e4c8b9a1d3e5c..."
```

---

## API Contracts

### Input: Wikipedia Article

**URL**: `https://en.wikipedia.org/wiki/Timeline_of_food`

**Expected format**: HTML with structure:
```html
<div id="mw-content-text">
  <h2>Prehistoric times</h2>
  <ul>
    <li>• 5-2 million years ago: Hominids shift away...</li>
    ...
  </ul>
  <h2>Neolithic</h2>
  <ul>...</ul>
  ...
</div>
```

### Output: JSON Artifact

**File**: `artifacts/timeline_of_food_<RUN_ID>.json`

**Schema**:
```json
{
  "strategy": "TimelineOfFood",
  "run_id": "20260125_120000_abc123",
  "generated_at_utc": "2026-01-25T12:00:00Z",
  "event_count": 3847,
  "metadata": {
    "sections_parsed": 12,
    "events_with_explicit_dates": 3200,
    "events_with_inferred_dates": 600,
    "events_with_approximate_dates": 47,
    "unparseable_events": 0,
    "confidence_distribution": {
      "explicit": 0.83,
      "inferred": 0.16,
      "approximate": 0.01,
      "contentious": 0.0,
      "fallback": 0.0
    }
  },
  "events": [
    {
      "event_key": "7f2e4c8b9a1d3e5c...",
      "source": "Timeline of Food",
      "title": "Figs cultivated",
      "description": "Figs cultivated in the Jordan Valley",
      "category": "Food",
      "date_year": 9300,
      "date_range_start": 9300,
      "date_range_end": 9300,
      "confidence_level": "explicit",
      "section_name": "Neolithic",
      "parsing_notes": null
    },
    ...
  ]
}
```

### Output: Strategy Log

**File**: `logs/timeline_of_food_<RUN_ID>.log`

**Contents**:
- Summary: Events parsed, success rate, warnings
- Parsing decisions: Which sections, how many events per section
- Confidence breakdown: Distribution of confidence levels
- Errors/warnings: Any unparseable events, edge cases, anomalies
- Performance: Time elapsed, events/second, memory usage

**Example**:
```
[2026-01-25 12:00:00] Timeline of Food Ingestion Strategy Started
[2026-01-25 12:00:01] Fetched article (42 KB)
[2026-01-25 12:00:02] Detected 12 sections
[2026-01-25 12:00:03] Parsing section "Prehistoric times" (45 events)
[2026-01-25 12:00:05] Parsing section "Neolithic" (28 events)
...
[2026-01-25 12:00:15] Parsed 3,847 events total
[2026-01-25 12:00:15] Confidence breakdown: explicit=83%, inferred=16%, approximate=1%
[2026-01-25 12:00:15] Wrote artifact: artifacts/timeline_of_food_abc123.json
[2026-01-25 12:00:15] Strategy completed successfully
```

---

## Implementation Checklist for Phase 1

### A. Extend span_parsing library (NEW)
- [ ] **Create `span_parsing/century_parser.py`** (handles "5th century BCE")
- [ ] **Create `span_parsing/century_range_parser.py`** (handles "11th-14th centuries")
- [ ] **Create `span_parsing/years_ago_parser.py`** (handles "250,000 years ago")
- [ ] **Create `span_parsing/tilde_circa_year_parser.py`** (handles "~1450" as circa year)
- [ ] **Create `span_parsing/century_with_modifier_parser.py`** (handles Early/Mid/Late/Before century forms and hybrid ranges)
- [ ] **Create `span_parsing/orchestrators/food_timeline_parse_orchestrator.py`** (custom parser ordering)
- [ ] **Update `span_parsing/orchestrators/parse_orchestrator_factory.py`** (add FOOD_TIMELINE enum)
- [ ] Write unit tests for 5 new parsers (>80% coverage each)
- [ ] Write unit tests for new orchestrator

### B. Implement Timeline of Food strategy
- [ ] Define FoodEvent dataclass
- [ ] Define TextSection dataclass
- [ ] Implement TextSectionParser (extract sections from HTML)
- [ ] **Use FoodTimelineParseOrchestrator for date parsing**
- [ ] Implement EventTextParser (bullet + table parsing)
- [ ] Implement Span → confidence level mapping logic
- [ ] Implement event_key generation
- [ ] Implement conversion to HistoricalEvent
- [ ] Write unit tests for event parsing (>80% coverage)
- [ ] Create test fixtures (sample HTML, expected events)
- [ ] Document all classes and functions
- [ ] Update ingestion_strategy_factory.py to register TimelineOfFood strategy

---

## Notes for Implementers

1. **Reuse existing patterns**: Follow ListOfYearsStrategy structure for consistency
2. **Error handling**: Log unparseable events; don't fail pipeline
3. **Date edge cases**: Handle BC/AD year 0 properly (no year 0 exists)
4. **Performance**: Should parse 3,000+ events in <30 seconds
5. **Testing**: Create comprehensive fixtures; test each date format separately

---

## Next Steps

→ Phase 1 (Contract Design): Define API endpoints/message formats  
→ Phase 1 (Implementation): Build strategy classes  
→ Phase 2: Build unit tests  
→ Phase 3: Integration testing with real Wikipedia article
