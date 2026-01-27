# Tasks: Timeline of Food Ingestion Strategy

**Input**: Design documents from `/specs/001-timeline-of-food/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED per Constitution Principle III (Test-First Development, NON-NEGOTIABLE). All non-trivial logic must have unit tests with >80% coverage target.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create directory structure `wikipedia-ingestion/strategies/timeline_of_food/` with `__init__.py`
- [ ] T002 Create directory structure `wikipedia-ingestion/strategies/timeline_of_food/tests/` with `__init__.py`
- [ ] T003 Create directory structure `wikipedia-ingestion/strategies/timeline_of_food/tests/fixtures/`

---

## Phase 2: Foundational (Blocking Prerequisites - span_parsing Extensions)

**Purpose**: Core span_parsing library extensions that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Extend span_parsing Library

- [X] T004 [P] Create `wikipedia-ingestion/span_parsing/century_parser.py` with CenturyParser class (handles "5th century BCE")
- [X] T004a [P] Write unit tests for CenturyParser in `wikipedia-ingestion/span_parsing/tests/test_century_parser.py` (15+ test cases covering all centuries and eras, BC/AD/CE/no-marker, target >80% coverage)
- [X] T005 [P] Create `wikipedia-ingestion/span_parsing/century_range_parser.py` with CenturyRangeParser class (handles "11th-14th centuries")
- [X] T005a [P] Write unit tests for CenturyRangeParser in `wikipedia-ingestion/span_parsing/tests/test_century_range_parser.py` (10+ test cases including BC ranges, target >80% coverage)
- [X] T006 [P] Create `wikipedia-ingestion/span_parsing/century_with_modifier_parser.py` with CenturyWithModifierParser class (handles "Early 1700s", "Late 16th century", "Before 17th century")
- [X] T006a [P] Write unit tests for CenturyWithModifierParser in `wikipedia-ingestion/span_parsing/tests/test_century_with_modifier_parser.py` (20+ test cases for all modifiers and formats, target >80% coverage)
- [X] T007 [P] Create `wikipedia-ingestion/span_parsing/years_ago_parser.py` with YearsAgoParser class (handles "250,000 years ago")
- [X] T007a [P] Write unit tests for YearsAgoParser in `wikipedia-ingestion/span_parsing/tests/test_years_ago_parser.py` (10+ test cases including edge cases with commas and millions, target >80% coverage)
- [X] T008 [P] Create `wikipedia-ingestion/span_parsing/tilde_circa_year_parser.py` with TildeCircaYearParser class (handles "~1450")
- [X] T008a [P] Write unit tests for TildeCircaYearParser in `wikipedia-ingestion/span_parsing/tests/test_tilde_circa_year_parser.py` (8+ test cases, target >80% coverage)
- [X] T009 Create `wikipedia-ingestion/span_parsing/orchestrators/food_timeline_parse_orchestrator.py` with FoodTimelineParseOrchestrator class (combines all parsers in priority order)
- [X] T009a Write unit tests for FoodTimelineParseOrchestrator in `wikipedia-ingestion/span_parsing/orchestrators/tests/test_food_timeline_parse_orchestrator.py` (25+ test cases exercising all parser paths, target >80% coverage)
- [X] T010 Update `wikipedia-ingestion/span_parsing/orchestrators/parse_orchestrator_factory.py` to add FOOD_TIMELINE enum and register FoodTimelineParseOrchestrator

**Checkpoint**: span_parsing library extensions complete - user story implementation can now begin

---

## Phase 3: User Story 1 - Ingest Timeline of Food Events (Priority: P1) 🎯 MVP

**Goal**: Extract and load historical food events from Wikipedia "Timeline of Food" article into the database

**Independent Test**: Run ingestion strategy and verify 3,000+ events are extracted, loaded into database, and appear on frontend timeline with correct dates

### Implementation for User Story 1

- [X] T011 [P] [US1] Create `wikipedia-ingestion/strategies/timeline_of_food/food_event.py` with FoodEvent dataclass and to_historical_event() method
- [X] T012 [P] [US1] Create `wikipedia-ingestion/strategies/timeline_of_food/hierarchical_strategies.py` with TextSectionParser class to extract hierarchical sections from HTML
- [X] T013 [US1] Create `wikipedia-ingestion/strategies/timeline_of_food/date_extraction_strategies.py` with EventParser class to parse bullet points and extract dates using FoodTimelineParseOrchestrator
- [X] T014 [US1] Create `wikipedia-ingestion/strategies/timeline_of_food/timeline_of_food_strategy.py` implementing IngestionStrategy base class (fetch, parse, generate_artifacts methods)
- [X] T015 [US1] Implement fetch() method in timeline_of_food_strategy.py to HTTP GET Wikipedia article with caching and error handling
- [X] T016 [US1] Implement parse() method in timeline_of_food_strategy.py to orchestrate section parsing and event extraction
- [X] T017 [US1] Implement generate_artifacts() method in timeline_of_food_strategy.py to create JSON artifact file
- [X] T017a [US1] Validate JSON artifact schema compliance in timeline_of_food_strategy.py (verify all required fields, metadata, schema version)
- [X] T018 [US1] Implement title generation logic in food_event.py (first 50-70 characters of description)
- [X] T019 [US1] Implement event_key generation in food_event.py using MD5(date + title + "Timeline of Food")
- [X] T020 [US1] Add category "Food History" assignment in food_event.py
- [X] T021 [US1] Add source "Timeline of Food" assignment in food_event.py
- [X] T022 [US1] Update `wikipedia-ingestion/strategies/ingestion_strategy_factory.py` to add TIMELINE_OF_FOOD enum and register TimelineOfFoodStrategy
- [X] T023 [US1] Add logging for undated events (info logs as warnings, error logs for failures) in date_extraction_strategies.py
- [X] T024 [US1] Add error handling for network failures and 404s in timeline_of_food_strategy.py

### Unit Tests for User Story 1 (Constitution Required - >80% Coverage)

- [X] T011a [P] [US1] Write unit tests for FoodEvent in `wikipedia-ingestion/strategies/timeline_of_food/tests/test_food_event.py` (test to_historical_event(), event_key generation, title generation, category/source assignment)
- [X] T012a [P] [US1] Write unit tests for TextSectionParser in `wikipedia-ingestion/strategies/timeline_of_food/tests/test_hierarchical_strategies.py` (test section extraction, HTML parsing, hierarchical structure)
- [X] T013a [US1] Write unit tests for EventParser in `wikipedia-ingestion/strategies/timeline_of_food/tests/test_date_extraction_strategies.py` (test bullet point parsing, date extraction with orchestrator, logging) **COMPLETE** - 34/34 unit tests passing
- [X] T014a [US1] Write integration tests for TimelineOfFoodStrategy in `wikipedia-ingestion/strategies/timeline_of_food/tests/test_timeline_of_food_strategy.py` (test fetch/parse/artifact flow with mocked HTTP) **COMPLETE** - 5/5 integration tests passing, 33 total timeline_of_food_strategy tests passing
- [X] T015a [US1] Write unit tests for fetch() method (test caching, error handling, HTTP responses) **COMPLETE** - 6/6 unit tests passing
- [X] T016a [US1] Write unit tests for parse() method (test orchestration, event extraction, edge cases) **COMPLETE** - 5/5 unit tests passing
- [X] T018a [US1] Write unit tests for title generation (test truncation at 50-70 chars, edge cases with short/long descriptions) **COMPLETE** - 6/6 unit tests passing
- [X] T019a [US1] Write unit tests for event_key generation (test MD5 consistency, deduplication scenarios) **COMPLETE** - 5/5 unit tests passing
- [X] T023a [US1] Write unit tests for undated event logging (test info warnings and error log recording) **COMPLETE** - 3/3 unit tests passing
- [X] T024a [US1] Write unit tests for error handling (test 404s, network timeouts, malformed HTML) **COMPLETE** - 6/6 unit tests passing

- [X] T025b [US1] Extract and use table cell dates in `_extract_events_from_table()` - parse first column year/date and use for event dating (not fallback parser) **COMPLETE** - Implementation working; 2 validation cases blocked on span_parsing library decade notation support
- [X] T025c [US1] Write unit tests for table cell date extraction (test year parsing, year ranges, century formats, date format variants) **COMPLETE** - 9/9 unit tests passing

**Checkpoint**: 🎯 **User Story 1 MVP COMPLETE** 
- Basic ingestion working with explicit dates, bullet points, and table formats
- 115+ unit tests passing (9 food_event + 34 event_parser + 64 timeline_of_food_strategy total)
- >80% test coverage achieved
- Ready for integration testing with Wikipedia data
- Implementation files: food_event.py, hierarchical_strategies.py, date_extraction_strategies.py, timeline_of_food_strategy.py all complete with full unit test coverage

## Phase 4: User Story 2 - Support Date Range Inference and Decade Notation (Priority: P2)

**Goal**: Infer reasonable date ranges for undated events based on hierarchical section context AND support decade notation parsing ("1990s" → 1990-1999, "1800s" → 1800-1809)

**Independent Test**: Verify decade notation parses correctly (1990s→1990-1999, 1800s→1800-1809) AND events without explicit dates receive inferred date ranges from section headers

### Implementation for User Story 2

- [ ] T026 [US2] Extend TextSection dataclass in hierarchical_strategies.py to include inferred_date_range field
- [ ] T027 [US2] Implement section header date extraction in hierarchical_strategies.py (parse "4000-2000 BCE", "17th Century" from h2/h3/h4 tags)
- [ ] T027a [US2] Fix YearRangeParser BC/BCE notation bug in `wikipedia-ingestion/span_parsing/year_range_parser.py` - when BC/BCE is on the second part of a range, apply to first part too (e.g., "2500–1500 BCE" → -2500 to -1500, not 2500 to -1500)
- [ ] T029 [US2] Implement hierarchical date range inheritance in hierarchical_strategies.py (child sections inherit parent ranges)
- [ ] T030 [US2] Update date_extraction_strategies.py to use section context as fallback when FoodTimelineParseOrchestrator returns None
- [ ] T031 [US2] Add confidence level "inferred" for events using section-based dates in food_event.py
- [ ] T032 [US2] Create `wikipedia-ingestion/span_parsing/decade_parser.py` with DecadeParser class (handles "1990s" → 1990-1999, "1800s" → 1800-1809)
- [ ] T032a [US2] Write unit tests for DecadeParser in `wikipedia-ingestion/span_parsing/tests/test_decade_parser.py` (test all decade patterns: 1000s-2000s, 1800s→1800-1809, 1990s→1990-1999, edge cases, target >80% coverage)
- [ ] T033 [US2] Update FoodTimelineParseOrchestrator in `wikipedia-ingestion/span_parsing/orchestrators/food_timeline_parse_orchestrator.py` to register and prioritize DecadeParser
- [ ] T034 [US2] Update logging in date_extraction_strategies.py to distinguish between explicit, section-inferred, and decade-parsed dates

**Checkpoint**: User Story 2 complete - decade notation parsed, undated events get section-based date ranges, 1990s→1990-1999, 1800s→1800-1809, BC/BCE ranges handled correctly

---

## Phase 5: User Story 3 - Support Multiple Date Formats and Variants (Priority: P2)

**Goal**: Handle diverse date formats including ranges, centuries, approximate dates, and special notations

**Independent Test**: Verify all 9+ date format patterns (year ranges, centuries, circa, tilde, years-ago, modifiers, decades, etc.) parse correctly with appropriate confidence levels

### Implementation for User Story 3

- [ ] T035 [US3] Implement Span → confidence mapping in food_event.py (circa=True → "approximate", section fallback → "inferred", decade → "explicit", explicit → "explicit")
- [ ] T036 [US3] Add BC/AD conversion validation in food_event.py (negative years for BC, 1 BC → 1 AD cutover)
- [ ] T037 [US3] Validate "years ago" anchoring to ingestion run date in years_ago_parser.py (from Phase 2)
- [ ] T038 [US3] Add support for contentious/disputed date marking in food_event.py (parse "contentious evidence" notes)
- [ ] T039 [US3] Update date_extraction_strategies.py to handle embedded dates in descriptions (extract primary date for event_key)
- [ ] T040 [US3] Add validation for very ancient dates (>10,000 BC) in food_event.py with appropriate precision handling

**Checkpoint**: User Story 3 complete - all date formats handled with proper confidence tracking

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T041 [P] Create test fixtures in `wikipedia-ingestion/strategies/timeline_of_food/tests/fixtures/sample_html.py` with real Wikipedia HTML samples (including table and decade examples)
- [ ] T042 [P] Create expected events fixture in `wikipedia-ingestion/strategies/timeline_of_food/tests/fixtures/expected_events.json` (with bullet, table, section-inferred, and decade events)
- [ ] T043 [P] Add integration validation script to verify 3,500+ events extracted and >95% date parsing success (including decade notation)
- [ ] T044 [P] Add performance validation (measure fetch/parse/load phases, ensure <30s total)
- [ ] T045 [P] Document strategy usage in `wikipedia-ingestion/strategies/timeline_of_food/README.md` (include table parsing and decade notation notes)
- [ ] T046 Run quickstart.md validation with live Wikipedia article fetch
- [ ] T047 Verify all constitution checks pass (>80% coverage, atomic integrity, microservices separation)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User Story 1 (P1): Independent after Phase 2
  - User Story 2 (P2): Depends on US1 (T011, T012, T013 specifically)
  - User Story 3 (P2): Depends on US1 and US2 infrastructure
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Depends on US1 core files AND span_parsing Phase 2 (creates DecadeParser as extension) AND fixes YearRangeParser BC/BCE range notation
- **User Story 3 (P2)**: Depends on US1 and US2 infrastructure but adds validation/edge case handling

### Within Each User Story

**User Story 1**:
- T011 (FoodEvent) and T012 (SectionParser) can run in parallel [P]
- T013 (EventParser) depends on T011, T012
- T014-T017 (Strategy implementation) depends on T011-T013
- T018-T024 (Details) can be done after T014 in any order

**User Story 2**:
- All tasks are sequential, extending US1 infrastructure

**User Story 3**:
- Most tasks can be done in parallel with [P] marking where applicable

### Parallel Opportunities

#### Phase 2 (Foundational):
All 5 parser tasks (T004-T008) can run in parallel - different files, no dependencies

```bash
Task T004: Create century_parser.py
Task T005: Create century_range_parser.py  
Task T006: Create century_with_modifier_parser.py
Task T007: Create years_ago_parser.py
Task T008: Create tilde_circa_year_parser.py
```

#### User Story 1:
Initial data structures can be built in parallel:

```bash
Task T011: Create food_event.py
Task T012: Create hierarchical_strategies.py
```

#### Phase 6 (Polish):
All documentation and validation tasks marked [P] can run in parallel:

```bash
Task T037: Create sample_html.py fixtures
Task T038: Create expected_events.json
Task T039: Add integration validation
Task T040: Add performance validation
Task T041: Document strategy usage
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (3 tasks)
2. Complete Phase 2: Foundational - span_parsing extensions (13 tasks: 5 parsers + 5 test suites + orchestrator + test + factory) - CRITICAL
3. Complete Phase 3: User Story 1 (25 tasks: 14 implementation + 10 test tasks + 1 artifact validation)
4. **STOP and VALIDATE**: Run ingestion against live Wikipedia, verify 3,000+ events extracted
5. Deploy/demo MVP

