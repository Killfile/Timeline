# Feature Specification: Timeline of Roman History Ingestion Strategy

**Feature Branch**: `001-timeline-of-roman-history`  
**Created**: January 27, 2026  
**Status**: Draft  
**Input**: Build a new Wikipedia ingestion strategy for https://en.wikipedia.org/wiki/Timeline_of_Roman_history called "Timeline of Roman History"

## Shared Architecture & Patterns

This implementation follows the established ingestion strategy pattern from Timeline of Food and Wars strategies. See [ROMAN_HISTORY_SHARED_PATTERNS.md](../wikipedia-ingestion/ROMAN_HISTORY_SHARED_PATTERNS.md) for detailed guidance on reusable components.

### Components to Reuse:
- `IngestionStrategy` base class (3-phase: fetch, parse, generate_artifact)
- `ingestion_common.get_html()` for HTTP fetching with built-in caching, retry logic, and URL canonicalization
- `ingestion_common.log_info()` / `log_error()` for centralized logging
- `HistoricalEvent` base schema for database storage
- Event key generation pattern (MD5: date|title|source) for deterministic deduplication
- Title generation (first 50-70 chars) and precision/confidence tracking
- Testing pattern (pytest + unittest.mock for HTTP mocking)
- Artifact output conforming to `import_schema.json`

### Components to Create (Roman-Specific):
- **`TableRowDateParser`**: New span parsing strategy for columnar date extraction (year + month/day from separate columns)
- **`RomanEvent`**: Domain-specific event model extending HistoricalEvent with month/day fields
- **`TimelineOfRomanHistoryStrategy`**: Strategy implementation orchestrating table parsing

## Clarifications

### Session 2026-01-28

- Q: How should legendary period events (pre-509 BC kingdom era) be handled? → A: Include legendary events with separate `confidence="legendary"` marking for explicit categorization, enabling full timeline coverage while signaling historical uncertainty
- Q: When a row lacks a year but rowspan tracking suggests inheritance, should parser use inherited value? → A: Use inherited year and log warning (non-blocking) to capture data while flagging edge cases for review
- Q: When event description embeds a year (e.g., "Battle of Issus (194)") differing from table row year, which is canonical? → A: Table row year is canonical; log warning if embedded dates differ but store table year as authoritative
- Q: How should events with embedded date ranges (e.g., "First Punic War (264-241 BC)") be handled? → A: Ignore ranges in event text, use only table row year as point-in-time event
- Q: Should Byzantine Empire events (6th-15th century) be included in ingestion? → A: Include Byzantine events as part of documented Roman continuity; use same category "Roman History"
- Q: How should month-only dates (e.g., "July") be represented in precision field? → A: Use `SpanPrecision.MONTH_ONLY` enum to leverage existing precision constants in codebase
- Q: How should event keys be computed for idempotent deduplication across reimports? → A: Use shared `timeline_common.event_key.compute_event_key(title, start_year, end_year, description)` which produces SHA-256 hash via `{title}|{start_year}|{end_year}|{description}`. New `timeline_common/` module created as sibling to `api/` and `wikipedia-ingestion/` to resolve dependency graph

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest Roman History Events from Tabular Structure (Priority: P1)

The system should discover and extract historical Roman events from the Wikipedia article "Timeline of Roman History" and load them into the database so they appear on the main timeline visualization alongside other historical events.

**Why this priority**: This is the core feature that delivers immediate value—populating the timeline with Roman history data spanning from the earliest kingdoms through the later empire.

**Independent Test**: The feature can be fully tested by running the ingestion strategy and verifying that:
1. Events are extracted from the tabular structure in the Wikipedia page
2. Events are loaded into the database via the standard ETL pipeline
3. Events appear on the frontend timeline with proper dates and descriptions
4. Each event has proper date formatting (BC/AD handling, year/month/day composition)

**Acceptance Scenarios**:

1. **Given** the Timeline of Roman History Wikipedia article with tabular data, **When** the ingestion strategy is run, **Then** all discoverable events are extracted from table rows into the database
2. **Given** extracted events, **When** the frontend queries the timeline, **Then** Roman events are displayed with other events in chronological order
3. **Given** table rows with year in one column and month/day in another, **When** they are ingested, **Then** dates are correctly composed and stored

