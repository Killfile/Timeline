# Wikipedia Ingestion System

This system ingests historical events from Wikipedia and other sources into the Timeline database using a clean ETL (Extract-Transform-Load) architecture.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Usage](#usage)
4. [Event Schema](#event-schema)
5. [Strategies](#strategies)
6. [Artifact Format](#artifact-format)
7. [Configuration](#configuration)
8. [Testing](#testing)

---

## Quick Start

### Run Complete ETL Pipeline

```bash
# Step 1: Extract (generate JSON artifacts)
docker-compose run --rm wikipedia-ingestion

# Step 2: Load (insert to database)
docker-compose run --rm database-loader
```

### Run With Convenience Script

```bash
./scripts/atomic-reimport
```

This script runs both Extract and Load stages with the configured date range from `.env`.

---

## Architecture

The system follows a clean **Extract-Transform-Load (ETL)** architecture with complete separation between data collection and database operations:

```
┌──────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│     EXTRACT      │ →   │   JSON ARTIFACTS │  →  │      LOAD       │
│                  │     │                  │     │                 │
│  Strategies      │     │  events_*.json   │     │ database_loader │
│  fetch + parse   │     │  (inspectable!)  │     │  validate +     │
│                  │     │                  │     │  insert         │
└──────────────────┘     └──────────────────┘     └─────────────────┘
```

### Benefits

- ✅ **Clean separation** - Each stage runs independently
- ✅ **Debuggable** - Inspect artifacts between stages
- ✅ **Reprocessable** - Re-run Load without re-fetching
- ✅ **Flexible** - Any process that produces conformant JSON can load data
- ✅ **Testable** - Test each stage independently

---

## Usage

### Extract Stage

Generate JSON artifacts from data sources.

#### Run All Strategies

```bash
docker-compose run --rm wikipedia-ingestion
```

#### Run Specific Strategy

```bash
# List of years strategy
WIKIPEDIA_INGEST_STRATEGY=list_of_years docker-compose run --rm wikipedia-ingestion

# Bespoke events strategy
WIKIPEDIA_INGEST_STRATEGY=bespoke_events docker-compose run --rm wikipedia-ingestion

# Time periods strategy
WIKIPEDIA_INGEST_STRATEGY=list_of_time_periods docker-compose run --rm wikipedia-ingestion
```

#### Run Multiple Strategies

```bash
WIKIPEDIA_INGEST_STRATEGIES=list_of_years,bespoke_events docker-compose run --rm wikipedia-ingestion
```

#### Custom Date Range

```bash
WIKI_MIN_YEAR="1000 BC" WIKI_MAX_YEAR="2026 AD" docker-compose run --rm wikipedia-ingestion
```

### Load Stage

Load all JSON artifacts into the database.

#### Replace Mode (Default)

Clears all existing data and inserts fresh:

```bash
docker-compose run --rm database-loader
```

#### Upsert Mode

Deletes events by URL and inserts (preserves enrichments):

```bash
LOADER_MODE=upsert docker-compose run --rm database-loader
```

### Inspect Artifacts

```bash
# List artifacts
ls -lh wikipedia-ingestion/logs/events_*.json

# View artifact
jq . wikipedia-ingestion/logs/events_list_of_years_*.json | less

# Count events
jq '.event_count' wikipedia-ingestion/logs/events_*.json

# View first event
jq '.events[0]' wikipedia-ingestion/logs/events_list_of_years_*.json
```

### Development Workflow

```bash
# Extract once
docker-compose run --rm wikipedia-ingestion

# Develop/debug loader (run multiple times without re-extracting)
docker-compose run --rm database-loader
docker-compose run --rm database-loader
docker-compose run --rm database-loader
```

---

## Event Schema

All events must conform to the **canonical event schema** defined in `event_schema.py`.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | `str` | Event title/summary (max 500 chars) |
| `description` | `str` | Full event description (max 500 chars) |
| `url` | `str` | Source Wikipedia URL |
| `start_year` | `int` | Start year (positive integer, era indicated by `is_bc_start`) |
| `end_year` | `int` | End year (positive integer, era indicated by `is_bc_end`) |
| `is_bc_start` | `bool` | `True` if start year is BC/BCE |
| `is_bc_end` | `bool` | `True` if end year is BC/BCE |
| `weight` | `int` | Event duration in days (used for packing priority) |
| `precision` | `float` | Date precision value (represents uncertainty) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `start_month` | `int \| None` | Start month (1-12), or `None` for year-only precision |
| `start_day` | `int \| None` | Start day (1-31), or `None` |
| `end_month` | `int \| None` | End month (1-12), or `None` |
| `end_day` | `int \| None` | End day (1-31), or `None` |
| `category` | `str \| None` | Event category/tag from extraction |
| `pageid` | `int \| None` | Wikipedia page ID (for deduplication) |

### Example Event

```json
{
  "title": "Industrial Age",
  "description": "Period of industrialization and mechanization",
  "url": "https://en.wikipedia.org/wiki/Industrial_Age",
  "start_year": 1760,
  "start_month": null,
  "start_day": null,
  "end_year": 1970,
  "end_month": null,
  "end_day": null,
  "is_bc_start": false,
  "is_bc_end": false,
  "weight": 76661,
  "precision": 730.5,
  "category": "Technological periods",
  "pageid": null
}
```

### Validation

Use `CanonicalEvent` dataclass and `validate_canonical_event()` to validate events:

```python
from event_schema import CanonicalEvent, validate_canonical_event

# Validate dict
errors = validate_canonical_event(event_dict)
if errors:
    print(f"Invalid event: {errors}")

# Or use dataclass
event = CanonicalEvent(**event_dict)
```

---

## Strategies

Strategies implement the `IngestionStrategy` interface defined in `strategy_base.py`. Each strategy has four phases:

1. **fetch()** - Discover and fetch source data (HTTP/API calls)
2. **parse(fetch_result)** - Extract and structure events
3. **generate_artifacts()** - Write JSON artifact files
4. **cleanup_logs()** - Generate diagnostic logs

### Available Strategies

#### 1. List of Years (`list_of_years`)

Extracts events from Wikipedia's "List of years" pages (e.g., 490 BC, 2025 AD).

**Features:**
- Discovers year pages within configured range
- Parses HTML with BeautifulSoup
- Uses span parsing framework for date extraction
- Generates exclusion report for unparseable events

**Configuration:**
- `WIKI_MIN_YEAR` - Earliest year (e.g., "100 BC")
- `WIKI_MAX_YEAR` - Latest year (e.g., "2026 AD")

**Usage:**
```bash
WIKIPEDIA_INGEST_STRATEGY=list_of_years docker-compose run --rm wikipedia-ingestion
```

#### 2. List of Time Periods (`list_of_time_periods`)

Extracts historical periods from Wikipedia's "List of time periods" page.

**Features:**
- Parses 6 main sections (Technological, African, American, Asian, European, Oceanian)
- Extracts period names and date ranges
- Handles complex date formats (BC/AD, centuries, approximate dates)

**Usage:**
```bash
WIKIPEDIA_INGEST_STRATEGY=list_of_time_periods docker-compose run --rm wikipedia-ingestion
```

#### 3. Bespoke Events (`bespoke_events`)

Loads manually curated events from a JSON file.

**Features:**
- Reads from `bespoke_events.json` (creates template if missing)
- Validates against canonical schema
- Useful for custom or future events

**Usage:**
```bash
WIKIPEDIA_INGEST_STRATEGY=bespoke_events docker-compose run --rm wikipedia-ingestion
```

**File format:**
```json
{
  "events": [
    {
      "title": "My Event",
      "description": "Description",
      "start_year": 2030,
      "end_year": 2030,
      "is_bc_start": false,
      "is_bc_end": false,
      "precision": 365.25,
      "weight": 365,
      "url": null
    }
  ]
}
```

#### 4. Timeline of Roman History (`timeline_of_roman_history`)

Extracts historical events from Wikipedia's [Timeline of Roman History](https://en.wikipedia.org/wiki/Timeline_of_Roman_history) article.

**Features:**
- Parses Wikipedia wikitable format with complex row structures
- Handles rowspan inheritance (year cells spanning multiple rows)
- Extracts and normalizes dates with BC/AD notation
- Assigns confidence levels based on parsing method and historical period
- Distinguishes legendary events (pre-753 BC) from documented history
- Comprehensive error handling for malformed table cells

**Architecture:**
- `TableRowDateParser`: Multi-strategy date parser supporting 8+ date formats
- `RomanEvent`: Domain model with confidence assignment and event key computation
- `TimelineOfRomanHistoryStrategy`: Full ingestion pipeline with caching

**Usage:**
```bash
WIKIPEDIA_INGEST_STRATEGY=timeline_of_roman_history docker-compose run --rm wikipedia-ingestion
```

**Configuration:**
```
WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/Timeline_of_Roman_history"
(hardcoded - no environment variable needed)
```

**Documentation:**
- See [Timeline of Roman History Strategy README](strategies/timeline_of_roman_history/README.md) for:
  - Architectural overview and data flow
  - Design decisions (rowspan handling, legendary dates, etc.)
  - Confidence level assignment rules
  - Edge cases handled (BC-to-AD transitions, alternate date formats, etc.)
  - Usage examples and integration patterns

### Creating New Strategies

1. **Implement the interface:**

```python
from strategy_base import IngestionStrategy

class MyStrategy(IngestionStrategy):
    def name(self) -> str:
        return "my_strategy"
    
    def fetch(self) -> dict:
        # Fetch data
        return {"data": ...}
    
    def parse(self, fetch_result: dict) -> list[dict]:
        # Parse into events
        return [event1, event2, ...]
    
    def generate_artifacts(self, events: list[dict]) -> Path:
        # Write JSON artifact
        artifact_path = self.output_dir / f"events_my_strategy_{self.run_id}.json"
        # ... write artifact
        return artifact_path
    
    def cleanup_logs(self) -> None:
        # Optional: generate logs
        pass
```

2. **Register in `ingest_wikipedia.py`:**

```python
elif strategy_name in {"my_strategy", "my"}:
    strategy_obj = MyStrategy(RUN_ID, output_dir)
```

3. **Run it:**

```bash
WIKIPEDIA_INGEST_STRATEGY=my_strategy docker-compose run --rm wikipedia-ingestion
docker-compose run --rm database-loader
```

---

## Artifact Format

All strategies must produce JSON artifacts conforming to this format:

```json
{
  "strategy": "list_of_years",
  "run_id": "20260110T120000Z",
  "generated_at_utc": "2026-01-10T12:00:00Z",
  "event_count": 1500,
  "metadata": {
    "pages_processed": 250,
    "exclusions": {}
  },
  "events": [
    {
      "title": "Battle of Marathon",
      "description": "...",
      "start_year": 490,
      "is_bc_start": true,
      "end_year": 490,
      "is_bc_end": true,
      "weight": 365,
      "precision": 365.25,
      "url": "https://en.wikipedia.org/wiki/490_BC"
    }
  ]
}
```

### Artifact Structure

| Field | Type | Description |
|-------|------|-------------|
| `strategy` | `str` | Strategy name |
| `run_id` | `str` | Unique run identifier (ISO timestamp) |
| `generated_at_utc` | `str` | Generation timestamp (ISO 8601) |
| `event_count` | `int` | Number of events in artifact |
| `metadata` | `object` | Strategy-specific metadata |
| `events` | `array` | Array of event objects (see Event Schema) |

### Artifact Naming Convention

Artifacts must follow this naming pattern:

```
events_{strategy_name}_{run_id}.json
```

Examples:
- `events_list_of_years_20260110T120000Z.json`
- `events_bespoke_events_20260110T120000Z.json`
- `events_list_of_time_periods_20260110T120000Z.json`

---

## Configuration

### Environment Variables

#### Extract Stage (`wikipedia-ingestion`)

| Variable | Description | Default |
|----------|-------------|---------|
| `WIKIPEDIA_INGEST_STRATEGY` | Strategy name or "all" | `list_of_years` |
| `WIKIPEDIA_INGEST_STRATEGIES` | Comma-separated strategy list | - |
| `WIKI_MIN_YEAR` | Earliest year (e.g., "100 BC") | `3000 BC` |
| `WIKI_MAX_YEAR` | Latest year (e.g., "2026 AD") | `2026 AD` |

#### Load Stage (`database-loader`)

| Variable | Description | Default |
|----------|-------------|---------|
| `LOADER_MODE` | Load mode: `replace` or `upsert` | `replace` |
| `ARTIFACT_DIR` | Directory with artifacts | `logs/` |
| `ARTIFACT_PATTERN` | Glob pattern for artifacts | `events_*.json` |
| `DB_HOST` | Database host | `database` |
| `DB_PORT` | Database port | `5432` |
| `DB_NAME` | Database name | `timeline` |
| `DB_USER` | Database user | `timeline` |
| `DB_PASSWORD` | Database password | (from .env) |
| `INGEST_TARGET_TABLE` | Target table | `historical_events` |

### Load Modes

#### Replace Mode (Default)

Clears all data in the target table and inserts fresh data:

```bash
docker-compose run --rm database-loader
# or
LOADER_MODE=replace docker-compose run --rm database-loader
```

**Use when:**
- Doing a clean full reimport
- Testing with sample data
- Don't need to preserve enrichments

#### Upsert Mode

Deletes events by URL and inserts fresh data (preserves enrichments):

```bash
LOADER_MODE=upsert docker-compose run --rm database-loader
```

**How it works:**
1. Collect all unique URLs from all artifacts
2. Delete all database events with matching URLs
3. Insert all events from artifacts

**Use when:**
- Reimporting Wikipedia data while preserving user enrichments
- Updating specific year ranges
- Preserving AI-generated categories and interest counts

**Key guarantee:** All deletions complete before any insertions, even if the same URL appears in multiple artifacts.

---

## Testing

### Unit Tests

```bash
# Run all tests
docker-compose run --rm wikipedia-ingestion pytest

# Run specific test file
docker-compose run --rm wikipedia-ingestion pytest test_event_schema.py

# Run with coverage
docker-compose run --rm wikipedia-ingestion pytest --cov=. --cov-report=html
```

### Integration Tests

```bash
# Test extract + load
docker-compose run --rm wikipedia-ingestion pytest test_integration_schema.py

# Test with real Wikipedia data
WIKI_MIN_YEAR="2010 AD" WIKI_MAX_YEAR="2010 AD" docker-compose run --rm wikipedia-ingestion
docker-compose run --rm database-loader
```

### Manual Testing

```bash
# Extract with small range
WIKI_MIN_YEAR="2025 AD" WIKI_MAX_YEAR="2025 AD" docker-compose run --rm wikipedia-ingestion

# Inspect artifact
jq . wikipedia-ingestion/logs/events_list_of_years_*.json | less

# Load to database
docker-compose run --rm database-loader

# Check database
docker-compose exec database psql -U timeline -d timeline \
  -c "SELECT COUNT(*) FROM historical_events WHERE start_year = 2025;"
```

---

## Troubleshooting

### No Artifacts Generated

**Check logs:**
```bash
cat wikipedia-ingestion/logs/ingest_*.info.log
cat wikipedia-ingestion/logs/ingest_*.error.log
```

**Verify strategies ran:**
```bash
ls -lh wikipedia-ingestion/logs/events_*.json
```

### Loader Can't Find Artifacts

**Check artifact directory:**
```bash
ls -lh wikipedia-ingestion/logs/events_*.json
```

**Verify ARTIFACT_DIR:**
```bash
echo $ARTIFACT_DIR
```

### Events Not Inserted

**Check load report:**
```bash
jq . wikipedia-ingestion/logs/load_report_*.json | less
```

**Check validation errors:**
```bash
jq '.by_strategy' wikipedia-ingestion/logs/load_report_*.json
```

### Duplicate Events

Loader automatically deduplicates. Check load report:
```bash
jq '.duplicates_removed' wikipedia-ingestion/logs/load_report_*.json
```

### Invalid Event Schema

**Validate before generating artifact:**
```python
from event_schema import validate_canonical_event

errors = validate_canonical_event(event_dict)
if errors:
    print(f"Validation errors: {errors}")
```

---

## File Structure

```
wikipedia-ingestion/
├── ingest_wikipedia.py          # Extract orchestrator (E)
├── database_loader.py            # Loader (L)
├── strategy_base.py              # Strategy interface
├── event_schema.py               # Canonical event schema
├── strategies/                   # Strategy implementations
│   ├── __init__.py
│   ├── list_of_years_strategy.py
│   ├── bespoke_events_strategy.py
│   └── list_of_time_periods/
│       └── list_of_time_periods_strategy.py
├── span_parsing/                 # Date parsing framework
│   ├── span.py                  # Span dataclass
│   ├── span_parser.py           # Main parser
│   ├── strategy.py              # Parser strategy interface
│   └── *_parser.py              # Parser implementations
├── logs/                         # Artifacts and reports
│   ├── events_*.json            # Artifacts (E output)
│   ├── load_report_*.json       # Load reports (L output)
│   ├── ingest_*.log             # Extract logs
│   └── exclusions_*.json        # Extract diagnostics
├── README.md                     # This file
└── SPEC.md                       # Implementation history
```

---

## Related Documentation

- **`SPEC.md`** - Implementation history and refactoring chronology
- **`EVENT_SCHEMA.md`** - Detailed event schema documentation
- **`../docs/README.md`** - Atomic reimport and enrichment architecture guide
- **`../scripts/atomic-reimport`** - Convenience script for full ETL pipeline
