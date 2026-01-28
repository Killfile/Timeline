# Implementation Plan: Timeline of Food Ingestion Strategy

**Branch**: `001-timeline-of-food` | **Date**: 2026-01-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-timeline-of-food/spec.md`

## Summary

Build a new Wikipedia ingestion strategy to extract food-related historical events from the "Timeline of Food" article and populate the database with events spanning from prehistoric times to the 21st century. The strategy will implement discovery, hierarchical, and event parsing strategies to handle the article's varied date formats and hierarchical organization by historical periods.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: BeautifulSoup4 (HTML parsing), requests (HTTP), pytest (testing)  
**Storage**: PostgreSQL (HistoricalEvent schema)  
**Testing**: pytest with mocked HTTP responses  
**Target Platform**: Docker container (component of the wikipedia-ingestion service)  
**Project Type**: Single module - Python ingestion strategy  
**Performance Goals**: Ingestion completes in <30 seconds; database load in <5 seconds  
**Constraints**: Handle graceful failures (404s, network errors); no unbounded requests  
**Scale/Scope**: ~5,000 events from single Wikipedia article

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Architecture & Design

- ✅ **Microservices Separation**: Strategy isolated in `wikipedia-ingestion/strategies/timeline_of_food/`
- ✅ **Explicit Interfaces**: Implements standard `IngestionStrategy` base class
- ✅ **Test-First Development**: REQUIRED - add unit tests for parse logic, date handling, edge cases
- ✅ **Atomic Data Integrity**: Uses same event key pattern as other strategies
- ✅ **Observability & Versioning**: Uses same logging pattern as other strategies
- ✅ **Ingestion Architecture**: Follows Extract-Translate-Load phases

**No violations identified.** Timeline of Food follows existing strategy pattern with no special requirements.

## Project Structure

### Documentation (this feature)

```text
specs/001-timeline-of-food/
├── plan.md              # This file
├── research.md          # Phase 0 findings (TBD)
├── data-model.md        # Phase 1 design (TBD)
├── quickstart.md        # Phase 1 quick start (TBD)
└── contracts/           # Phase 1 API contracts (TBD)
```

### Source Code

```text
wikipedia-ingestion/strategies/timeline_of_food/
├── __init__.py
├── timeline_of_food_strategy.py      # Main strategy implementation
├── food_event.py                     # Event data structure
├── date_extraction_strategies.py     # Multiple date format parsers
├── hierarchical_strategies.py        # Section/subsection parsing
├── tests/
│   ├── __init__.py
│   ├── test_timeline_of_food_strategy.py
│   ├── test_date_extraction.py
│   ├── test_hierarchical_parsing.py
│   └── fixtures/
│       ├── sample_html.py           # Sample Wikipedia page HTML
│       └── expected_events.json      # Test fixture events
└── logs/
    └── timeline_of_food_<RUN_ID>.json  # Strategy-specific logs
