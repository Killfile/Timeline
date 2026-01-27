# Feature Specification: Timeline of Food Ingestion Strategy

**Feature Branch**: `001-timeline-of-food`  
**Created**: 2026-01-25  
**Status**: Draft  
**Input**: Build a new Wikipedia ingestion strategy for https://en.wikipedia.org/wiki/Timeline_of_food called "Timeline of Food"

## Clarifications

### Session 2026-01-25

- Q: What anchor should "years ago" dates use? → A: Anchor to ingestion run date (current UTC) for conversion.
- Q: How should event titles be generated from descriptions? → A: Use first 50-70 characters of event description as title; full text remains in description field.
- Q: How should events without explicit dates (and no section context) be handled? → A: Do not insert into database; log as warning in info logs and record failure in error logs.
- Q: What category should be assigned to Timeline of Food events? → A: "Food History" (single category for entire article).
- Q: How should the source be recorded for traceability? → A: Use standard HistoricalEvent.source field with value "Timeline of Food".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest Timeline of Food Events (Priority: P1)

The system should discover and extract historical food events from the Wikipedia article "Timeline of Food" and load them into the database so they appear on the main timeline visualization alongside other historical events.

**Why this priority**: This is the core feature that delivers immediate value - populating the timeline with food history data that users can explore and filter.

**Independent Test**: The feature can be fully tested by running the ingestion strategy and verifying that:
1. Events are extracted from the Wikipedia page
2. Events are loaded into the database
3. Events appear on the frontend timeline with proper dates and descriptions
4. Each event has proper date formatting (BC/AD handling)

**Acceptance Scenarios**:

1. **Given** the Timeline of Food Wikipedia article, **When** the ingestion strategy is run, **Then** all discoverable events are extracted into the database
2. **Given** extracted events, **When** the frontend queries the timeline, **Then** food events are displayed with other events in chronological order
3. **Given** events with various date formats (e.g., "8000 BC", "1500 AD"), **When** they are ingested, **Then** dates are correctly parsed and stored

---

### User Story 2 - Support Date Range Inference for Undated Events (Priority: P2)

Some events in the Timeline of Food article may not have explicit dates. The system should infer reasonable date ranges for such events based on hierarchical context (e.g., a subsection header like "Medieval Period").

**Why this priority**: Enhances data completeness by providing context-based date ranges for events that would otherwise be unusable.

**Independent Test**: Can be tested by:
1. Verifying that events without explicit dates receive inferred date ranges
2. Confirming that hierarchical context (sections/subsections) is properly captured
3. Validating that inferred ranges are reasonable given the Wikipedia structure

**Acceptance Scenarios**:

1. **Given** an event without explicit date under "17th century" section, **When** the event is extracted, **Then** it receives an inferred date range matching the span of the 17th century (1601-1700)
2. **Given** nested subsections with different time periods, **When** extracting events, **Then** events inherit the most specific applicable time range

---

### User Story 3 - Support Multiple Date Formats and Variants (Priority: P2)

The Timeline of Food article likely contains diverse date formats (ranges, centuries, approximate dates, "circa" dates, etc.). The system should handle these variations gracefully.

**Why this priority**: Food history articles often use varied date conventions; proper handling ensures high data quality.

**Independent Test**: Can be tested by:
1. Creating test cases for each identified date format variant
2. Verifying correct parsing of century notation (e.g., "5th century BC", "21st century")
3. Confirming handling of approximate/uncertain dates

**Acceptance Scenarios**:

1. **Given** event text "circa 1000 AD", **When** parsed, **Then** date is extracted as approximately 1000 AD
2. **Given** event text "3000-2500 BC", **When** parsed, **Then** both start and end years are captured
3. **Given** event text "5th century BC", **When** parsed, **Then** century is converted to year range (500-401 BC)

---

### Edge Cases