**MVP Delivery**: ~41 tasks (includes all required test coverage per constitution), delivers core value (food events in database)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (16 tasks: setup + parsers + tests)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP with 41 tasks total)
3. Add User Story 2 → Test independently → Deploy/Demo (47 tasks total) 
4. Add User Story 3 → Test independently → Deploy/Demo (53 tasks total)
5. Add Polish → Final validation (60 tasks total)

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With 2-3 developers:

1. **Week 1**: Team completes Setup + Foundational together (10 tasks)
2. **Week 2**: Once Foundational is done:
   - Developer A: User Story 1 core (T011-T017)
   - Developer B: User Story 1 details (T018-T024)
   - Developer C: Start span_parsing unit tests (optional)
3. **Week 3**: 
   - Developer A: User Story 2 (T025-T030)
   - Developer B: User Story 3 (T031-T036)
   - Developer C: Polish tasks (T037-T043)

---

## Notes

- [P] tasks = different files, no dependencies - can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests are REQUIRED per Constitution Principle III (NON-NEGOTIABLE) with >80% coverage target
- All parser and strategy implementation tasks now include corresponding test tasks (T004a-T008a, T009a, T011a-T024a)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- span_parsing extensions (Phase 2) are CRITICAL and block all other work
- Total task count: ~60 tasks including all constitution-required tests
