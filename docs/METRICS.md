# Authentication Metrics & Monitoring

**Feature**: Cookie-Based JWT Authentication  
**Last Updated**: February 3, 2026

## Overview

All authentication events are logged with structured fields for monitoring, alerting, and analysis. This document describes the metrics available and how to query them.

## Logged Events

### 1. Token Issuance (Success)

**Event**: User/client obtains a new session cookie  
**Endpoint**: `POST /token`  
**Log Level**: INFO

**Structured Fields**:
```json
{
  "message": "Token issued successfully via cookie",
  "client_ip": "192.168.1.100",
  "client_type": "browser",
  "browser": "Chrome 121.0",
  "confidence": 0.95,
  "token_id": "abc12345...",
  "expires_in": 900,
  "status_code": 200
}
```

**Use Cases**:
- Track authentication rate over time
- Identify user-agent patterns (browser vs bot)
- Detect unusual client types

### 2. Rate Limit Exceeded

**Event**: Client exceeded token issuance rate limit  
**Endpoint**: `POST /token`  
**Log Level**: WARNING

**Structured Fields**:
```json
{
  "message": "Token issuance rate limit exceeded",
  "client_ip": "192.168.1.100",
  "client_type": "cli",
  "status_code": 429
}
```

**Use Cases**:
- Detect abusive clients
- Identify IPs to block
- Adjust rate limit thresholds

### 3. Authentication Success

**Event**: Valid cookie authenticated successfully  
**Endpoint**: Any protected endpoint  
**Log Level**: INFO

**Structured Fields**:
```json
{
  "message": "Auth successful",
  "client_ip": "192.168.1.100",
  "endpoint": "/events",
  "token_id": "abc12345...",
  "status_code": 200
}
```

**Use Cases**:
- Track API usage by endpoint
- Correlate sessions across requests
- Identify high-traffic clients

### 4. Authentication Failure - Missing Cookie

**Event**: Request missing authentication cookie  
**Endpoint**: Any protected endpoint  
**Log Level**: WARNING

**Structured Fields**:
```json
{
  "message": "Auth failed: missing authentication cookie",
  "reason": "missing_cookie",
  "cookie_name": "auth_token",
  "client_ip": "192.168.1.100",
  "endpoint": "/events",
  "status_code": 401
}
```

**Use Cases**:
- Detect misconfigured clients
- Identify clients not calling /token
- Track authentication errors

### 5. Authentication Failure - Token Expired

**Event**: Cookie JWT has expired  
**Endpoint**: Any protected endpoint  
**Log Level**: WARNING

**Structured Fields**:
```json
{
  "message": "Auth failed: token expired",
  "reason": "token_expired",
  "client_ip": "192.168.1.100",
  "endpoint": "/events",
  "status_code": 401
}
```

**Use Cases**:
- Monitor token refresh patterns
- Identify clients not refreshing tokens
- Tune TTL based on usage

### 6. Authentication Failure - Invalid Token

**Event**: Cookie JWT signature invalid or malformed  
**Endpoint**: Any protected endpoint  
**Log Level**: WARNING

**Structured Fields**:
```json
{
  "message": "Auth failed: invalid token",
  "reason": "invalid_token",
  "error": "Signature verification failed",
  "client_ip": "192.168.1.100",
  "endpoint": "/events",
  "status_code": 401
}
```

**Use Cases**:
- Detect token tampering attempts
- Identify mismatched JWT secrets
- Monitor for attacks

### 7. Logout

**Event**: User explicitly logged out  
**Endpoint**: `POST /logout`  
**Log Level**: INFO

**Structured Fields**:
```json
{
  "message": "User logged out successfully",
  "client_ip": "192.168.1.100",
  "status_code": 200
}
```

**Use Cases**:
- Track logout frequency
- Understand user session behavior

## Metrics Queries

### View Logs in Real-Time

```bash
# All auth-related logs
docker-compose logs -f api | grep -E "(Auth|Token|logout)"

# Only failures
docker-compose logs -f api | grep -E "(Auth failed|Rate limit)"

# Only successes
docker-compose logs -f api | grep -E "(Auth successful|Token issued)"
```

### Count Authentication Events

```bash
# Total successful authentications today
docker-compose logs api --since 24h | grep "Auth successful" | wc -l

# Failed auth attempts by reason
docker-compose logs api --since 24h | grep "Auth failed" | \
  grep -oP '"reason": "\K[^"]+' | sort | uniq -c

# Rate limit hits
docker-compose logs api --since 24h | grep "Rate limit exceeded" | wc -l
```

### Identify Top IPs

```bash
# Top 10 IPs by auth attempts
docker-compose logs api --since 24h | grep "Auth" | \
  grep -oP '"client_ip": "\K[^"]+' | sort | uniq -c | sort -rn | head -10

# IPs hitting rate limits
docker-compose logs api --since 24h | grep "Rate limit exceeded" | \
  grep -oP '"client_ip": "\K[^"]+' | sort | uniq -c
```

### User-Agent Analysis

```bash
# Client type distribution
docker-compose logs api --since 24h | grep "Token issued" | \
  grep -oP '"client_type": "\K[^"]+' | sort | uniq -c

# Browser breakdown
docker-compose logs api --since 24h | grep "Token issued" | \
  grep -oP '"browser": "\K[^"]+' | sort | uniq -c
```

### Authentication Rate Over Time

```bash
# Successful authentications per hour (last 24h)
docker-compose logs api --since 24h | grep "Auth successful" | \
  awk '{print $1, $2}' | cut -d: -f1 | sort | uniq -c
```

## Alerting Rules

### Recommended Alerts

1. **High Auth Failure Rate**
   - Trigger: >10 failed auths from single IP in 1 minute
   - Action: Alert security team, consider IP block

