# Timeline of Roman History: Shared Components & Patterns

**Document Purpose**: Identify reusable components, patterns, and architecture from existing strategies (Timeline of Food, Wars) that should be adopted for the Roman History ingestion strategy.

---

## 1. CORE ARCHITECTURE PATTERN (Strategy Base)

### Required: Implement `IngestionStrategy` Interface

All strategies must inherit from `strategies.strategy_base.IngestionStrategy` and implement:

```python
class TimelineOfRomanHistoryStrategy(IngestionStrategy):
    def name(self) -> str:
        """Return lowercase strategy name for logging/artifacts"""
        
    def fetch(self) -> FetchResult:
        """Phase 1: Fetch Wikipedia content"""
        
    def parse(self, fetch_result: FetchResult) -> ParseResult:
        """Phase 2: Parse content into events"""
        
    def generate_artifact(self, parse_result: ParseResult) -> ArtifactData:
        """Phase 3: Generate JSON artifact conforming to import_schema.json"""
```

**Why**: Ensures consistent integration with the orchestrator (`ingest_wikipedia.py`) and database loader.

---

## 2. SHARED HTTP CACHING FRAMEWORK

### Location: `ingestion_common.py`

**Function**: `get_html(url: str, context: str) -> tuple[(html: str, final_url: str), error: str | None]`

### What It Provides:
- ✅ **URL-keyed SHA256 caching** with automatic retry logic
- ✅ **Exponential backoff** for transient failures (timeouts, 5xx)
- ✅ **Content validation** (prevents stub/malformed content)
- ✅ **Canonical URL capture** (final URL after redirects for deduplication)
- ✅ **Centralized logging** (all fetches logged via `log_info()` / `log_error()`)

### Usage Pattern (from Timeline of Food):

```python
def fetch(self) -> FetchResult:
    log_info(f"Fetching {self.WIKIPEDIA_URL}")
    
    # MUST use get_html() for all HTTP fetches
    (html, final_url), error = get_html(
        self.WIKIPEDIA_URL, 
        context="timeline_of_roman_history"
    )
    
    if error or not html.strip():
        log_error(f"Failed to fetch: {error}")
        raise RuntimeError(f"Failed to fetch article: {error}")
    
    self.html_content = html
    self.canonical_url = final_url
    
    return FetchResult(
        strategy_name=self.STRATEGY_NAME,
        fetch_count=1,
        fetch_metadata={
            "url": self.WIKIPEDIA_URL,
            "final_url": final_url,
            "content_length_bytes": len(self.html_content),
            "fetch_timestamp_utc": datetime.utcnow().isoformat() + "Z",
        }
    )
```

**❌ NEVER DO:**
- Raw `requests.get()` for HTTP fetching
- Custom caching logic (files, dicts)
- Hard-coded User-Agent or custom retry logic
- HTTP response logging in strategy code

---

## 3. SPAN PARSING LIBRARY (FOR COLUMN-BASED DATE EXTRACTION)

### Location: `wikipedia-ingestion/span_parsing/`

**What's Available**:
- `span.py`: Core `SpanPrecision` enum and date composition logic
- `decade_parser.py`: Decade notation parsing (e.g., "1990s" → 1990-1999)
- Base classes for **custom parsers** (year + month/day column parsing)

### What Roman History Needs: **NEW `TableRowDateParser`**

Since Roman data is **tabular with separated year/month-day columns**, you'll need:

```python
# wikipedia-ingestion/span_parsing/table_row_date_parser.py

class TableRowDateParser:
    """Parse dates from separate year and month/day table columns."""
    
    def parse_year_column(self, year_text: str, is_bc: bool = False) -> (int, bool):
        """Extract year from year column. Return (year, is_bc)."""
        
    def parse_month_day_column(self, month_day_text: str) -> (int | None, int | None):
        """Extract month and day from month/day column. Return (month, day)."""
        
    def compose_date(self, year: int, is_bc: bool, month: int | None, day: int | None) -> HistoricalEvent:
        """Compose complete date from components."""
```

### Why Separate from Timeline of Food:
- **Food strategy**: Text-based parsing ("5-2 million years ago")
- **Roman strategy**: Table-based with columnar structure (separate columns for year, month, day)
- **Wars strategy**: Table-based with merged date cells or range columns

Each requires its own parser strategy; reuse the `SpanPrecision` and `HistoricalEvent` schema.

---

## 4. EVENT DATA MODEL

### Required Base: `historical_event.py` (HistoricalEvent)

