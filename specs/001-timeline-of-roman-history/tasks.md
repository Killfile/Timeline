# Tasks: Timeline of Roman History Ingestion Strategy

**Feature Branch**: `001-timeline-of-roman-history`  
**Status**: Planning Phase  
**Estimated Scope**: ~40-50 tasks across 4 phases  
**Priority**: P1 (core feature delivering immediate timeline coverage)

---

## Phase 0: Infrastructure & Setup

### Shared Utilities Layer (timeline_common Module)

- [X] T001 Create `timeline_common/` directory as sibling to `api/` and `wikipedia-ingestion/`
- [X] T002 Create `timeline_common/__init__.py` with module initialization
- [X] T003 [P] Move `api/event_key.py` to `timeline_common/event_key.py` with import compatibility layer in api/
- [X] T004 [P] Create `timeline_common/tests/` directory with `__init__.py`
- [X] T005 [P] Create `timeline_common/tests/test_event_key.py` - unit tests for SHA-256 event key computation
- [X] T006 Update `api/` to import event_key from `timeline_common` (backward compatibility)
- [X] T007 Update `wikipedia-ingestion/` imports to use `timeline_common.event_key`
- [X] T008 Verify pytest discovers tests in `timeline_common/tests/`
- [X] **CHECKLIST: event_key.py is in timeline_common and all uses of event_key.py now import from timeline_common** (Verifies T003+T006+T007)

### Specification & Design Documentation

- [X] T009 Create `specs/001-timeline-of-roman-history/design-notes.md` for architecture decisions
- [X] T010 Document rowspan handling strategy with ASCII diagrams in design-notes.md
- [X] T011 Create test fixtures directory: `wikipedia-ingestion/strategies/timeline_of_roman_history/tests/fixtures/`

---

## Phase 1: Research & Design

### Wikipedia Page Structure Analysis

- [X] T012 [P] Fetch actual Wikipedia page HTML and analyze table structure
- [X] T013 [P] Document actual column count, column order (Year | Date | Event), and rowspan patterns
- [X] T014 [P] Extract sample HTML with 3-5 representative table rows (including rowspan rows)
- [X] T015 [P] Create `fixtures/sample_html_6th_century_bc.html` with representative 6th century BC data
- [X] T016 [P] Create `fixtures/sample_html_1st_century_ad.html` with BC→AD transition data
- [X] T017 [P] Create `fixtures/sample_html_byzantine.html` with Byzantine period data
- [X] T018 Document edge cases found: month-only dates, legendary events, embedded ranges
- [X] T019 Verify all 8 date format variations present in actual data

### TableRowDateParser Design

- [X] T020 Design `TableRowDateParser` class structure and method signatures in design-notes.md
- [X] T021 Document rowspan inheritance algorithm: how to track year context by row index
- [X] T022 Design regex patterns for month parsing ("January", "1", "01" variants)
- [X] T023 Design BC/AD detection and propagation rules for rowspan blocks
- [X] T024 Map actual Wikipedia column indices (determine which column is Year, Date, Event)
- [X] T025 Document confidence level assignment rules for each date format variant

### RomanEvent Domain Model Design

- [X] T026 [P] Document RomanEvent field mapping to HistoricalEvent schema
- [X] T027 [P] Design title generation from event description (first 50-70 chars)
- [X] T028 [P] Design precision/confidence assignment logic per edge case
- [X] T029 [P] Document event_key computation: which fields are included in SHA-256 hash

---

## Phase 2: Foundational Components

### Timeline Common Module Completion

- [X] T030 [P] Run `pytest timeline_common/tests/test_event_key.py` - all tests pass
- [X] T031 [P] Verify both `api/` and `wikipedia-ingestion/` can import from timeline_common
- [X] T032 [P] Document timeline_common module in README.md

### TableRowDateParser Implementation

- [X] T033 Create `wikipedia-ingestion/span_parsing/table_row_date_parser.py`
- [X] T034 Implement `parse_year_column(text: str) → tuple[int, bool]` (returns year, is_bc)
- [X] T035 Implement `parse_month_day_column(text: str) → tuple[int | None, int | None]` (month, day)
- [X] T036 Implement `compose_date()` to return RomanEvent-compatible dict with precision/confidence
- [X] T037 Implement rowspan context tracking class `RowspanContext` to inherit years to sub-rows
- [X] T038 Create `wikipedia-ingestion/span_parsing/tests/test_table_row_date_parser.py`
- [X] T039 Unit test: parse_year_column with "509 BC" → (509, True)
- [X] T040 Unit test: parse_year_column with "AD 10" → (10, False)
- [X] T041 Unit test: parse_year_column with "112" (bare number) → (112, False)
- [X] T042 Unit test: parse_month_day_column with "January 1" → (1, 1)
- [X] T043 Unit test: parse_month_day_column with "July" → (7, None)
- [X] T044 Unit test: parse_month_day_column with "" → (None, None)
- [X] T045 Unit test: rowspan inheritance - year applies to 3 rows without explicit year cell
- [X] T046 Unit test: BC/AD designation from year cell propagates to all rowspan rows
- [X] T047 Unit test: compose_date returns dict with correct start_year, start_month, precision, confidence
- [X] T048 Unit test: edge case - month-only date sets precision to `SpanPrecision.MONTH_ONLY`
- [X] T049 Unit test: edge case - legendary date (pre-509 BC) sets confidence to "legendary"
- [X] T050 [P] Run `pytest wikipedia-ingestion/span_parsing/tests/test_table_row_date_parser.py` - all pass
- [X] T051 [P] Code coverage check - TableRowDateParser >95% coverage

