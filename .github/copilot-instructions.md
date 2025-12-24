# Copilot instructions for this repository

These instructions apply to all Copilot-generated code and edits in this repo.

## Architecture & design

- Prefer a **microservices-first** mentality:
  - Keep `api/`, `wikipedia-ingestion/`, `frontend/`, and `database/` responsibilities clearly separated.
  - Don’t add cross-service coupling (e.g., direct filesystem sharing) unless explicitly required.
  - When adding new functionality, decide **which service owns it** and keep the change scoped.

- Enforce **Separation of Concerns**:
  - Keep IO (HTTP/DB/files) at the edges.
  - Keep business logic in pure functions/modules wherever possible.
  - Avoid “god modules” and large functions; refactor into smaller units.

- Follow **SOLID** principles:
  - **S**ingle Responsibility: one module/function/class should have one reason to change.
  - **O**pen/Closed: prefer extension points (interfaces/functions) instead of edits in many places.
  - **L**iskov Substitution: keep contracts consistent when subclassing / plugging components.
  - **I**nterface Segregation: prefer small, focused interfaces.
  - **D**ependency Inversion: depend on abstractions (protocols/interfaces) not concretions; inject dependencies (e.g., a `requests.Session`, DB connection) rather than creating them deep in the call graph.

## Modular coding standards

- Prefer small modules with explicit APIs.
- Avoid circular dependencies.
- Use clear naming and consistent structure:
  - For Python: prefer `snake_case`, type hints when practical, and docstrings for public functions.
  - For JS: keep functions small and pure where possible.
- Keep configuration in env vars / compose (12-factor style), not hard-coded values.

## Readability & maintainability

- Optimize for the next reader:
  - Write clear comments explaining *why*, not *what*.
  - Avoid cleverness.
  - Prefer explicit error handling with actionable messages.
- Don’t mix formatting-only changes into functional changes.

## Testing expectations (required)

- Any non-trivial logic change **must** come with unit tests.
- Tests should cover:
  - happy path
  - at least 1–2 edge cases
  - at least 1 failure mode (exception/invalid input)

### Python

- Prefer **pytest**-style unit tests when adding/changing Python logic.
- Structure code to be testable:
  - avoid global state where possible
  - parameterize external dependencies (HTTP sessions, DB connections)
  - keep pure logic in functions that don’t require Docker to test

### Frontend (JS)

- When adding significant frontend logic, add tests using whatever test framework exists in the repo.
  - If no test framework is present, keep changes small and propose adding one separately.

## API & DB changes

- When adding API routes or DB schema changes:
  - update docs/README if user-facing behavior changes
  - validate backwards compatibility where reasonable
  - keep migrations/versioning in mind (don’t silently break existing data)

## Output & logging

- Log to stdout/stderr in containers.
- Make logs actionable (include context like IDs, category names, and response status codes).
- Avoid logging secrets.
