# Security Documentation

**Last Updated**: February 3, 2026  
**Feature**: Cookie-Based JWT Authentication

## Overview

The Timeline API implements cookie-based JWT authentication to protect against unauthorized access and abuse. This document explains the security model, threat protections, and best practices.

## Authentication Architecture

### Cookie-Based Session Authentication

**Why cookies over Authorization headers?**

The API uses `HttpOnly` cookies with JWT tokens instead of Authorization headers for several security reasons:

1. **Browser-Enforced Security**: Cookies cannot be set by non-browser clients, preventing trivial spoofing
2. **XSS Protection**: `HttpOnly` flag prevents JavaScript access to tokens
3. **CSRF Protection**: `SameSite=Strict` flag prevents cross-site request forgery
4. **Automatic Handling**: Browser manages cookie lifecycle, reducing attack surface

### Security Properties

| Property | Value | Purpose |
|----------|-------|---------|
| `HttpOnly` | true | Prevents JavaScript access (XSS mitigation) |
| `Secure` | true (production) | HTTPS-only transmission (MitM protection) |
| `SameSite` | Strict | Prevents CSRF attacks |
| Cookie Name | `auth_token` | Configurable via `COOKIE_NAME` |
| Max-Age | 900 seconds (15 min) | Limits replay window |

## Threat Model & Mitigations

### ✅ Cross-Site Scripting (XSS)

**Threat**: Malicious JavaScript steals authentication tokens  
**Mitigation**: `HttpOnly` cookies cannot be accessed by JavaScript, even if XSS exists

**Why this works**: The browser enforces `HttpOnly` at the engine level. Even `document.cookie` cannot read the token.

### ✅ Cross-Site Request Forgery (CSRF)

**Threat**: Attacker tricks user into making authenticated requests to our API  
**Mitigation**: `SameSite=Strict` prevents cookies from being sent on cross-site requests

**Why this works**: 
- `Strict` mode: Cookies only sent when request originates from same domain
- Browser enforces this policy before sending any request
- No token in request → 401 Unauthorized

**Alternative for embedded content**: Use `SameSite=Lax` if you need to support top-level navigation from external sites (e.g., email links).

### ✅ Origin Header Spoofing

**Threat**: Non-browser client spoofs `Origin` header to bypass authentication  
**Mitigation**: Cookies cannot be set/sent by non-browser clients (browser-enforced security)

**Previous vulnerability**: Authorization header + Origin validation was bypassable because non-browser clients can fake any header.

**Current protection**: Even if a non-browser client sends a fake `Origin` header, it:
1. Cannot receive the `Set-Cookie` response (browsers only)
2. Cannot send cookies in subsequent requests (browsers only)
3. Gets 401 Unauthorized on all protected endpoints

### ✅ Token Replay Attacks

**Threat**: Attacker intercepts token and reuses it indefinitely  
**Mitigations**:
1. **Short TTL**: Tokens expire after 15 minutes (configurable)
2. **HTTPS in Production**: `Secure` flag prevents interception on the wire
3. **Signature Validation**: HMAC-SHA256 signature prevents token forgery

**Limitation**: Tokens are reusable within their 15-minute window. This is by design (standard JWT behavior) and acceptable for this use case.

**Why no jti replay cache?**: 
- Adds complexity (distributed cache coordination in multi-instance deployments)
- Short TTL (15 min) provides sufficient protection for anti-scraping use case
- Not user authentication (no high-value accounts being protected)

### ✅ Rate Limit Bypass

**Threat**: Attacker floods `/token` endpoint to get unlimited sessions  
**Mitigations**:
1. **Per-IP Rate Limiting**: 60 requests/minute with 10-request burst (configurable)
2. **Token-bucket algorithm**: Smooth rate limiting with burst handling
3. **429 Too Many Requests**: Clear feedback when limit exceeded

