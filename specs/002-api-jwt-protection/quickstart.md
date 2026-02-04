# Phase 1 Quickstart: API JWT Token Protection

## Environment Variables

Set these in the API service environment:

- `API_JWT_SECRET`: signing key for JWTs (HMAC)
- `API_JWT_ISSUER` (optional): issuer claim
- `API_JWT_AUDIENCE` (optional): audience claim
- `API_TOKEN_TTL_SECONDS`: token lifetime (default 900)
- `COOKIE_NAME`: cookie name for auth token (default timeline_auth)
- `COOKIE_SECURE`: set to true in production (default true)
- `COOKIE_SAMESITE`: Strict, Lax, or None (default Strict)
- `COOKIE_DOMAIN`: optional domain for cookie
- `CORS_ALLOWED_ORIGINS`: comma-separated list of allowed frontend origins
- `API_RATE_LIMIT_PER_MINUTE`: rate limit for token endpoint (default 60)
- `API_RATE_LIMIT_BURST`: burst limit (default 10)

## Token Issuance

Browsers automatically obtain tokens and store them in HTTP-only cookies:

```bash
curl -X POST http://localhost:8000/token \
  -c cookies.txt \
  -H "Origin: http://localhost:3000"
```

Expected response sets an HTTP-only cookie with the JWT:

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
