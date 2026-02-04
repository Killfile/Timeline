# Feature Specification: API JWT Token Protection

**Feature Branch**: `002-api-jwt-protection`  
**Created**: January 30, 2026  
**Status**: Draft  
**Input**: User description: "Protect the API by adding JWT tokens."

## Clarifications

### Session 2026-01-30

- Q: Should the token endpoint require any proof from the frontend (vs being fully public)? → A: Require a simple client secret (static key) from the frontend to obtain a token.
- Q: Which endpoints should require tokens? → A: Protect all endpoints, including health/status.
- Q: Should the client secret be shared across frontend instances or segmented? → A: Use a single shared secret for all frontend instances.
- Q: What should the access token expiration be? → A: 15 minutes.
- Q: Should we add replay mitigation beyond expiration? → A: Include a token ID (jti) and reject duplicates seen within a short window.
- Q: Where should the client secret be validated to obtain a token? → A: Validate in the API token endpoint (server-side check).
- Q: How should the client secret be provided by the frontend? → A: In an HTTP header (e.g., X-Client-Secret).
- Q: Should the token endpoint be rate-limited? → A: Yes, rate-limit per IP (e.g., 60/min).
- Q: Should tokens be bound to a specific origin? → A: Validate Origin header against allowed frontend origin(s).
- Q: Should tokens be cached in the frontend or fetched per page load? → A: Cache token in memory (refresh on reload).
- Q: How should missing Origin headers be handled? → A: Reject requests missing Origin.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Frontend Obtains Access Token (Priority: P1)

The frontend needs to obtain a token from the server before making API requests. This token serves as proof that requests are coming from the legitimate frontend application, not automated scrapers.

**Why this priority**: Without a way to obtain tokens, the frontend cannot authenticate itself to protected endpoints.

**Independent Test**: Can be fully tested by having the frontend call a token endpoint and receiving a valid JWT token that can be immediately used in subsequent API requests.

**Acceptance Scenarios**:

1. **Given** the frontend application starts, **When** it calls the token endpoint, **Then** it receives a valid JWT token
2. **Given** a newly issued token, **When** the frontend includes it in API requests, **Then** all requests are accepted
3. **Given** the token endpoint is called multiple times, **When** tokens are issued, **Then** all issued tokens are valid and accepted by the API
4. **Given** a token has been obtained, **When** the frontend includes it in the Authorization header as `Bearer <token>`, **Then** the API processes the request normally

---

### User Story 2 - API Validates Token on Protected Endpoints (Priority: P1)

All API endpoints that serve data to the frontend must validate that requests include a valid token. Requests without a token or with an invalid token are rejected, preventing automated scrapers from accessing the API.

**Why this priority**: This is the core protection mechanism. Without validation, the token system provides no security benefit.

**Independent Test**: Can be fully tested by attempting to call protected API endpoints with and without valid tokens, verifying that valid tokens succeed and missing/invalid tokens are rejected.

**Acceptance Scenarios**:

1. **Given** a valid token in the Authorization header, **When** a request is made to a protected endpoint, **Then** the request succeeds and data is returned
2. **Given** no token in the request, **When** a call is made to a protected endpoint, **Then** the API returns a 401 Unauthorized error
3. **Given** an invalid or malformed token, **When** a request is made to a protected endpoint, **Then** the API returns a 401 Unauthorized error
4. **Given** a token with a modified signature, **When** used in a request, **Then** the API rejects it as tampered and returns 401 Unauthorized

---

### User Story 3 - Token Expiration Limits Replay Attacks (Priority: P2)

Tokens should expire after a reasonable time period so that if a token is compromised, the window for abuse is limited. The frontend should be able to obtain a fresh token when needed.

**Why this priority**: Token expiration is a security best practice that reduces the impact if a token is stolen or intercepted. It also encourages the frontend to refresh its token periodically.

**Independent Test**: Can be tested by issuing a token with a short expiration, waiting for it to expire, and verifying that the expired token is rejected by the API.

**Acceptance Scenarios**:

1. **Given** an expired token, **When** used in an API request, **Then** the API returns a 401 Unauthorized error indicating expiration
2. **Given** a token approaching expiration, **When** the frontend calls the token endpoint again, **Then** it receives a fresh token
3. **Given** freshly issued tokens, **When** compared, **Then** each has an independent expiration time

### Edge Cases