All strategies output `HistoricalEvent` instances, which conform to the PostgreSQL schema.

### Optional Extension (Like Food Strategy):

Create a domain-specific event class:

```python
# wikipedia-ingestion/strategies/timeline_of_roman_history/roman_event.py

@dataclass
class RomanEvent:
    """Roman history event with table-based date handling."""
    
    event_key: str  # Deterministic MD5 for deduplication
    source: str = "Timeline of Roman History"
    
    # Columnar date components
    year: int
    month: int | None = None
    day: int | None = None
    is_bc: bool = False
    confidence_level: str = "explicit"  # | "approximate" | "uncertain" | "inferred"
    
    # Event content
    title: str = ""
    description: str = ""
    category: str = "Roman History"
    
    # Metadata
    span_match_notes: str = ""
    precision: float = 1.0
    
    def generate_title(self) -> str:
        """Generate title from first 50-70 chars of description."""
        # Use same logic as Food strategy
        
    def generate_event_key(self) -> str:
        """Generate deterministic key: MD5(date | title | source)."""
        # Use same logic as Food strategy
        
    def to_historical_event(self) -> HistoricalEvent:
        """Convert to HistoricalEvent for database insertion."""
```

---

## 5. LOGGING & OBSERVATION

### Location: `ingestion_common.py`

**Available Functions**:
- `log_info(msg: str)` — Info level, includes run_id and timestamp
- `log_error(msg: str)` — Error level, for recoverable failures
- `LOGS_DIR` — Directory for strategy-specific logs

### Pattern (From Food Strategy):

```python
from ingestion_common import log_info, log_error

log_info(f"Fetching Timeline of Roman History article")
log_info(f"Found {len(sections)} sections")
log_info(f"[{self.name()}] Parsed {len(events)} events in {elapsed:.2f}s")
log_info(f"[{self.name()}] Undated events: {undated_count}")

log_error(f"Failed to fetch Roman History article: {error}")
log_error(f"Skipped malformed row {row_index}: {reason}")
```

---

## 6. ARTIFACT OUTPUT SCHEMA

### Required: Conform to `import_schema.json`

All strategies output JSON artifacts matching this schema:

```json
{
  "strategy": "TimelineOfRomanHistory",
  "run_id": "20260127T181814Z",
  "generated_at_utc": "2026-01-27T18:18:15.085478Z",
  "event_count": 3000,
  "metadata": {
    "total_events_found": 3200,
    "total_events_parsed": 3000,
    "sections_identified": 8,
    "parsing_start_utc": "2026-01-27T18:18:14.877088Z",
    "parsing_end_utc": "2026-01-27T18:18:15.084637Z",
    "elapsed_seconds": 0.207549,
    "events_per_second": 14472.5,
    "confidence_distribution": {
      "explicit": 2800,
      "inferred": 150,
      "approximate": 50,
      "contentious": 0,
      "fallback": 0
    },
    "undated_events": {
      "total_undated": 0,
      "events": []
    }
  },
  "events": [
    {
      "title": "753 BC: Legendary founding of Rome",
      "start_year": 753,
      "end_year": 753,
      "is_bc_start": true,
      "is_bc_end": true,
      "start_month": null,
      "start_day": null,
      "precision": 1.0,
      "weight": 365,
      "url": "https://en.wikipedia.org/wiki/Timeline_of_Roman_history",
      "span_match_notes": "Year from table year column, no month/day",
      "description": "753 BC: Legendary founding of Rome on the Palatine Hill",
      "category": "Roman History",
      "_debug_extraction": null
    },
    /* ...more events... */
  ]
}
```