### RomanEvent Domain Model

- [X] T052 Create `wikipedia-ingestion/span_parsing/roman_event.py`
- [X] T053 Define `RomanEvent` dataclass with fields: year, month, day, is_bc, title, description, source, category, confidence_level, precision, event_key, span_match_notes
- [X] T054 Implement `generate_title(description: str) → str` - extract first 50-70 chars
- [X] T055 Implement `compute_event_key(self) → str` using event key computation
- [X] T056 Implement `to_historical_event(self) → HistoricalEvent` conversion for JSON export
- [X] T057 Create `wikipedia-ingestion/span_parsing/tests/test_roman_event.py`
- [X] T058 Unit test: RomanEvent with year=509, is_bc=True creates correct event_key
- [X] T059 Unit test: RomanEvent idempotency - same input → same event_key across runs
- [X] T060 Unit test: to_historical_event() returns HistoricalEvent-compatible object
- [X] T061 Unit test: title generation truncates to 50-70 chars correctly
- [X] T062 [P] Run `pytest wikipedia-ingestion/span_parsing/tests/test_roman_event.py` - all pass

---

## Phase 3: Strategy Implementation

### TimelineOfRomanHistoryStrategy Class

- [X] T063 Create `wikipedia-ingestion/strategies/timeline_of_roman_history/timeline_of_roman_history_strategy.py`
- [X] T064 Implement class extending `IngestionStrategy` base class
- [X] T065 Implement `fetch(self) → FetchResult` using `ingestion_common.get_html()`
- [X] T066 Implement `parse(self) → ParseResult` with BeautifulSoup table extraction
- [X] T067 Implement table parsing logic:
  - Extract all `<table>` elements from HTML
  - For each table, iterate `<tr>` elements
  - Extract year column (handling rowspan)
  - Extract date column
  - Extract event description column
  - Use RowspanContext to track inherited years
  - Create RomanEvent for each row
- [X] T068 Implement error handling for malformed rows (log warning, skip row, continue)
- [X] T069 Implement BC/AD detection from year cell content
- [X] T070 Implement rowspan inheritance: apply year cell to N rows based on rowspan="N"
- [X] T071 Implement `generate_artifact(self) → ArtifactData` to produce JSON per import_schema.json
- [X] T072 Implement artifact metadata: event_count, parsed_rows, skipped_rows, parse_duration_ms
- [X] T073 Implement artifact logging: all events with metadata about parsing decisions
- [X] T074 Implement confidence distribution in artifact metadata
- [X] T075 Create `wikipedia-ingestion/strategies/timeline_of_roman_history/tests/test_timeline_of_roman_history_strategy.py`

### Strategy Testing

- [X] T076 Unit test: fetch() returns FetchResult with HTML content
- [X] T077 Unit test: fetch() mocks HTTP response via unittest.mock (no real network calls)
- [X] T078 Unit test: parse() with sample_html_6th_century_bc.html extracts all events
- [X] T079 Unit test: parse() correctly handles rowspan inheritance across 5 rows
- [X] T080 Unit test: parse() logs warnings for inherited year rows
- [X] T081 Unit test: parse() with BC→AD transition data creates correct is_bc flags
- [X] T082 Unit test: parse() with Byzantine data includes events with "Roman History" category
- [X] T083 Unit test: parse() with legendary events (pre-509 BC) sets confidence="legendary"
- [X] T084 Unit test: parse() with malformed row logs error and skips row without stopping
- [X] T085 Unit test: generate_artifact() produces valid JSON per import_schema.json schema
- [X] T086 Unit test: generate_artifact() includes confidence distribution metadata
- [X] T087 [P] Run full strategy test suite with multiple sample HTML fixtures
- [X] T088 Code coverage check - Strategy >90% coverage (Result: 96% coverage, 118 statements)

### Integration with Factory

- [X] T089 Update `wikipedia-ingestion/ingestion_strategy_factory.py` to register `TimelineOfRomanHistoryStrategy`
- [X] T090 Add "timeline_of_roman_history" case to factory's strategy selector
- [X] T091 Unit test: factory can instantiate strategy by name "timeline_of_roman_history"
- [X] T092 Unit test: strategy integrates with orchestrator (`ingest_wikipedia.py` calls it correctly)

---

## Phase 4: Validation & Integration

### Artifact Schema Validation