- What happens if the frontend loses its token (browser tab closed, page refresh)? Should it fetch a new one?
- How does the system handle clock skew between frontend and API server?
- What happens if an attacker intercepts a token via network sniffing?
- How should the API respond if requests arrive in rapid succession with the same token?
- Should there be rate limiting on the token endpoint itself to prevent abuse?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a token endpoint that issues JWT tokens to the frontend when a valid client secret is provided
- **FR-002**: System MUST enforce token validation on all API endpoints (including health/status) and reject requests with invalid or missing tokens
- **FR-003**: System MUST return 401 Unauthorized HTTP status for requests with expired, invalid, or missing authentication tokens
- **FR-004**: System MUST include token expiration claims (exp) in all issued JWT tokens with a configurable expiration time (default: 15 minutes)
- **FR-005**: System MUST validate token signatures using a cryptographic key (HMAC256 or RSA) to prevent tampering
- **FR-006**: System MUST support the Bearer token format in the Authorization header: `Authorization: Bearer <token>`
- **FR-007**: System MUST include an issuance timestamp (iat) in tokens for logging and debugging
- **FR-008**: System MUST handle token validation failures gracefully with appropriate error messages in API responses
- **FR-009**: System MUST allow tokens to carry optional identity claims (e.g., subject or role) without changing validation rules for the current anti-scraping scope
- **FR-011**: System MUST include a token ID (jti) and reject replayed tokens seen within a configurable short window (default: 900 seconds)
- **FR-012**: System MUST validate the client secret on the API token endpoint before issuing a token
- **FR-013**: System MUST accept the client secret via an HTTP header (e.g., X-Client-Secret) on the token request
- **FR-014**: System MUST rate-limit the token endpoint per IP address (default: 60 requests/minute with burst up to 10)
- **FR-015**: System MUST validate the Origin header against allowed frontend origin(s) on protected endpoints
- **FR-017**: System MUST reject requests that omit the Origin header on protected endpoints
- **FR-016**: Frontend MUST cache the token in memory and refresh it on page reload

### Key Entities

- **JWT Token**: A digitally signed token containing claims about when it was issued and when it expires, used to authenticate requests from the frontend
- **Token Claim**: A key-value pair within a JWT (e.g., exp, iat) that contains metadata about the token
- **Bearer Token**: The token included in the Authorization header with the format `Bearer <token_value>`

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All data-serving API endpoints require valid JWT tokens; 100% of protected endpoints enforce token validation
- **SC-002**: Authentication failures (invalid/expired/missing tokens) return 401 Unauthorized within 50ms
- **SC-003**: Token issuance completes within 100ms with 99.9% success rate
- **SC-004**: Token validation occurs on every protected request with <20ms latency overhead
- **SC-005**: JWT token signatures validate correctly 100% of the time for authentic tokens and reject 100% of tampered/invalid tokens
- **SC-006**: Automated scrapers without valid tokens are unable to access protected API endpoints
- **SC-007**: Frontend can obtain tokens and make authenticated API requests with <1s total round-trip time (token fetch + data request)
- **SC-008**: API documentation clearly specifies which endpoints require authentication and the expected Bearer token format
- **SC-009**: System logs all API requests with authentication status (success/failure) for security monitoring
- **SC-010**: Token expiration is enforced; tokens older than configured expiration (15 minutes default) are rejected

## Assumptions

- Token endpoint requires a static client secret provided by the frontend (anti-scraping, not user auth)
- All requests from the frontend will include valid tokens obtained from the token endpoint
- A single shared client secret is used across all frontend instances
- HMAC256-based signing is acceptable for initial implementation
- Tokens have a fixed expiration time of 15 minutes; no refresh token mechanism required
- Replay window is 900 seconds by default; configurable via environment variable
- Clock skew between frontend and API server is negligible (<1 minute)
- Network communication is over HTTPS, protecting tokens from network-level interception
- The frontend is served from a known domain and will consistently use the same token endpoint
- The token format and validation pipeline can be extended later to support user authentication without breaking existing clients

## Out of Scope

- User authentication or login flows
- Multi-factor authentication (MFA)
- OAuth2 or external identity providers
- Role-based access control (RBAC) - all authenticated requests are treated equally
- Token revocation or logout mechanisms (tokens expire naturally)
- Token refresh endpoint (frontend gets new token by calling token endpoint again)
- Token auditing dashboards or detailed analytics
- Hardware security token (HSM) support
- User registration, account recovery, and password management