---

### User Story 2 - Parse Table-Based Date Columns (Priority: P2)

The Roman history data is structured in tables with year and month/day in separate columns. The system must handle this columnar structure by extracting year from one column and optional month/day information from another, then composing them into complete dates.

**Why this priority**: The tabular structure is fundamental to the Roman data format; without proper column parsing, dates cannot be accurately extracted.

**Independent Test**: Can be tested by:
1. Verifying that year values are correctly extracted from the year column
2. Confirming that month/day information (where present) is parsed from separate columns
3. Validating that BC/AD designation is correctly applied
4. Checking that composed dates match the source table

**Acceptance Scenarios**:

1. **Given** a table row with year in one column and "January 1" in another, **When** parsed, **Then** the complete date "January 1, [year]" is composed and stored
2. **Given** a table row with only a year value and no month/day, **When** parsed, **Then** the year is stored with appropriate precision (YEAR_ONLY)
3. **Given** Roman era dates with BC designation, **When** parsed, **Then** dates are stored with correct BC flag and chronological ordering

---

### User Story 3 - Support Date Inference for Uncertain Periods (Priority: P2)

Some events may have imprecise dates (e.g., "mid-3rd century", "uncertain date"). The system should parse these gracefully, extracting the most reliable date information available and recording confidence levels.

**Why this priority**: Roman history contains many events with uncertain or approximate dates; proper handling ensures high data quality while preserving information.

**Independent Test**: Can be tested by:
1. Verifying that approximations ("mid-", "late-", "early-") are correctly parsed
2. Confirming that uncertain dates are logged with lower confidence
3. Validating that events are still usable even with partial date information

**Acceptance Scenarios**:

1. **Given** an event dated "mid-3rd century AD", **When** parsed, **Then** it is assigned a date range (200-299 AD) with marked confidence/uncertainty
2. **Given** an event with "uncertain" or "circa" designation, **When** parsed, **Then** it is stored with appropriate metadata noting the uncertainty

---

### User Story 4 - Data Quality and Deduplication (Priority: P3)

As a maintainer, I want the ingestion strategy to log errors, skip malformed entries, and ensure no duplicate events are created even when the strategy is run multiple times.

**Why this priority**: Ensures reliability, maintainability, and data integrity.

**Independent Test**: Can be tested by:
1. Introducing malformed table rows and verifying errors are logged
2. Running the strategy multiple times and confirming events are not duplicated
3. Validating that partial/incomplete rows are properly skipped

**Acceptance Scenarios**:

1. **Given** a malformed table row, **When** the import is run, **Then** the row is skipped and an error is logged
2. **Given** the strategy is run twice, **When** events are processed, **Then** no duplicate events appear in the database
3. **Given** a valid event row, **When** imported, **Then** it is successfully inserted even if other rows fail

---

### Corner Cases & HTML Table Structure

**Critical Discovery**: Wikipedia's Timeline of Roman History uses `rowspan` attributes to span year cells across multiple rows:
```html
<td rowspan="5" valign="top"><a>509 BC</a></td>
```

This creates the "orphaned rows" without year values—they inherit from the rowspan cell above. The parser must:

1. **Handle rowspan-based year inheritance**: When parsing `<tr>` elements within a rowspan, the year cell appears only in the first row; subsequent rows must look to the parent rowspan cell to find the year.
   - Recommendation: Use BeautifulSoup's row index to determine which rows are "spanned" by a year cell
   - Track the current year context and apply it to rows beneath a rowspan="N" cell

2. **Support date-only sub-events**: Many rows have date + event but no year (e.g., "13 September: Temple dedication"). These are sub-events within a year block.
   - Parsing strategy: Capture the year from rowspan, combine with month/day from date column
   - Example: rowspan year="509 BC" + date="13 September" → year=509, month=9, day=13, is_bc=true

3. **Handle inconsistent date column formats**:
   - Full format: "16 August" or "16 August 79" (with optional year)
   - Month-only: "July", "December"
   - Empty: Many rows have blank date columns (use year only)
   - Range: "6 May" ... "4 September" (start/end dates across years)