**Configuration**:
```bash
API_RATE_LIMIT_PER_MINUTE=60  # Requests per minute
API_RATE_LIMIT_BURST=10       # Additional burst capacity
```

### ✅ Man-in-the-Middle (MitM)

**Threat**: Attacker intercepts network traffic and steals cookies  
**Mitigations**:
1. **HTTPS Required in Production**: `COOKIE_SECURE=true` enforces TLS
2. **HSTS Headers**: Force HTTPS for all connections (add to nginx/load balancer)
3. **Certificate Pinning**: Optional for high-security deployments

**Development vs Production**:
- **Local Dev**: `COOKIE_SECURE=false` allows HTTP testing
- **Production**: `COOKIE_SECURE=true` REQUIRED - cookies only sent over HTTPS

### ⚠️ Brute Force Token Guessing

**Threat**: Attacker tries to guess valid JWT signatures  
**Protection**: HMAC-SHA256 with 256-bit secret makes brute force computationally infeasible

**Key Management**:
- Generate strong random secrets: `openssl rand -base64 32`
- Never commit secrets to version control
- Rotate secrets periodically (causes logout for all users)

### ⚠️ Timing Attacks

**Threat**: Attacker infers information from response timing differences  
**Mitigation**: PyJWT's `decode()` uses constant-time comparison for signatures

**Additional note**: Response times may vary based on database query complexity, but authentication validation itself is constant-time.

### ❌ Out of Scope

These threats are **not addressed** by the current system:

1. **User Authentication**: No login system - all clients share same authentication
2. **Session Revocation**: Cannot invalidate tokens before expiration (15-min window)
3. **Account Lockout**: No user accounts to lock out
4. **Distributed DoS**: Rate limiting is per-instance, not global across load balancers
5. **SQL Injection**: Mitigated by database layer (psycopg2 parameterized queries), not auth

## Production Deployment Checklist

### Required Security Configurations

- [ ] **Set Strong JWT Secret**: `API_JWT_SECRET="<256-bit-random>"`
- [ ] **Enable Secure Cookies**: `COOKIE_SECURE=true`
- [ ] **Restrict CORS Origins**: `CORS_ALLOWED_ORIGINS="https://yourdomain.com"`
- [ ] **Enable HTTPS**: Configure reverse proxy (nginx/Cloudflare) for TLS
- [ ] **Add HSTS Header**: `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- [ ] **Remove Default Secrets**: Never use test/development secrets in production

### Recommended Security Configurations

- [ ] **Adjust Rate Limits**: Tune based on expected traffic patterns
- [ ] **Set SameSite Policy**: Use `Strict` unless you need `Lax` for external links
- [ ] **Add Security Headers**: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`
- [ ] **Enable Logging**: Monitor failed auth attempts and rate limit hits
- [ ] **Set Up Alerts**: Notify on suspicious patterns (e.g., 10+ failed auths from one IP)

### Secret Generation

Generate strong secrets for production:

```bash
# JWT signing secret (256 bits)
openssl rand -base64 32

# Or use Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Configuration Reference

### Environment Variables

| Variable | Default | Production | Purpose |
|----------|---------|------------|---------|
| `API_JWT_SECRET` | *none* | **REQUIRED** | JWT signing key |
| `COOKIE_SECURE` | `false` | `true` | HTTPS-only cookies |
| `COOKIE_SAMESITE` | `Strict` | `Strict` | CSRF protection |
| `COOKIE_NAME` | `auth_token` | (any) | Cookie identifier |
| `COOKIE_DOMAIN` | (none) | (optional) | Multi-subdomain support |
| `API_TOKEN_TTL_SECONDS` | `900` | `900` | Session duration (15 min) |
| `API_RATE_LIMIT_PER_MINUTE` | `60` | (tune) | Token requests per minute |
| `API_RATE_LIMIT_BURST` | `10` | (tune) | Burst allowance |
| `CORS_ALLOWED_ORIGINS` | `localhost:3000` | **YOUR_DOMAIN** | Allowed origins |

### Example Production Config

```bash
# .env.production
API_JWT_SECRET="<redacted-256-bit-random>"
COOKIE_SECURE=true
COOKIE_SAMESITE=Strict
CORS_ALLOWED_ORIGINS="https://timeline.yourdomain.com"
API_RATE_LIMIT_PER_MINUTE=100
API_RATE_LIMIT_BURST=20
```

## Incident Response

### Suspected Token Compromise

If you suspect JWT secret compromise:

1. **Generate New Secret**: `openssl rand -base64 32`
2. **Update Environment**: Set new `API_JWT_SECRET`
3. **Restart API**: `docker-compose restart api`
4. **Impact**: All existing sessions invalidated (users must re-authenticate)

### Rate Limit Abuse

If you see sustained rate limit hits:

1. **Check Logs**: `docker-compose logs api | grep "Rate limit"`
2. **Identify IP**: Look for patterns in source IPs
3. **Block at Network Layer**: Use firewall/WAF to block abusive IPs
4. **Adjust Limits**: Temporarily reduce `API_RATE_LIMIT_PER_MINUTE`

### CORS Misconfiguration

If users report authentication failures:

1. **Verify Origins**: Check `CORS_ALLOWED_ORIGINS` matches your domain
2. **Check Whitespace**: Ensure no spaces in comma-separated list
3. **Test CORS**: Use browser DevTools → Network → Check preflight OPTIONS requests
4. **Restart API**: Config changes require restart

## Monitoring & Logging

### Authentication Events to Monitor

1. **Failed Authentication Attempts**
   - Log: "Authentication failed: <reason>"
   - Alert: 10+ failures from same IP in 1 minute

2. **Rate Limit Hits**
   - Log: "Rate limit exceeded for IP: <ip>"
   - Alert: Sustained rate limit hits (possible abuse)

3. **User-Agent Patterns**
   - Log: Client type (browser/cli/bot) for each request
   - Monitor: Unusual patterns (e.g., sudden increase in bot traffic)

4. **Cookie Rejection**
   - Log: Missing/invalid/expired cookies
   - Monitor: High rate may indicate client misconfiguration

### Example Log Queries

```bash
# Failed auth attempts by IP
docker-compose logs api | grep "Could not validate credentials" | awk '{print $X}' | sort | uniq -c

# Rate limit events
docker-compose logs api | grep "Rate limit exceeded"

# User-agent distribution
docker-compose logs api | grep "User-Agent" | awk -F'User-Agent:' '{print $2}' | sort | uniq -c
```

## Testing Security

### Manual Security Tests

```bash
# Test 1: Cookie not sent without credentials
curl http://localhost:8000/events
# Expected: 401 Unauthorized

# Test 2: Get session cookie
curl -c cookies.txt -X POST http://localhost:8000/token
# Expected: 200 OK, Set-Cookie header

# Test 3: Use session cookie
curl -b cookies.txt http://localhost:8000/events
# Expected: 200 OK, events returned

# Test 4: Rate limiting
for i in {1..70}; do curl -X POST http://localhost:8000/token; done
# Expected: First 60 succeed, then 429 Too Many Requests
```

### Automated Security Tests

Run the test suite:

```bash
# Unit tests (includes auth tests)
docker-compose run --rm api python -m pytest tests/unit/

# Integration tests (includes cookie auth tests)
docker-compose run --rm api python -m pytest tests/integration/test_cookie_auth.py -v
```

## References

- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [MDN: Using HTTP cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies)
- [RFC 6265: HTTP State Management Mechanism (Cookies)](https://datatracker.ietf.org/doc/html/rfc6265)
- [RFC 7519: JSON Web Token (JWT)](https://datatracker.ietf.org/doc/html/rfc7519)

## Contact

For security issues or questions, please contact the development team.
