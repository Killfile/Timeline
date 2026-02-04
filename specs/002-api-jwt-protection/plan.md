# Implementation Plan: API JWT Token Protection

**Branch**: `002-api-jwt-protection` | **Date**: January 30, 2026 | **Spec**: [specs/002-api-jwt-protection/spec.md](specs/002-api-jwt-protection/spec.md)
**Input**: Feature specification from `/specs/002-api-jwt-protection/spec.md`

## Summary

Protect all API endpoints (including health/status) using JWTs issued by a dedicated token endpoint. The frontend obtains tokens by providing a shared client secret via header, caches the token in memory, and sends it as a Bearer token. The API enforces token validation, origin checks, rate limits the token endpoint, and blocks token replay using `jti` tracking with a short TTL.

**Breaking change note**: Protecting `/health` will break unauthenticated probes. Update deployment/monitoring to include a token or update health checks to call `/token` first.

**Versioning note**: This is a breaking change; plan a MAJOR version bump or explicitly document the breaking change in release notes per semantic versioning policy.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, Pydantic, psycopg2, httpx, uvicorn (API); D3.js frontend  
**Storage**: PostgreSQL (no schema changes), in-memory caches for rate limiting and `jti` replay tracking  
**Testing**: pytest  
**Target Platform**: Linux containers (Docker Compose)  
**Project Type**: Web application (backend + frontend)  
**Performance Goals**: <200ms p95 API response time  
**Constraints**: No hardcoded secrets; env vars only; all services containerized  
**Scale/Scope**: Single API service with public read traffic; no explicit concurrency targets

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Microservices Separation**: PASS — Changes scoped to API + frontend; no cross-service filesystem coupling.
- **Explicit Interfaces**: PASS — Token endpoint and auth contract documented in OpenAPI.
- **Test-First Development**: PASS — Plan includes unit tests for token issuance/validation, rate limiting, replay checks.
- **Atomic Data Integrity**: PASS — No ingestion or DB changes.
- **Observability & Versioning**: PASS — Auth logging included; no breaking external version changes required.

## Project Structure

### Documentation (this feature)

```text
specs/002-api-jwt-protection/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
api/
├── api.py
├── requirements.txt
└── Dockerfile

frontend/
├── candidate/
└── (existing frontend assets)

docker-compose.yml
```

**Structure Decision**: Use existing `api/` FastAPI service for token issuance/validation and `frontend/candidate/` for token fetch/cache logic. No database or ingestion changes.

## Phase 0: Research

- Research completed in [specs/002-api-jwt-protection/research.md](specs/002-api-jwt-protection/research.md).
- Decisions captured for JWT library, replay mitigation storage, rate limiting approach, origin enforcement, and token endpoint path.

## Phase 1: Design & Contracts

- Data model documented in [specs/002-api-jwt-protection/data-model.md](specs/002-api-jwt-protection/data-model.md).
- API contract documented in [specs/002-api-jwt-protection/contracts/api-token-auth.yaml](specs/002-api-jwt-protection/contracts/api-token-auth.yaml).
- Quickstart documented in [specs/002-api-jwt-protection/quickstart.md](specs/002-api-jwt-protection/quickstart.md).

### Constitution Re-check (Post-Design)

- **Microservices Separation**: PASS — no cross-service coupling introduced.
- **Explicit Interfaces**: PASS — token endpoint documented.
- **Test-First Development**: PASS — plan includes unit tests with mocks.
- **Observability & Versioning**: PASS — auth logging required; no breaking API version bump yet.

## Phase 2: Implementation Planning (High-Level)

1. **API: token issuance**
  - Add `/token` endpoint that validates `X-Client-Secret`, issues JWT with `exp`, `iat`, `jti`.
  - Add per-IP rate limiter for `/token`.
2. **API: request validation**
  - Add middleware/dependency to enforce Bearer auth for all endpoints including `/health`.
  - Validate signature, expiration, origin allowlist, and replay window.
3. **Replay mitigation**
  - Track `jti` in an in-memory TTL cache; reject replays within window.
4. **Frontend: token fetch & caching**
  - Fetch token on app load; cache in memory; refresh on reload.
5. **Configuration**
  - Add env vars: `API_JWT_SECRET`, `API_TOKEN_TTL_SECONDS`, `COOKIE_NAME`, `COOKIE_SECURE`, `COOKIE_SAMESITE`, `COOKIE_DOMAIN`, `CORS_ALLOWED_ORIGINS`, `API_RATE_LIMIT_PER_MINUTE`, `API_RATE_LIMIT_BURST`.
6. **Testing**
  - Unit tests for token issuance, invalid secret, rate limiting, token validation failure modes, replay rejection, and origin checks. Mock time and request headers.
7. **Docs**
  - Update API README/docs for auth requirements and token endpoint usage.

## Complexity Tracking

No constitution violations.