4. **Handle BC/AD designation and transitions**:
   - BC designator appears inline in year cell: `<a>509 BC</a>`
   - AD dates use "AD" prefix: `AD 10`, `AD 14` (early 1st century) or bare numbers: `112`, `115` (later centuries)
   - Transition: Rows with "1 BC" followed by "AD 10" (no year 0)

5. **Uncertain/approximate dates**:
   - Early kingdom period (7th-6th BC): Dates marked as "legendary" in article intro
   - Approximate indicators: "c." (circa), "about", "probably"
   - Recommendation: Record confidence level (explicit, inferred, approximate, contentious)

6. **Event text with internal date ranges**:
   - Example: "Battle of Issus (194): Niger's forces defeated..." (year embedded in event description)
   - Recommendation: Extract year from year column; if event text contains alternate dates, log as warning

### Edge Cases

- What happens when a table row has a year but no month/day information? → Use precision=`SpanPrecision.YEAR_ONLY`
- How should very ancient dates (e.g., "753 BC" for Rome's founding) be handled? → Use confidence=inferred or approximate; note in metadata
- How are events with date ranges ("264-241 BC") parsed when spread across columns? → Extract start year from range, store as start_year/end_year in HistoricalEvent
- What if the Wikipedia page restructures its table format? → Parser should log warnings if expected columns are missing or in unexpected order
- How are legendary or semi-legendary events (pre-historical Roman kingdom period) dated and labeled? → Record confidence metadata and precision levels

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement `IngestionStrategy` interface with three phases: fetch, parse, generate_artifact
- **FR-002**: System MUST fetch the Wikipedia article at https://en.wikipedia.org/wiki/Timeline_of_Roman_history using shared `ingestion_common.get_html()` framework (handles caching, retries, URL canonicalization)
- **FR-003**: System MUST extract all event entries from the article's tabular structures using BeautifulSoup4
- **FR-004**: System MUST implement `TableRowDateParser` (new span parsing strategy) to extract year values from year column(s), including handling HTML `rowspan` attributes where year cells span multiple `<tr>` elements
- **FR-004a**: System MUST track rowspan context by row index to apply inherited year values to rows without explicit year cells (sub-events under a rowspan year block)
- **FR-005**: System MUST use `TableRowDateParser` to extract month/day information from separate column(s) when present, handling formats: "Day Month", "Month", "Day-Month", or empty (year-only)
- **FR-006**: System MUST compose complete dates from year and optional month/day components, storing precision level using `SpanPrecision` enum (`YEAR_ONLY`, `MONTH_ONLY`, `EXACT_DATE`)
- **FR-007**: System MUST handle BC/AD date conversions correctly using project conventions (BC dates count backward; cutover at 1 BC → 1 AD; detect AD prefix in early centuries and bare numbers in later periods)
- **FR-007a**: System MUST detect BC/AD designation from year cell content (e.g., "509 BC", "AD 10") and propagate to all rows under a rowspan block
- **FR-008**: System MUST parse approximate/uncertain date indicators ("c.", "about", "probably", "mid-", "circa", "uncertain") and record confidence metadata (explicit, inferred, approximate, contentious)
- **FR-008a**: System MUST extract date ranges from event text (e.g., "(264-241 BC)") when present and store as start_year/end_year in HistoricalEvent
- **FR-009**: System MUST generate event titles from first 50-70 characters of description (reuse Food strategy pattern)
- **FR-010**: System MUST generate deterministic event keys using `timeline_common.event_key.compute_event_key(title, start_year, end_year, description)` which produces SHA-256 hash via `{title}|{start_year}|{end_year}|{description}` format for deduplication
- **FR-011**: System MUST generate JSON artifact file conforming to `import_schema.json` schema, including metadata about parsing (timing, confidence distribution, undated event summary)
- **FR-012**: System MUST convert all events to `HistoricalEvent` instances for PostgreSQL storage via standard schema
- **FR-013**: System MUST assign category "Roman History" to all events from this source
- **FR-014**: System MUST set source field to "Timeline of Roman History" for all events
- **FR-015**: System MUST exclude events with no parseable date and no context from database insertion (log as warning in info logs, record in error logs)
- **FR-016**: System MUST use centralized logging via `ingestion_common.log_info()` / `log_error()` for all operations
- **FR-017**: System MUST produce strategy-specific log documenting parsing decisions, table structure, and any ambiguities
- **FR-018**: System MUST generate summary report including counts of successfully parsed rows, skipped rows, parse time, and errors
- **FR-019**: System MUST be idempotent (multiple runs produce identical event keys and avoid duplicates)
- **FR-020**: System MUST integrate with orchestrator (`ingest_wikipedia.py`) and be registered in `IngestionStrategyFactory`

### Key Entities *(include if feature involves data)*

- **RomanEvent** (domain model, similar to FoodEvent):
  - event_key: SHA-256 hash computed via `timeline_common.event_key.compute_event_key(title, start_year, end_year, description)` for deterministic deduplication across reimports
  - source: "Timeline of Roman History" (constant)
  - year: Year component (numeric, can be BC or AD)
  - month (optional): Month number (1-12)
  - day (optional): Day of month (1-31)
  - is_bc: Boolean flag indicating BC dates
  - confidence_level: "explicit" | "inferred" | "approximate" | "contentious" | "legendary" | "fallback"
  - title: First 50-70 characters of description
  - description: Full event text
  - category: "Roman History" (constant)
  - precision: `SpanPrecision` enum value (`EXACT_DATE` | `MONTH_ONLY` | `YEAR_ONLY` | `APPROXIMATE` | `UNCERTAIN`)
  - span_match_notes: How the date was extracted from the table
  - Converts to `HistoricalEvent` for database insertion

- **HistoricalEvent** (base schema, reused from existing pattern):
  - Stores in PostgreSQL via `database_loader.py`
  - Standard fields: start_year, end_year, is_bc_start, is_bc_end, start_month, start_day, end_month, end_day, title, description, source, category

- **TableRowDateParser** (new span parsing strategy):
  - parse_year_column(text, is_bc) → (year: int, is_bc: bool)
  - parse_month_day_column(text) → (month: int | None, day: int | None)
  - compose_date(year, is_bc, month, day) → HistoricalEvent with precision/confidence
  - Located in: `wikipedia-ingestion/span_parsing/table_row_date_parser.py`

## Success Criteria *(mandatory)*

- 100% of valid timeline events from the Wikipedia table(s) are extracted and stored in the system.
- Column-based dates (year + month/day) are correctly composed and stored with appropriate `SpanPrecision` enum values.
- All BC/AD dates are parsed and stored accurately with correct chronological ordering.
- Approximate/uncertain dates are parsed and marked with confidence metadata.
- No duplicate or partial data is present after import, even if strategy is run multiple times.
- Errors and skipped rows are logged with actionable messages.
- Strategy completes ingestion in <30 seconds for the full article.
- A summary report is generated documenting rows parsed, rows skipped, and any errors encountered.

## Technical Context

**Architecture Pattern**: Follows `IngestionStrategy` interface (established in Timeline of Food and Wars strategies)

**Implementation Structure**:
```
wikipedia-ingestion/
├── span_parsing/
│   └── table_row_date_parser.py        (NEW: columnar date parser)
├── strategies/
│   ├── timeline_of_roman_history/
│   │   ├── __init__.py
│   │   ├── roman_event.py              (Domain model with year/month/day)
│   │   ├── timeline_of_roman_history_strategy.py  (Main strategy)
│   │   ├── README.md
│   │   └── tests/
│   │       ├── test_table_row_date_parser.py
│   │       ├── test_roman_event.py
│   │       ├── test_timeline_of_roman_history_strategy.py
│   │       └── fixtures/
│   │           ├── sample_html.py
│   │           └── expected_events.json
│   └── ingestion_strategy_factory.py   (UPDATE: register TimelineOfRomanHistoryStrategy)
├── ingestion_common.py                 (REUSE: get_html, log_info, log_error)
├── historical_event.py                 (REUSE: base schema)
└── import_schema.json                  (CONFORM: artifact validation)

timeline_common/                         (NEW: shared utilities sibling module)
├── __init__.py
├── event_key.py                        (MOVE from api/: SHA-256 event key computation)
└── tests/
    └── test_event_key.py
```

**Language/Version**: Python 3.11+

**Shared Dependencies** (reused from existing strategies):
- BeautifulSoup4 (HTML/table parsing)
- requests (HTTP via `ingestion_common.get_html()`)
- pytest + unittest.mock (testing)

**New Dependencies**: None (leverage existing stack)

**Storage**: PostgreSQL via `HistoricalEvent` schema (same as other strategies)

**Testing Framework**: pytest with mocked HTTP responses (follow Timeline of Food pattern)

**Performance Goals**: Ingestion completes in <30 seconds; database load in <5 seconds

**Output**: JSON artifact conforming to `import_schema.json` with:
- strategy: "TimelineOfRomanHistory"
- event_count: ~2,500-4,000 (estimated)
- metadata: timing, confidence distribution, undated event summary
- events: array of events with start_year, end_year, start_month, start_day, end_month, end_day, precision, weight, etc.

**Integration Points**:
- Shared Utilities: `timeline_common.event_key` provides deterministic event key computation for both `api/` and `wikipedia-ingestion/`
- Orchestrator: `ingest_wikipedia.py` calls fetch → parse → generate_artifact
- Database: `database_loader.py` loads artifact JSON into PostgreSQL
- Factory: `IngestionStrategyFactory.create_strategy()` instantiates strategy by name

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Architecture & Design

- ✅ **Microservices Separation**: Strategy isolated in `wikipedia-ingestion/strategies/timeline_of_roman_history/`
- ✅ **Explicit Interfaces**: Implements standard `IngestionStrategy` base class (fetch, parse, generate_artifact)
- ✅ **HTTP Framework**: Reuses `ingestion_common.get_html()` (handles caching, retries, canonicalization)
- ⚠️ **New Table Row Parser**: `TableRowDateParser` (new but narrow scope—columnar date extraction only)
- ✅ **Deduplication**: Uses established MD5(date|title|source) pattern
- ✅ **Test-First Development**: REQUIRED—unit tests covering table parsing, column extraction, date composition, BC/AD, edge cases
- ✅ **Logging & Observation**: Reuses `log_info()` / `log_error()` from `ingestion_common.py`
- ✅ **Artifact Schema**: Conforms to `import_schema.json` with month/day field support
- ✅ **Ingestion Architecture**: Follows Extract-Translate-Load (fetch → parse → artifact) established in food/wars strategies

### Complexity Analysis

**LOW COMPLEXITY** — Reuses 90% of established patterns:
- HTTP fetching: inherited from `ingestion_common`
- Event model: follows FoodEvent pattern
- Deduplication: reuses event key logic
- Logging: reuses centralized logging
- Testing: reuses pytest + mock pattern
- Artifact output: conforms to existing schema

**New Work Scoped to**: `TableRowDateParser` (pure function, well-defined inputs/outputs, testable in isolation)

## Assumptions

- The Wikipedia page contains primarily tabular data for historical events
- Year values are consistently in a dedicated column, month/day values in separate column(s)
- Date values are primarily numeric (e.g., "753" for 753 BC, "14" for day 14)
- Network access to Wikipedia is available; `ingestion_common.get_html()` handles transient failures
- HistoricalEvent schema and database infrastructure are stable (reuse existing)
- Legendary/semi-legendary dates (pre-historical kingdom period) are handled with appropriate precision/confidence markers
- Strategy registration in `IngestionStrategyFactory` will be handled as part of implementation

## Next Steps (Phase 0 & Phase 1 Research)

1. **Examine Wikipedia page structure**: Review actual table columns, date formats, data patterns
2. **Design TableRowDateParser**: Identify column indices, parsing rules, edge cases from real data
3. **Create test fixtures**: Extract sample HTML and expected event output for testing
4. **Implement RomanEvent model**: Follow FoodEvent pattern with month/day fields
5. **Implement strategy**: Orchestrate fetch → table parsing → event extraction → artifact generation
6. **Register in factory**: Update `IngestionStrategyFactory` for integration
7. **Validate artifact**: Confirm output against `import_schema.json`