```

## Phase 0: Research Findings

### Article Structure

**Main sections identified** (from Wikipedia "Timeline of Food"):
- Prehistoric times
- Neolithic  
- 4000-2000 BCE
- 2000-1 BCE
- 1-1000 CE
- 1000-1500
- 16th century
- 17th century
- 18th century
- 19th century (mixed format: includes table-based entries)
- 20th century
- 21st century

**Format observation**: Prehistoric through 18th century use bullet point format with mixed text and HTML formatting. 19th century and later use a mix of bullet points and table format.

### Date Format Analysis

**Patterns identified**:
1. **Single years**: "8000 BCE", "1516", "1609"
2. **BC/AD variants**: "5-2 million years ago", "250,000 years ago", "170,000 years ago"
3. **Ranges**: "8000-5000 BCE", "2500-1500 BCE", "11th–14th centuries"
4. **Centuries**: "5th century", "19th century", "21st century"
5. **Approximate**: "~9300 BCE", "~8000 BCE", "circa 1000 AD"
6. **Contentious**: "13,000 BCE" with note about skepticism
7. **Early AD dates**: "1-1000 CE", "1–1000 CE" format

### Hierarchical Context

Sections serve as implicit date range indicators:
- "Prehistoric times" → wide range (pre-3000 BCE)
- "Neolithic" → 9300 BCE to ~3000 BCE (varies by region)
- "4000-2000 BCE" → explicit range in heading
- "Medieval" sections in later centuries → specific historical period

### Event Density

**Estimated counts**:
- Prehistoric through Medieval: ~50-100 events
- 16th-17th centuries: ~20-30 events
- 18th century: ~50-70 events
- 19th century: ~150+ events (denser with company founding dates)
- 20th century: ~50+ events
- 21st century: ~3 events

**Total estimate**: 3,000-5,000 events depending on extraction strategy

### Edge Cases Identified

1. **Company/product founding dates** (especially 19th century): Should these be included? Answer: Yes, as they represent food culture milestones
2. **Contested dates**: Some entries explicitly state "contentious evidence" or disagreement. Should include with confidence marking
3. **Range ambiguity**: Entries like "11th–14th centuries" need conversion (1001-1400)
4. **Very ancient dates**: Proper handling of "million years ago" format required
5. **Cross-references**: Many events reference other Wikipedia articles (food items, people, locations)

## Key Decisions

1. **Extend span_parsing library**: Create 5 NEW parser strategies (`century_parser.py`, `century_range_parser.py`, `century_with_modifier_parser.py`, `years_ago_parser.py`, `tilde_circa_year_parser.py`) and 1 NEW orchestrator (`food_timeline_parse_orchestrator.py`)
2. **Custom orchestrator**: `FoodTimelineParseOrchestrator` combines standard parsers + new parsers in optimal priority order
3. **Start with text-based parsing**: First implement bullet-point parser (works for ~90% of article)
4. **Table parsing as phase 2**: 19th century table-based entries can be handled separately
5. **Date confidence levels**: Map `Span` properties to confidence (circa → approximate, etc.)
6. **Graceful degradation**: Events without proper date extraction go to logs, not database

## Phase 1: Design Complete

✅ **Data models**: Defined in [data-model.md](data-model.md)  
✅ **API contracts**: Defined in [contracts/data-contracts.md](contracts/data-contracts.md)  
✅ **Architecture**: Uses span_parsing library with 5 new parsers + custom orchestrator  
✅ **Quick start guide**: [quickstart.md](quickstart.md)  

## Phase 2: Implementation Plan

### A. Extend span_parsing Library (Week 1)

**Deliverables**:

1. **`span_parsing/century_parser.py`**
   - Parse "5th century BCE" → Span(start=-500, end=-401)
   - Handle 1st-21st centuries with BC/AD/CE/no-marker
   - Unit tests: 15+ test cases covering all centuries and eras

2. **`span_parsing/century_range_parser.py`**
   - Parse "11th-14th centuries" → Span(start=1001, end=1400)
   - Handle BC ranges (decreasing years)
   - Unit tests: 10+ test cases including BC ranges

3. **`span_parsing/century_with_modifier_parser.py`**
   - Parse "Early 1700s", "Late 16th century", "Before 17th century"
   - Handle "Late 16th century–17th century" hybrid ranges
   - Thirds mapping: Early (1-33%), Mid (34-66%), Late (67-100%)
   - Unit tests: 20+ test cases for all modifiers and formats

4. **`span_parsing/years_ago_parser.py`**
   - Parse "250,000 years ago" anchored to ingestion run date
   - Handle "5-2 million years ago" ranges with multiplier
   - Unit tests: 10+ test cases including edge cases (commas, millions)

5. **`span_parsing/tilde_circa_year_parser.py`**
   - Parse "~1450" → Span(start=1450, end=1450, circa=True)
   - Handle "~450 BCE"
   - Unit tests: 8+ test cases

6. **`span_parsing/orchestrators/food_timeline_parse_orchestrator.py`**
   - Combine all parsers in priority order (exact → circa → ranges → centuries → years-ago → decades → fallback)
   - Unit tests: 25+ test cases exercising all parser paths

7. **Update `parse_orchestrator_factory.py`**
   - Add `ParseOrchestratorTypes.FOOD_TIMELINE` enum
   - Register FoodTimelineParseOrchestrator

**Dependencies**: None (extends existing library)  
**Risks**: Parser precedence conflicts → Mitigated by comprehensive integration tests  
**Testing target**: >80% coverage for each parser

### B. Implement Timeline of Food Strategy (Week 2)

**Deliverables**:

1. **`strategies/timeline_of_food/timeline_of_food_strategy.py`**
   - Implement `fetch()`: HTTP GET with caching, error handling
   - Implement `parse()`: HTML → FoodEvent list using orchestrator
   - Implement `generate_artifacts()`: JSON output with metadata
   - Entry point for ingestion pipeline

2. **`strategies/timeline_of_food/food_event.py`**
   - FoodEvent dataclass with fields: event_key, date fields, title, description, category, confidence
   - `to_historical_event()` conversion method
   - `generate_event_key()` using MD5(date + title + source)

3. **`strategies/timeline_of_food/section_parser.py`**
   - Extract hierarchical sections (h2, h3, h4) from HTML
   - Build TextSection tree with inferred date ranges
   - Context inheritance for undated events

4. **`strategies/timeline_of_food/event_parser.py`**
   - Parse bullet points using BeautifulSoup
   - Extract date text → call FoodTimelineParseOrchestrator
   - Generate title (first 50-70 chars) and full description
   - Map Span → confidence levels (explicit/approximate/fallback)

5. **`strategies/timeline_of_food/tests/`** (comprehensive test suite)
   - `test_timeline_of_food_strategy.py`: End-to-end strategy tests
   - `test_section_parser.py`: Hierarchical parsing tests
   - `test_event_parser.py`: Event extraction and date parsing tests
   - `fixtures/sample_html.py`: Real Wikipedia HTML samples
   - `fixtures/expected_events.json`: Expected parsed events

6. **Update `ingestion_strategy_factory.py`**
   - Add `IngestionStrategies.TIMELINE_OF_FOOD` enum
   - Import and register TimelineOfFoodStrategy

**Dependencies**: Phase 2A complete (span_parsing extensions)  
**Risks**: HTML structure changes → Mitigated by defensive parsing and logging  
**Testing target**: >80% coverage; 50+ test cases

### C. Integration & Validation (Week 2-3)

**Tasks**:

1. **Integration testing**
   - Run strategy against live Wikipedia article
   - Verify 3,000+ events extracted with >95% date parsing success
   - Performance validation: <30 seconds total execution

2. **Database validation**
   - Verify event_key deduplication works correctly
   - Check BC/AD date storage (negative years for BC)
   - Validate category "Food History" applied to all events

3. **Error handling validation**
   - Test 404 handling (page not found)
   - Test network timeout handling
   - Verify undated events logged but not inserted

4. **Artifact validation**
   - JSON schema compliance check
   - Verify artifact contains all required metadata
   - Test artifact can be loaded and replayed

**Success criteria**:
- ✅ 3,000+ events extracted and loaded
- ✅ >95% date parsing accuracy
- ✅ <30 second execution time
- ✅ >80% code coverage
- ✅ All constitution checks pass
- ✅ Zero critical bugs in error handling

## Implementation Sequence

### Week 1: span_parsing Extensions
1. Day 1-2: Century parsers (basic, range, modifier)
2. Day 3: Years-ago and tilde parsers
3. Day 4: Custom orchestrator
4. Day 5: Integration tests and factory registration

### Week 2: Strategy Implementation
1. Day 1: FoodEvent and section parser
2. Day 2-3: Event parser with orchestrator integration
3. Day 4: Main strategy (fetch/parse/artifact)
4. Day 5: Strategy test suite

### Week 3: Integration & Polish
1. Day 1-2: Live Wikipedia testing and debugging
2. Day 3: Database integration validation
3. Day 4: Error handling and edge case testing
4. Day 5: Documentation and handoff

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Wikipedia structure changes | Low | High | Defensive parsing; comprehensive error logging |
| Date parsing edge cases | Medium | Medium | Extensive test fixtures; fallback to section context |
| Performance degradation | Low | Medium | Profile parse phase; optimize BeautifulSoup selectors |
| Parser precedence bugs | Medium | High | Comprehensive orchestrator tests; clear precedence docs |
| BC/AD conversion errors | Low | High | Dedicated test cases; validation against known events |

## Monitoring & Observability

- **Logs**: JSON-structured logs in `logs/timeline_of_food_<RUN_ID>.json`
- **Metrics tracked**: 
  - Events extracted (total)
  - Date parsing success rate (by format)
  - Execution time (fetch/parse/load phases)
  - Undated events count
- **Alerts**: Log ERROR when >5% events fail date parsing

## Post-Implementation (Phase 3)

**Future enhancements**:
1. Table-based event parsing (19th-20th century sections)
2. LLM-based subcategory classification
3. Cross-reference extraction (linked Wikipedia articles)
4. Multi-language support (other Wikipedia language versions)

## Constitution Re-Check (Post-Phase 1)

### Architecture & Design
- ✅ **Microservices Separation**: Strategy isolated; no cross-service coupling
- ✅ **Explicit Interfaces**: Follows IngestionStrategy contract
- ✅ **Test-First Development**: Comprehensive test plan with >80% coverage target
- ✅ **Atomic Data Integrity**: event_key deduplication ensures atomicity
- ✅ **Observability & Versioning**: JSON logs with run IDs
- ✅ **Ingestion Architecture**: ETL pattern (Extract → Translate → Load)

**Result**: ✅ All gates pass. Ready for implementation.
