# Timeline API

FastAPI-based REST API providing access to historical timeline data with JWT authentication.

## Quick Start

### Running the API (Docker Container)

⚠️ **Important**: The API always runs in a Docker container. Do not attempt to run it standalone with `uvicorn`.

```bash
# Start all services (API will start in Docker container)
cd /Users/chris/Timeline
docker-compose up -d

# API will be available at http://localhost:8000
```

The API container automatically:
- Connects to the PostgreSQL database (also in Docker)
- Mounts the schema file for JSON validation
- Sets up all environment variables
- Enables hot reload for development

### API Documentation

- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Authentication

All API endpoints (except `/token`) require JWT authentication via secure cookies.

### How Cookie Authentication Works

1. **Obtain Session**: Call `POST /token` - the API sets an `HttpOnly` cookie automatically
2. **Automatic Authentication**: Browser sends cookie with all subsequent requests
3. **No Manual Token Management**: No need to handle tokens in JavaScript

This approach provides better security than Authorization headers:
- Cookies cannot be spoofed by non-browser clients
- `HttpOnly` flag prevents JavaScript access (XSS protection)
- `SameSite=Strict` prevents CSRF attacks
- Browser enforces same-origin cookie policy

### Obtaining a Session (Browser Clients)

**Endpoint**: `POST /token`

**Headers**: None required (browser automatically sends Origin)

**Request**:
```javascript
// JavaScript/Browser
fetch('http://localhost:8000/token', {
  method: 'POST',
  credentials: 'include'  // Critical: ensures cookie is set and sent
});
```

**Response**: 
- **Status**: 200 OK
- **Set-Cookie**: `auth_token=<jwt>; HttpOnly; Secure; SameSite=Strict`
- **Body**: `{"status": "authenticated"}`

### Using Authenticated Endpoints

Once you have a session, simply include `credentials: 'include'` in all fetch requests:

```javascript
// All subsequent requests automatically include the cookie
fetch('http://localhost:8000/events', {
  credentials: 'include'
});
```

**No Authorization header needed!** The browser handles everything.

### Logout

**Endpoint**: `POST /logout`

Clears the authentication cookie:

```javascript
fetch('http://localhost:8000/logout', {
  method: 'POST',
  credentials: 'include'
});
```

### Cookie Details

- **Name**: `auth_token` (configurable via `COOKIE_NAME`)
- **Algorithm**: HMAC-SHA256 (HS256)
- **Expiration**: 15 minutes (900 seconds)
- **Reusability**: Cookies can be used multiple times within their TTL
- **Security Flags**:
  - `HttpOnly`: Cannot be accessed by JavaScript
  - `Secure`: Only sent over HTTPS (production)
  - `SameSite=Strict`: Prevents CSRF attacks

### Rate Limiting

Token issuance is rate-limited:
- **Default**: 60 requests per minute per IP
- **Burst**: 10 additional requests allowed
- **Response**: HTTP 429 when limit exceeded

### Non-Browser Clients (curl, Postman, etc.)

Cookie-based auth is designed for browser clients. For testing with non-browser tools:

```bash
# Step 1: Get cookie from /token
curl -c cookies.txt -X POST http://localhost:8000/token

# Step 2: Use cookie in subsequent requests
curl -b cookies.txt http://localhost:8000/events
```

## Endpoints

### Health Check

`GET /health`

**Authentication**: Required ⚠️

**Response**:
```json
{
  "status": "healthy"
}
```

### Events

`GET /events`

Get paginated list of historical events.

**Authentication**: Required

**Query Parameters**:
- `limit` (int): Maximum number of events to return (default: 100)
- `offset` (int): Number of events to skip (default: 0)

### Event Bins

`GET /events/bins`

Get events grouped by time bins for timeline visualization.

**Authentication**: Required

**Query Parameters**:
- `viewport_center` (float): Center year of the viewport
- `viewport_span` (float): Width of the viewport in years
- `zone` (str): Zone filter (center, buffer, extended)
- `limit` (int): Maximum events per bin
- `max_weight` (int): Maximum weight for filtering
- `strategy` (str): Filter by ingestion strategy (can be repeated)

### Categories

`GET /categories`

Get list of available event categories.

**Authentication**: Required

### Search

`GET /search`

Search for events by keyword.

**Authentication**: Required

**Query Parameters**:
- `q` (str): Search query
- `limit` (int): Maximum results (default: 20)

## Configuration

### Environment Variables

#### Required

- `API_JWT_SECRET`: Secret key for signing JWTs (CHANGE IN PRODUCTION!)

#### Optional - Authentication

