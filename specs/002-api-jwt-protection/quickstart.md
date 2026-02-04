# Phase 1 Quickstart: API JWT Token Protection

## Environment Variables

Set these in the API service environment:

- `API_CLIENT_SECRET`: shared secret used by frontend to obtain tokens
- `API_JWT_SECRET`: signing key for JWTs (HMAC)
- `API_JWT_ISSUER` (optional): issuer claim
- `API_JWT_AUDIENCE` (optional): audience claim
- `API_ALLOWED_ORIGINS`: comma-separated list of allowed frontend origins
- `API_TOKEN_TTL_SECONDS`: token lifetime (default 900)
- `API_TOKEN_REPLAY_WINDOW_SECONDS`: replay window for `jti` (default 900)

## Token Issuance

```bash
curl -X POST http://localhost:8000/token \
  -H "X-Client-Secret: test-client-secret-12345" \
  -H "Origin: http://localhost:3000"
```

Expected response:

```json
{
  "access_token": "<jwt>",
  "token_type": "Bearer",
  "expires_in": 900
}
```

**Note**: The `Origin` header is required for token issuance.

## Using the Token

```bash
curl http://localhost:8000/events \
  -H "Authorization: Bearer <jwt>" \
  -H "Origin: http://localhost:3000"
```

**Note**: All protected endpoints require a valid `Origin` header. Requests missing `Origin` are rejected.

## Frontend Usage

- Fetch token on app load.
- Cache token in memory.
- Refresh token on page reload or when token expires.