### Key Fields for Roman History:
- **precision**: 1.0 for explicit dates (year + month/day), 0.5 for year-only, 0.3 for approximate
- **weight**: Related to date span (single days = 365, year ranges = year span)
- **confidence_distribution**: Track how many events have explicit vs. inferred/approximate dates
- **start_month, start_day, end_month, end_day**: New for Roman strategy (Food doesn't use these)

---

## 7. DEDUPLICATION & EVENT KEYS

### Pattern (From Both Food & Wars):

```python
from hashlib import md5

def generate_event_key(year: int, is_bc: bool, title: str, source: str) -> str:
    """Generate deterministic key for deduplication."""
    date_str = str(year) if year else "0"
    bc_flag = "BC" if is_bc else "AD"
    key_input = f"{date_str}|{bc_flag}|{title}|{source}"
    return md5(key_input.encode('utf-8')).hexdigest()
```

**Why**: Ensures idempotency—running the strategy multiple times produces the same event keys, allowing the database loader to skip duplicates.

---

## 8. TESTING PATTERN

### Location: `wikipedia-ingestion/strategies/timeline_of_roman_history/tests/`

### Required Test Structure (From Food Strategy):

```
timeline_of_roman_history/
├── __init__.py
├── roman_event.py              # Domain model
├── table_row_date_parser.py    # NEW: Custom column parser
├── timeline_of_roman_history_strategy.py  # Main strategy
├── README.md
└── tests/
    ├── __init__.py
    ├── test_table_row_date_parser.py        # NEW: Test column parsing
    ├── test_roman_event.py                  # Test event model
    ├── test_timeline_of_roman_history_strategy.py  # Integration tests
    ├── fixtures/
    │   ├── __init__.py
    │   ├── sample_html.py       # Mock Wikipedia HTML
    │   └── expected_events.json  # Expected artifact output
```

### Mock Pattern (Using `unittest.mock.patch`):

```python
from unittest.mock import patch

def test_fetch_with_mocked_http():
    with patch('strategies.timeline_of_roman_history.ingestion_common.get_html') as mock_get:
        mock_get.return_value = (
            ("<html>...</html>", "https://final.url"), 
            None  # no error
        )
        strategy = TimelineOfRomanHistoryStrategy(run_id, output_dir)
        result = strategy.fetch()
        assert result.fetch_count == 1
```

---

## 9. STRATEGY REGISTRATION

### Location: `wikipedia-ingestion/strategies/ingestion_strategy_factory.py`

After implementing the Roman History strategy, register it:

```python
from strategies.timeline_of_roman_history.timeline_of_roman_history_strategy import TimelineOfRomanHistoryStrategy

class IngestionStrategyFactory:
    def create_strategy(self, strategy_name: str, ...) -> IngestionStrategy:
        strategies = {
            "timeline_of_food": TimelineOfFoodStrategy,
            "timeline_of_roman_history": TimelineOfRomanHistoryStrategy,  # ADD THIS
            "wars": WarsStrategy,
            ...
        }
```

---

## 10. RUNNING & VALIDATION

### Command Pattern (From Copilot Instructions):

```bash
# Ingest Roman History events
python ingest_wikipedia.py timeline_of_roman_history

# Validate artifact against schema
python - <<'PY'
import json
from jsonschema import validate

schema = json.load(open("wikipedia-ingestion/import_schema.json"))
artifact = json.load(open("wikipedia-ingestion/artifacts/timeline_of_roman_history_*.json"))
validate(instance=artifact, schema=schema)
print("✓ Artifact valid")
PY
```

---

## SUMMARY: SHARED vs. ROMAN-SPECIFIC

| Component | Shared (Reuse) | Roman-Specific (New) |
|-----------|---|---|
| **Architecture** | `IngestionStrategy` base class | Implement three methods |
| **HTTP Fetching** | `ingestion_common.get_html()` | Strategy: single Wikipedia page |
| **Caching** | Built-in (shared cache framework) | Reuse as-is |
| **Date Parsing** | `SpanPrecision` enum, `span_parsing/` lib | `TableRowDateParser` for columns |
| **Event Model** | `HistoricalEvent` base schema | `RomanEvent` with year/month/day |
| **Title Generation** | 50-70 char truncation (food pattern) | Reuse same logic |
| **Event Keys** | MD5(date\|title\|source) | Reuse same logic |
| **Logging** | `log_info()` / `log_error()` from `ingestion_common` | Reuse as-is |
| **Artifact Output** | `import_schema.json` | Conform (add month/day fields) |
| **Deduplication** | Event key pattern | Reuse same logic |
| **Testing** | pytest + mocks (food pattern) | Reuse structure, test table parsing |

---

## NEXT STEPS FOR ROMAN HISTORY IMPLEMENTATION

1. **Create directory**: `wikipedia-ingestion/strategies/timeline_of_roman_history/`
2. **Implement `TableRowDateParser`**: `span_parsing/table_row_date_parser.py`
3. **Create domain model**: `strategies/timeline_of_roman_history/roman_event.py`
4. **Implement strategy**: `strategies/timeline_of_roman_history/timeline_of_roman_history_strategy.py`
5. **Add tests**: `strategies/timeline_of_roman_history/tests/` (mirroring food pattern)
6. **Register strategy**: Update `ingestion_strategy_factory.py`
7. **Validate artifact**: Test output against `import_schema.json`