2. **Sustained Rate Limiting**
   - Trigger: Same IP hits rate limit >5 times in 5 minutes
   - Action: Alert ops team, review rate limit config

3. **Invalid Token Spike**
   - Trigger: >50 "invalid token" errors in 1 minute
   - Action: Check for JWT secret mismatch or attack

4. **Zero Authentications**
   - Trigger: No successful auth for 10+ minutes during business hours
   - Action: Check API health, CORS config, frontend deployment

### Example Alertmanager Rules (Prometheus)

```yaml
groups:
- name: authentication
  rules:
  - alert: HighAuthFailureRate
    expr: rate(auth_failed_total[1m]) > 10
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "High authentication failure rate"
      description: "{{ $value }} auth failures per second"
  
  - alert: RateLimitAbuse
    expr: rate(rate_limit_exceeded_total[5m]) > 5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Client hitting rate limits"
      description: "{{ $labels.client_ip }} exceeded rate limit"
```

## Exporting Metrics to Prometheus

To enable Prometheus metrics, add a metrics exporter middleware:

```python
# api/api.py - Add prometheus_client
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
auth_success_total = Counter('auth_success_total', 'Successful authentications')
auth_failed_total = Counter('auth_failed_total', 'Failed authentications', ['reason'])
token_issued_total = Counter('token_issued_total', 'Tokens issued', ['client_type'])
rate_limit_exceeded_total = Counter('rate_limit_exceeded_total', 'Rate limit hits')

# Add to logging calls
logger.info("Auth successful", ...)
auth_success_total.inc()

# Expose metrics endpoint
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## Log Storage & Retention

### Development

Logs stored in Docker container stdout/stderr:
- **Location**: Docker daemon logs
- **Retention**: Until container restart
- **Access**: `docker-compose logs api`

### Production Recommendations

1. **Centralized Logging**: Ship logs to ELK, Splunk, or CloudWatch
2. **Retention**: 30-90 days for audit trail
3. **Indexing**: Index `client_ip`, `status_code`, `reason` for fast queries
4. **Compression**: Archive logs older than 7 days

### Example: Ship to ELK

```yaml
# docker-compose.yml
services:
  api:
    logging:
      driver: "fluentd"
      options:
        fluentd-address: localhost:24224
        tag: timeline.api
```

## Privacy & Compliance

### PII Considerations

Logged fields that may contain PII:
- **client_ip**: User IP address
- **user_agent**: Browser/OS information (indirect fingerprinting)

**Recommendations**:
1. Hash IPs before long-term storage: `sha256(ip + daily_salt)`
2. Anonymize after 7 days for GDPR compliance
3. Don't log full user-agent strings in production (use client_type only)

### Audit Requirements

For compliance audits, retain:
- All authentication attempts (success + failure)
- Rate limit events
- Token issuance logs

Minimum retention: 90 days (adjust per regulatory requirements)

## Dashboard Recommendations

### Key Metrics to Visualize

1. **Authentication Success Rate**
   - Formula: `successful_auths / (successful_auths + failed_auths)`
   - Target: >99%

2. **Token Issuance Rate**
   - Metric: Tokens issued per minute
   - Use for capacity planning

3. **Client Type Distribution**
   - Breakdown: Browser vs CLI vs Bot vs Unknown
   - Use to detect unusual patterns

4. **Top Endpoints by Traffic**
   - Metric: Requests per endpoint
   - Use to optimize caching

5. **P95 Authentication Latency**
   - Requires timing instrumentation (not currently logged)
   - Add with `time.perf_counter()` around auth logic

### Example Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Timeline Authentication Metrics",
    "panels": [
      {
        "title": "Auth Success Rate",
        "targets": [
          "rate(auth_success_total[5m]) / (rate(auth_success_total[5m]) + rate(auth_failed_total[5m]))"
        ]
      },
      {
        "title": "Token Issuance Rate",
        "targets": ["rate(token_issued_total[1m])"]
      },
      {
        "title": "Failed Auth Reasons",
        "targets": ["rate(auth_failed_total[5m]) by (reason)"]
      }
    ]
  }
}
```

## Troubleshooting with Metrics

### Scenario 1: Users Can't Authenticate

**Symptoms**: High "missing_cookie" failure rate  
**Diagnosis**:
```bash
docker-compose logs api | grep "missing_cookie" | head -20
```
**Likely Causes**:
- Frontend not calling `/token` on load
- `credentials: 'include'` missing from fetch()
- CORS blocking cookie delivery

### Scenario 2: Intermittent 401 Errors

**Symptoms**: "token_expired" failures spike at 15-minute intervals  
**Diagnosis**:
```bash
docker-compose logs api | grep "token_expired" | \
  awk '{print $1, $2}' | uniq -c
```
**Likely Causes**:
- Frontend not refreshing tokens on 401
- TTL too short for user workflow

### Scenario 3: Sudden Traffic Spike

**Symptoms**: Rate limit hits from many IPs  
**Diagnosis**:
```bash
docker-compose logs api | grep "Rate limit" | \
  grep -oP '"client_ip": "\K[^"]+' | sort | uniq -c
```
**Likely Causes**:
- DDoS attack (distributed IPs)
- Broken client retry loop (same IPs)
- Bot scraping attempt

## Future Enhancements

1. **Distributed Tracing**: Add OpenTelemetry for request flow visibility
2. **Performance Metrics**: Log auth latency (p50, p95, p99)
3. **Anomaly Detection**: ML-based detection of unusual auth patterns
4. **Session Analytics**: Track session duration, requests per session
5. **Geographic Analysis**: GeoIP lookup for client_ip to detect region anomalies

## References

- [Structured Logging Best Practices](https://www.structlog.org/)
- [Prometheus Monitoring Best Practices](https://prometheus.io/docs/practices/)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