- `COOKIE_NAME`: Name of the auth cookie (default: `auth_token`)
- `COOKIE_SECURE`: Set to `true` for HTTPS-only cookies (default: `false` for local dev)
- `COOKIE_SAMESITE`: CSRF protection mode - `Strict` or `Lax` (default: `Strict`)
- `COOKIE_DOMAIN`: Cookie domain for multi-subdomain support (default: none)
- `API_TOKEN_TTL_SECONDS`: Token expiration time (default: 900)
- `API_RATE_LIMIT_PER_MINUTE`: Rate limit for /token (default: 60)
- `API_RATE_LIMIT_BURST`: Burst allowance for rate limit (default: 10)
- `CORS_ALLOWED_ORIGINS`: CORS origins (default: `http://localhost:3000,http://127.0.0.1:3000`)

#### Optional - Database

- `DB_HOST`: PostgreSQL host (default: database)
- `DB_PORT`: PostgreSQL port (default: 5432)
- `DB_NAME`: Database name (default: timeline_history)
- `DB_USER`: Database user (default: timeline_user)
- `DB_PASSWORD`: Database password (default: timeline_pass)

### Production Configuration

**⚠️ Security Notes for Production**:

1. **Change Default JWT Secret**: Never use the default value for `API_JWT_SECRET`
2. **Enable Secure Cookies**: Set `COOKIE_SECURE=true` to enforce HTTPS-only cookies
3. **Restrict CORS Origins**: Set `CORS_ALLOWED_ORIGINS` to your actual domain only
4. **Use HTTPS**: All production traffic must use HTTPS for secure cookies
5. **Secure Environment Variables**: Store secrets in a secure vault, not in plaintext

Example production configuration:
```bash
API_JWT_SECRET="<generate-secure-random-string-256-bits>"
COOKIE_SECURE=true
COOKIE_SAMESITE=Strict
CORS_ALLOWED_ORIGINS="https://yourdomain.com"
```

## Error Responses

### Authentication Errors

**401 Unauthorized**:
```json
{
  "detail": "Could not validate credentials"
}
```

Common causes:
- Missing authentication cookie
- Invalid or expired cookie
- Cookie signature verification failed
- Cookie not sent due to `credentials: 'include'` missing

**429 Too Many Requests**:
```json
{
  "detail": "Rate limit exceeded"
}
```

Cause: Too many token requests from the same IP

## Development

### Running Tests

```bash
# Run all tests
docker-compose run --rm api python -m pytest

# Run specific test file
docker-compose run --rm api python -m pytest tests/unit/test_auth_config.py

# Run with coverage
docker-compose run --rm api python -m pytest --cov=auth --cov-report=html
```

### Project Structure

```
api/
├── api.py                  # Main FastAPI application
├── auth/                   # Authentication modules
│   ├── __init__.py
│   ├── auth_dependency.py  # FastAPI auth dependency
│   ├── config.py           # Configuration loader
│   ├── jwt_service.py      # JWT encode/decode
│   ├── rate_limiter.py     # Rate limiting
│   └── replay_cache.py     # Token replay prevention
├── tests/
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
└── requirements.txt
```

## Troubleshooting

### "Could not validate credentials"

Common causes:
1. Cookie missing or expired - call `POST /token` to get a new session
2. Forgot `credentials: 'include'` in fetch() - browser won't send cookies
3. CORS issue - check that origin is in `CORS_ALLOWED_ORIGINS`

### CORS Errors

If you see CORS errors in the browser console:
1. Check that your frontend origin is in `CORS_ALLOWED_ORIGINS`
2. Ensure there's no whitespace in the comma-separated list
3. Verify `credentials: 'include'` is set in all fetch() calls
4. Check browser Network tab for actual response status codes
5. Restart the API container after configuration changes

### Cookie Not Being Set

If `/token` returns 200 but cookie doesn't appear:
1. Check that `credentials: 'include'` is in the fetch() request
2. Verify CORS is configured correctly (same-origin or allowed origin)
3. In production, ensure `COOKIE_SECURE=true` and using HTTPS
4. Check browser DevTools → Application → Cookies

### Token Expired

Cookies expire after 15 minutes by default. The frontend should:
1. Detect 401 responses
2. Call `POST /token` to refresh the session
3. Retry the original request

Example retry logic:
```javascript
async authFetch(url, options = {}) {
  let response = await fetch(url, { ...options, credentials: 'include' });
  
  if (response.status === 401) {
    // Try to refresh session once
    await fetch('/token', { method: 'POST', credentials: 'include' });
    response = await fetch(url, { ...options, credentials: 'include' });
  }
  
  return response;
}
```

## License

See main project LICENSE file.
