# Timeline Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-25

## Active Technologies
- Python 3.11 + FastAPI, Pydantic, psycopg2, httpx, uvicorn (API); D3.js frontend (002-api-jwt-protection)
- PostgreSQL (no schema changes), in-memory caches for rate limiting and `jti` replay tracking (002-api-jwt-protection)
- Python 3.11+ + FastAPI (web framework), PostgreSQL (database), argon2-cffi or pwdlib (password hashing), jsonschema (JSON validation), psycopg2 (database driver) (001-admin-timeline-management)
- PostgreSQL (existing database with new tables: users, roles, user_roles, timeline_categories, ingestion_uploads) (001-admin-timeline-management)

- Python 3.11 + FastAPI (API), D3.js (frontend), PostgreSQL, Docker; Wikipedia ingestion service (Python) (001-history-of-food)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11: Follow standard conventions

## Recent Changes
- 001-admin-timeline-management: Added Python 3.11+ + FastAPI (web framework), PostgreSQL (database), argon2-cffi or pwdlib (password hashing), jsonschema (JSON validation), psycopg2 (database driver)
- 002-api-jwt-protection: Added Python 3.11 + FastAPI, Pydantic, psycopg2, httpx, uvicorn (API); D3.js frontend

- 001-history-of-food: Added Python 3.11 + FastAPI (API), D3.js (frontend), PostgreSQL, Docker; Wikipedia ingestion service (Python)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
