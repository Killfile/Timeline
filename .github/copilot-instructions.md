# Copilot instructions for this repository

These instructions apply to all Copilot-generated code and edits in this repo.

## Specification driven development
- Every AI interaction should include an examination of the specification and the refinement of the specification to include any new requirements discovered during implementation.

## Tenor and Demeanor

- Aim for a professional and clear tone.
- Question ambiguous requirements rather than making assumptions.
- When suggesting changes, prefer conservative improvements that align with existing code style and architecture.
- Avoid introducing new technologies or frameworks without prior discussion.
- Hold the user accountable for best practices.
- Provide rationale for your suggestions.
- Assume the user is knowledgeable but may not be an expert; question instructions which seem to contradict best practices.
- Prioritize maintainability and readability over cleverness or brevity.

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
- Keep functions and classes small; prefer composition over inheritance.
- Avoid deep nesting; use early returns to simplify control flow.
- Variable name length should be proportional to scope; longer names for wider scopes.
    - Exception: In test code, prefer longer and more descriptive names for clarity.
- Function name lengths should be inversely proportional to their scope: shorter names for widely used functions, longer names for narrow-scope functions.

## Testing expectations (required)

- Any non-trivial logic change **must** come with unit tests.
- Tests should cover:
  - happy path
  - at least 1–2 edge cases
  - at least 1 failure mode (exception/invalid input)
- Prefer fast, isolated unit tests over integration tests where possible.
- Mock external dependencies (HTTP, DB) in unit tests; no exceptions.
    - Use clean, readable, scoped mocks (e.g., `unittest.mock` in Python, `jest.mock` in JS).
- Tests should be isolated from each other both logically and architecturally. 
    - Avoid DRYing up tests; duplication in tests is often acceptable for clarity.
    - Avoid shared fixtures that create hidden dependencies between tests.
- Tests MUST be highly readable and maintainable:
  - Clear naming
  - Simple setup/teardown
  - Well-structured assertions
  - Avoid complex logic in tests
- Target 80%+ code coverage for any new/changed logic.
- Preference running all tests as part of any changes.
- Prefer parameterized tests over multiple asserts in a single test.
- Changes to any code under test coverage MUST include updates to tests to maintain or improve coverage.
- Run all tests locally as part of any changes.

### Python

- Prefer **pytest**-style unit tests when adding/changing Python logic.
- Structure code to be testable:
  - avoid global state where possible
  - parameterize external dependencies (HTTP sessions, DB connections)
  - keep pure logic in functions that don’t require Docker to test
- Avoid long functions and classes; break into smaller, testable units.
- Avoid defining functions within other functions or methods.
- Pass variables explicitly rather than relying on closures or outer scope.
- Use type hints for function parameters and return values.
- Use dictionaries or data classes for structured data rather than tuples or lists.
- When running python tests or any local python code, ALWAYS run them in a virtual environment to avoid dependency conflicts.
- You *never* need to spin up a python http.server locally. If you need a server, use docker.

### Frontend (JS)

- When adding significant frontend logic, add tests using whatever test framework exists in the repo.
  - If no test framework is present, keep changes small and propose adding one separately.
- Currently the canonical frontend application is in `frontend/candidate/`. When making changes to the frontend, ensure that the changes are made in the correct directory.

## API & DB changes
- When adding API routes or DB schema changes:
  - update docs/README if user-facing behavior changes
  - validate backwards compatibility where reasonable
  - keep migrations/versioning in mind (don’t silently break existing data)

## Output & logging

- Log to stdout/stderr in containers.
- Make logs actionable (include context like IDs, category names, and response status codes).
- Avoid logging secrets.

## Running and Debugging

- The frontend runs on http://localhost:3000 by default.
- The API runs on http://localhost:8000 by default.
- For testing wars ingestion logic, use: `python ingest_wikipedia.py wars`
- If you need to create temporary tools or debug scripts, place them in a `temp_tools/` directory at the repo root and do not commit them to version control.

## Git

- Leave git operations to the user.
- Do not issue git commands in agentic mode or suggest git commands unless explicitly asked.

## Database and migrations
- Don't bother attempting to modify data in place; we will destroy and recreate as needed.

## How dates work

- BC dates go backwards so 200 BC comes before 100 BC.
- AD dates go forwards so 100 AD comes before 200 AD.
- The cutover from BC to AD goes from 1 BC to 1 AD (there is no year 0).
- Date ingestion should be in chronological order and respect BC/AD rules.
- Century based dating like "15th century" should be converted to year ranges (e.g., 1401-1500).
- 1st century AD means years 1-100
- 1st century BC means years 100-1 BC
- There is no year 0 and there is no 0th century.