- What happens when the Timeline of Food article has a different structure than expected?
- How does the system handle events with ambiguous or uncertain dates? (Undated events are logged but not inserted)
- What happens if the Wikipedia page cannot be fetched (network error, page moved)?
- How are very ancient dates (10,000+ BC) handled?
- What if event descriptions contain embedded dates that don't match the main date field?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST discover the Wikipedia article at https://en.wikipedia.org/wiki/Timeline_of_food
- **FR-002**: System MUST extract all event entries from the article's main content sections
- **FR-003**: System MUST parse dates from event text using multiple recognized formats (years, ranges, centuries, approximate dates)
- **FR-004**: System MUST infer date ranges for undated events based on hierarchical context (sections/subsections)
- **FR-005**: System MUST handle BC/AD date conversions correctly (BC dates count backward, cutover at 1 BC → 1 AD)
- **FR-006**: System MUST generate event titles from the first 50-70 characters of the description text
- **FR-007**: System MUST generate a JSON artifact file containing all extracted events
- **FR-008**: System MUST prepare events for leading into the PostgreSQL database using the standard HistoricalEvent schema. The database_loader.py will handle the actual loading. 
- **FR-009**: System MUST assign category "Food History" to all events from this source
- **FR-010**: System MUST set source field to "Timeline of Food" for all events
- **FR-011**: System MUST exclude events with no parseable date and no section context from database insertion
- **FR-012**: System MUST log undated events as warnings in info logs AND record failures in error logs for visibility
- **FR-013**: System MUST produce a strategy-specific log documenting parsing decisions and any ambiguities
- **FR-014**: System MUST follow the same ETL (Extract-Translate-Load) architecture as existing strategies
- **FR-015**: System MUST maintain atomic data integrity by using deterministic event keys for deduplication

### Key Entities *(include if feature involves data)*

- **Event**: Represents a single historical food-related event
  - date/date_range: When the event occurred
  - title: First 50-70 characters of description (for display)
  - description: Full event text (extracted from Wikipedia)
  - source: "Timeline of Food" article
  - category: "Food History" (constant for all events)
  - confidence: Whether date is explicit or inferred
  
- **Section/Subsection**: Hierarchical structure in the Wikipedia article
  - title: Section heading
  - date_range (inferred): Likely time period for events in this section
  - depth: Nesting level (used for hierarchy traversal)

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: BeautifulSoup4 (HTML parsing), requests (HTTP fetch), pytest (testing)  
**Storage**: PostgreSQL (same schema as other ingestion strategies via HistoricalEvent)  
**Testing**: pytest with mocked HTTP responses and fixture data  
**Target Platform**: Docker container (same as api and wikipedia-ingestion services)  
**Project Type**: Single module - Python ingestion strategy  
**Performance Goals**: Ingestion completes in <30 seconds; database load in <5 seconds  
**Constraints**: Must not make unbounded HTTP requests; must handle 404/redirects gracefully  
**Scale/Scope**: Single Wikipedia article (~10,000 lines of HTML estimated; 3,000-5,000 events estimated)
**Date Anchoring Rule**: "Years ago" conversions anchor to ingestion run date (current UTC) to compute absolute years.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Architecture & Design

- ✅ **Microservices Separation**: Strategy isolated in `wikipedia-ingestion/strategies/timeline_of_food/`
- ✅ **Explicit Interfaces**: Implements standard `IngestionStrategy` base class
- ⚠️ **Test-First Development**: REQUIRED - must add unit tests covering parse logic, date handling, edge cases
- ✅ **Atomic Data Integrity**: Uses same event key pattern as other strategies
- ✅ **Observability & Versioning**: Will use same logging pattern as other strategies
- ✅ **Ingestion Architecture**: Follows Extract-Translate-Load with discovery, hierarchical, and event strategies

### Complexity Analysis

No violations. Timeline of Food follows the existing strategy pattern with no special requirements that would justify complexity trade-offs.

## Next Steps (Phase 0 Research)

Before design (Phase 1), need to clarify:

1. **Article Structure**: What are the main sections of the Timeline of Food article? (hierarchies, subsections)
2. **Date Format Patterns**: What specific date formats appear in the article?
3. **Hierarchical Organization**: Is the article organized by time period, food type, geography, or other?
4. **Event Density**: Estimated number of events and typical event description format
5. **Edge Cases**: Common parsing ambiguities or special formatting in this article

