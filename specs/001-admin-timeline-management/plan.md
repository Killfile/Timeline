# Implementation Plan: Admin Timeline Management

**Branch**: `001-admin-timeline-management` | **Date**: 2026-02-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-admin-timeline-management/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature implements an admin interface for timeline management with role-based access control. The system allows administrators to manage users, assign roles, and perform CRUD operations on timeline categories including JSON upload/ingestion. The implementation leverages existing cookie-based JWT authentication, extends it with role-based permissions, and adds password hashing (Argon2id), user management endpoints, and category management with JSON schema validation.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI (web framework), PostgreSQL (database), argon2-cffi or pwdlib (password hashing), jsonschema (JSON validation), psycopg2 (database driver)  
**Storage**: PostgreSQL (existing database with new tables: users, roles, user_roles, timeline_categories, ingestion_uploads)  
**Testing**: pytest (existing framework with cookie auth fixtures in conftest.py)  
**Target Platform**: Linux containers (Docker Compose environment)  
**Project Type**: Web application (backend API + frontend admin UI)  
**Performance Goals**: <200ms p95 API response time, 0.2-0.5s password hashing latency  
**Constraints**: <200ms p95 for admin endpoints, 10MB max JSON upload size, no email integration for password resets  
**Scale/Scope**: 10-100 users initially, ~5-20 timeline categories, admin UI supports user and category CRUD operations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Microservices Separation** | ✅ PASS | Admin functionality lives within existing API service. Frontend admin page is separate UI component. No new services introduced, no cross-service coupling created. |
| **II. Explicit Interfaces** | ✅ PASS | All admin endpoints are REST APIs with documented request/response models. Database schema changes documented in migration SQL. JSON upload contract defined by import_schema.json. |
| **III. Test-First Development** | ✅ PASS | All new logic (password hashing, RBAC dependencies, JSON validation, user CRUD, category CRUD) will have unit tests covering happy path, edge cases, and failure modes. Mocking for DB and HTTP dependencies. Target 80%+ coverage. |
| **IV. Atomic Data Integrity** | ✅ PASS | Category deletion uses CASCADE foreign key constraints to automatically remove associated events and enrichments. No orphaned data. Ingestion uploads create deterministic event_key for enrichment association. |
| **V. Observability & Versioning** | ✅ PASS | Structured logging for all admin operations (user creation, role assignment, category CRUD, upload validation). Logs include context: user_id, category_name, upload_id, HTTP status. Database schema changes follow migration versioning (005_add_admin_tables.sql). |
| **VI. Ingestion Architecture** | ✅ PASS | JSON upload follows existing Extract-Translate-Load pattern: Upload file (Extract) → Validate schema (Translate validation) → Insert events (Load). Uses existing database_loader.py for consistency. |

**Verdict**: All constitutional gates PASS. No complexity justifications required.

## Project Structure

### Documentation (this feature)

```text
specs/001-admin-timeline-management/
├── spec.md              # Feature specification (user stories, requirements, success criteria)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (password hashing, RBAC, JSON validation, upload security)
├── data-model.md        # Phase 1 output (database schema: users, roles, user_roles, timeline_categories, ingestion_uploads)
├── quickstart.md        # Phase 1 output (setup instructions, seed admin user, run migrations)
├── contracts/           # Phase 1 output (OpenAPI specs for /admin/* endpoints)
│   ├── auth.openapi.yaml
│   ├── users.openapi.yaml
│   └── categories.openapi.yaml
└── checklists/
    └── requirements.md  # Specification quality checklist (complete)
```

### Source Code (repository root)

```text
api/
├── api.py                          # Main FastAPI application (add admin endpoints here)
├── auth/
│   ├── auth_dependency.py          # Existing cookie JWT auth (extend with RBAC)
│   ├── jwt_service.py              # JWT encode/decode (extend with role claims)
│   ├── password_service.py         # NEW: Argon2id password hashing
│   └── rbac.py                     # NEW: Role-based access control dependencies
├── models/
│   ├── user.py                     # NEW: User, Role, UserRole models
│   └── category.py                 # NEW: TimelineCategory, IngestionUpload models
├── services/
│   ├── user_service.py             # NEW: User CRUD operations
│   └── category_service.py         # NEW: Category CRUD and upload processing
└── tests/
    ├── conftest.py                 # Existing pytest fixtures (extend with admin user)
    ├── unit/
    │   ├── test_password_service.py   # NEW: Password hashing unit tests
    │   ├── test_rbac.py               # NEW: RBAC dependency unit tests
    │   ├── test_user_service.py       # NEW: User service unit tests
    │   └── test_category_service.py   # NEW: Category service unit tests
    └── integration/
        ├── test_admin_auth.py         # NEW: Admin authentication integration tests
        ├── test_user_endpoints.py     # NEW: /admin/users/* endpoint tests
        ├── test_category_endpoints.py # NEW: /admin/categories/* endpoint tests
        └── test_upload_endpoints.py   # NEW: /admin/uploads/* endpoint tests

frontend/
├── candidate/                      # Current production frontend
│   ├── admin.html                  # NEW: Admin page UI
│   ├── admin.js                    # NEW: Admin page logic (user/category management)
│   └── admin.css                   # NEW: Admin page styles
└── ...

database/
└── migrations/
    └── 005_add_admin_tables.sql    # NEW: Create users, roles, user_roles, timeline_categories, ingestion_uploads tables

wikipedia-ingestion/
└── database_loader.py              # Existing loader (reuse for JSON upload ingestion)
```

**Structure Decision**: This is a web application feature. Backend admin functionality is added to the existing `api/` service with new auth modules, models, and services. Frontend admin UI is a new page in `frontend/candidate/`. Database schema changes follow migration pattern. No new services introduced, maintaining microservices separation.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
