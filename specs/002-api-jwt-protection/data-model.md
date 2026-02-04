# Phase 1 Data Model: API JWT Token Protection

## Entities

### TokenClaims
- **represents**: JWT claims included in access tokens
- **fields**:
  - `iss`: issuer identifier (string)
  - `aud`: audience identifier (string)
  - `exp`: expiration epoch seconds (int)
  - `iat`: issued-at epoch seconds (int)
  - `jti`: token ID (string)
  - `sub` (optional): subject identifier for future user auth (string)
  - `role` (optional): role/permission hint for future user auth (string)

### TokenRequest
- **represents**: token issuance request from frontend
- **fields**:
  - `X-Client-Secret` header (string)
  - `Origin` header (string, optional)

### ReplayCacheEntry
- **represents**: replay detection record for a `jti`
- **fields**:
  - `jti` (string)
  - `seen_at` (timestamp)
  - `expires_at` (timestamp)

### ClientSecretConfig
- **represents**: server-side client secret and allowed origins
- **fields**:
  - `client_secret` (string, from env)
  - `allowed_origins` (list of strings)

## Relationships
- TokenRequest → TokenResponse (one issuance yields one token)
- TokenClaims → ReplayCacheEntry (each issued `jti` is tracked for short replay window)
- ClientSecretConfig → TokenRequest (validation requirement)

## Validation Rules
- `exp` must be later than `iat`
- `jti` must be unique within replay window
- `Origin` must match allowed origin list on protected endpoints
- `X-Client-Secret` must match configured secret

## State Transitions
- Token lifecycle: issued → valid → expired (after `exp`)
- ReplayCacheEntry: created on token issuance → expires after replay window
