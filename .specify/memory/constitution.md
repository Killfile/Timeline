<!--
Sync Impact Report
==================
Version change: 1.0.0 → 1.1.0 (MINOR)

Modified principles:
- Library-First → Microservices Separation
- CLI Interface → Explicit Interfaces
- Test-First → Test-First Development
- Integration Testing → Atomic Data Integrity
- Observability, Versioning, Simplicity → Observability & Versioning

Added sections: None
Removed sections: None

Templates requiring updates:
- .specify/templates/plan-template.md ✅ (validated)
- .specify/templates/spec-template.md ✅ (validated)
- .specify/templates/tasks-template.md ✅ (validated)

Follow-up TODOs:
- TODO(RATIFICATION_DATE): Confirm original ratification date if available
-->

# Timeline Constitution

## Core Principles

### I. Microservices Separation

Each service (API, database, wikipedia-ingestion, frontend) MUST be independently deployable, testable, and maintain clear boundaries. No direct cross-service filesystem sharing is permitted unless explicitly required.

**Rationale:** Prevents coupling and ensures maintainability. Each service can evolve, scale, and be debugged independently.

### II. Explicit Interfaces

All inter-service communication MUST use documented APIs (REST endpoints, database schema contracts). No hidden contracts or undocumented dependencies are permitted.

**Rationale:** Enables reliable integration and future extensibility. Changes to interfaces must be versioned and communicated.

### III. Test-First Development (NON-NEGOTIABLE)

All non-trivial logic MUST have unit tests covering:
- Happy path scenarios
- At least 1-2 edge cases
- At least 1 failure mode (exception/invalid input)

External dependencies (HTTP, DB) MUST be mocked in unit tests. Target: 80%+ code coverage for new/changed logic.

**Rationale:** Ensures correctness and prevents regressions. Tests document expected behavior and enable safe refactoring.

### IV. Atomic Data Integrity

Data refreshes (atomic reimport) MUST preserve enrichments using deterministic event keys. Orphaned enrichments MUST be pruned automatically via foreign key constraints.

**Rationale:** Guarantees data consistency and user trust. First-order data (Wikipedia facts) and second-order data (user enrichments, AI categories) must remain synchronized across reimports.

### V. Observability & Versioning

- Structured logging is REQUIRED for all services (log to stdout/stderr in containers)
- Logs MUST include context (IDs, category names, response status codes)
- All breaking changes MUST follow semantic versioning (MAJOR.MINOR.PATCH)
- Runtime guidance MUST be documented in README and docs/

**Rationale:** Enables debugging, traceability, and safe upgrades. Actionable logs help diagnose issues quickly.

### VI. Ingestion Architecture

- Ingestion is separated into three phases: Extract, Translate, Load
- Each phase MUST produce an artifact and use the artifacts as boundaries between the steps:
    - Extract: Produces a cache file for every remote resource read.  This speeds up development/debugging of the pipeline and ensures repeatabliity during the development process.
    - Translate: Produces a standardized, JSON representation of the extracted data.  All pipelines must produce the same datastructure so that the subsequent load step can be source agnostic.
    - Load: Produces the final database records.
- Each new ingestion pipeline (List of Events, Timeperiods, LGBTQ history, etc) must be a separate strategy under wikipedia-ingestion.
- The Translate phase of each ingestion pipeline should use strategy patterns and factories to identify the format of the content being parsed and select the appropriate strategy.
- Each translate strategy can be broken down into three phases: discovery strategies, hierarchical strategies, and event strategies.
    - Discovery strategies allow us to discover and follow links to other pages and ingest their contents.  Not all pipelines require discover strategies.
    - Hierarchical strategies allow us to infer the likely date ranges for undated elements on the page. We use them to traverse the page and discover events and associate those events with a fallback date range.
    - Event strategies look at a single event and attempt to extract that event into structured data.  If extraction is not possible, we can fall back onto the date range inferred by the hierarchical strategy. 

## Additional Constraints

**Technology Stack:**
- Python 3.11+
- FastAPI (API service)
- D3.js (frontend visualization)
- PostgreSQL (database)
- Docker & Docker Compose (containerization)

**Security & Deployment:**
- All services MUST run in containers
- No hardcoded secrets (use environment variables)
- Configuration follows 12-factor app principles

**Performance:**
- Database population must complete in <5 seconds.
- Wikipedia page parsing/extraction of events has no performance goal.
- API response time target: <200ms p95 for timeline queries

## Development Workflow

**Code Review:**
- All PRs require code review before merge
- All tests MUST pass before merge
- Deployment permitted only after review and test pass

**Quality Gates:**
- 80%+ code coverage for new/changed logic
- No critical lint errors
- Type hints for Python function parameters and return values

**Testing Discipline:**
- Run all tests locally as part of any changes
- Changes to code under test coverage MUST include test updates
- Prefer parameterized tests over multiple asserts in single test

## Governance

This constitution supersedes all other practices and guidelines. Amendments require:
1. Documentation of proposed changes
2. Approval from project maintainer
3. Migration plan for affected code

All PRs and code reviews MUST verify compliance with constitutional principles. Complexity and deviations MUST be justified explicitly.

For runtime development guidance, refer to:
- [README.md](../../README.md)
- [docs/README.md](../../docs/README.md)
- [.github/copilot-instructions.md](../../.github/copilot-instructions.md)

**Version**: 1.1.0 | **Ratified**: TODO(RATIFICATION_DATE): Confirm original ratification date if available | **Last Amended**: 2026-01-25