- [X] T093 Create fixture: `expected_events_6th_century_bc.json` (expected output for sample HTML)
- [X] T094 Create fixture: `expected_events_1st_century_ad.json` (expected output for AD data)
- [X] T095 Integration test: parse sample HTML → generate artifact → validate against import_schema.json
- [X] T096 Integration test: artifact event_count matches expected event count
- [X] T097 Integration test: all events have valid event_key values
- [X] T098 Integration test: BC dates have is_bc_start=True, AD dates have is_bc_start=False
- [X] T099 Integration test: legendary events have confidence="legendary"
- [X] T099b Schema validation: Verify generated JSON documents match `import_schema.json` schema using jsonschema validator

### End-to-End Testing

- [X] T100 Create test for idempotency: run strategy twice, verify identical event_keys
- [X] T101 Integration test: run full strategy on actual Wikipedia page (with network mock)
- [X] T102 Integration test: verify strategy completes in <30 seconds
- [X] T103 Integration test: verify no events are dropped due to parse errors
- [X] T104 Integration test: verify summary report is generated with counts

### Documentation

- [X] T105 Create `wikipedia-ingestion/strategies/timeline_of_roman_history/README.md`
- [X] T106 Document TableRowDateParser design decisions in README
- [X] T107 Document confidence level assignment rules in README
- [X] T108 Document edge cases handled (legendary dates, rowspan, month-only, etc.)
- [X] T109 Create usage example in README: how to run ingestion via orchestrator
- [X] T110 Update main `wikipedia-ingestion/README.md` to list new strategy

### Cross-Service Testing

- [X] T111 [P] Test that `timeline_common.event_key` works with both `api/` and `wikipedia-ingestion/`
- [X] T112 [P] Verify no import circular dependencies between api/ and wikipedia-ingestion/
- [ ] T113 [P] Run all tests: `pytest wikipedia-ingestion/ timeline_common/` - 100% pass
- [ ] T114 [P] Run full test suite including existing strategies to verify no regressions

### Polish & Final Checks

- [ ] T115 Code review checklist:
  - All functions have docstrings
  - All public methods documented with Args, Returns, Raises
  - Type hints on all functions
  - No hardcoded constants outside of source definitions
- [ ] T116 Linting: `pylint wikipedia-ingestion/strategies/timeline_of_roman_history/`
- [ ] T117 Formatting: `black wikipedia-ingestion/strategies/timeline_of_roman_history/`
- [ ] T118 Static type check: `mypy wikipedia-ingestion/strategies/timeline_of_roman_history/`
- [ ] T119 Final validation: artifact JSON conforms to `import_schema.json` schema
- [ ] T120 Performance validation: ingestion completes <30 seconds on actual Wikipedia page
- [ ] T121 Create PR summary document linking to spec and clarifications

---

## Task Dependency Graph

```
Phase 0: Setup
  T001-T008 (timeline_common module)
  T009-T011 (documentation)
    ↓
Phase 1: Research & Design
  T012-T019 (Wikipedia analysis) [parallel]
  T020-T025 (TableRowDateParser design) [parallel after T019]
  T026-T029 (RomanEvent design) [parallel]
    ↓
Phase 2: Implementation
  T030-T032 (timeline_common completion)
  T033-T051 (TableRowDateParser)
  T052-T062 (RomanEvent)
    ↓
Phase 3: Strategy
  T063-T075 (TimelineOfRomanHistoryStrategy)
  T076-T088 (Strategy testing)
  T089-T092 (Factory integration)
    ↓
Phase 4: Validation
  T093-T099 (Artifact validation)
  T100-T105 (End-to-end testing)
  T106-T111 (Documentation)
  T112-T122 (Cross-service testing & polish)
```

## Parallel Execution Opportunities

**Phase 0**: All tasks can run in parallel (independent module)

**Phase 1 (Research)**:
- T012-T019 (Wikipedia analysis) can run in parallel
- T020-T025 (Parser design) after T019
- T026-T029 (RomanEvent design) in parallel with T020

**Phase 2**:
- T033-T051 (TableRowDateParser) and T052-T062 (RomanEvent) can start in parallel after Phase 1

**Phase 3**:
- T063-T075 (Strategy impl) requires both T033 and T052 complete
- T076-T088 (Strategy testing) in parallel with implementation
- T089-T092 (Factory) after strategy complete

**Phase 4**:
- T093-T099 (Artifact validation) can start once T075 complete
- T100-T105 (E2E testing) can start once T092 complete
- T106-T111 (Docs) in parallel with testing
- T112-T122 (Final checks) after T115 complete

---

## Definition of Done

✅ All tasks completed
✅ All tests pass (pytest coverage >90%)
✅ No linting errors (pylint, black, mypy)
✅ Artifact validates against import_schema.json
✅ Idempotency verified (multiple runs → identical event keys)
✅ Documentation complete
✅ No circular dependencies
✅ Performance validated (<30 seconds ingestion)
✅ PR created with clarifications and design decisions documented
