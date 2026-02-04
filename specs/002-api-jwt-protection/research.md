# Phase 0 Research: API JWT Token Protection

## Decision 1: JWT library
- **Decision**: Use PyJWT for token encoding/decoding in the API service.
- **Rationale**: Minimal dependency footprint, straightforward HMAC signing, fits current FastAPI stack.
- **Alternatives considered**: python-jose (broader JOSE support, more features).

## Decision 2: Replay mitigation storage
- **Decision**: Use in-memory TTL cache for `jti` replay detection.
- **Rationale**: No new infrastructure needed; aligns with current scope and anti-scraping goals.
- **Alternatives considered**: Redis-backed cache (more durable across replicas), database table.

## Decision 3: Token endpoint rate limiting
- **Decision**: Implement simple in-process per-IP rate limiter for `/token` endpoint.
- **Rationale**: Meets requirement without introducing new dependencies or services.
- **Alternatives considered**: SlowAPI (dependency), reverse-proxy rate limiting (NGINX/Cloudflare).

## Decision 4: Origin enforcement
- **Decision**: Validate `Origin` header against allowed frontend origins on protected endpoints.
- **Rationale**: Simple additional check aligned with browser-based clients; avoids reliance on `Referer`.
- **Alternatives considered**: Referer-based validation, no origin validation.

## Decision 5: Token endpoint path
- **Decision**: Use `POST /token` for token issuance.
- **Rationale**: Simple, explicit endpoint name; avoids coupling to future user auth paths.
- **Alternatives considered**: `/auth/token`, `/session/token`.
