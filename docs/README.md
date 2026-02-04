# Atomic Reimport and Enrichment System

This directory contains documentation for the atomic reimport feature and event enrichment architecture.

## Table of Contents

1. [Overview](#overview)
2. [API Authentication](#api-authentication)
3. [Atomic Reimport Guide](#atomic-reimport-guide)
4. [Event Key System](#event-key-system)
5. [Enrichment Architecture](#enrichment-architecture)
6. [Usage Examples](#usage-examples)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The Timeline application implements a two-tier data architecture that separates:

- **First-order data**: Raw historical facts from Wikipedia (`historical_events` table)
- **Second-order data**: Enrichments like categories, interest counts, notes (`event_enrichments`, `event_categories` tables)

This architecture allows you to:
- ✅ **Refresh Wikipedia data** without losing user-generated enrichments
- ✅ **Preserve AI categorizations** across reimports
- ✅ **Track user engagement** (interest counts) persistently
- ✅ **Automatically clean up** orphaned enrichments

---

## API Authentication

All API endpoints require JWT authentication via secure cookies (except `/token`).

### Authentication Flow

```
1. Browser → POST /token (no headers needed)
   ← API sets HttpOnly cookie with JWT (15-minute TTL)

2. Browser → GET /events (cookie sent automatically with credentials: 'include')
   ← API validates cookie, returns data

3. Cookie reusable for 15 minutes, then browser requests new session
```

### Cookie-Based Authentication

**Why cookies instead of tokens?**
- **Better Security**: HttpOnly cookies cannot be accessed by JavaScript (XSS protection)
- **Browser Enforced**: Non-browser clients cannot fake cookie behavior
- **CSRF Protection**: SameSite=Strict flag prevents cross-site attacks
- **Simpler Frontend**: No manual token management needed

### Required Fetch Options

All API requests from the browser must include:

```javascript
fetch('http://localhost:8000/events', {
  credentials: 'include'  // Critical: ensures cookies are sent/received
});
```

### Authentication Rules

1. **All endpoints protected** except `/token` and `/logout`
2. **Cookie validation required**: Valid JWT in `auth_token` cookie
3. **Cookie expiration**: Sessions expire after 15 minutes (configurable via `API_TOKEN_TTL_SECONDS`)
4. **Cookie reusability**: Same cookie can be used multiple times within TTL
5. **Rate limiting**: Token issuance limited to 60 requests/minute per IP (configurable)

### Configuration

Set these environment variables in `docker-compose.yml` or `.env`:

```bash
# Required
API_JWT_SECRET="test-jwt-secret-67890"

# Optional - Cookie Settings
COOKIE_NAME="auth_token"                 # Cookie name (default)
COOKIE_SECURE="false"                    # Set to "true" in production (HTTPS only)
COOKIE_SAMESITE="Strict"                 # CSRF protection (Strict or Lax)
COOKIE_DOMAIN=""                         # Multi-subdomain support (optional)

# Optional - Rate Limiting
API_TOKEN_TTL_SECONDS=900                # Token expiration (default: 15 minutes)
API_RATE_LIMIT_PER_MINUTE=60             # Token requests per minute
API_RATE_LIMIT_BURST=10                  # Burst allowance
CORS_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
```

**⚠️ Production Security**: 
- Set `COOKIE_SECURE=true` to enforce HTTPS-only cookies
- Restrict `CORS_ALLOWED_ORIGINS` to your domain only
- Use a strong random string for `API_JWT_SECRET` (256+ bits)

### Error Responses

- **401 Unauthorized**: Missing/invalid/expired cookie, or `credentials: 'include'` not set
- **429 Too Many Requests**: Rate limit exceeded on `/token` endpoint

See [api/README.md](../api/README.md) for detailed authentication documentation.

---

## Atomic Reimport Guide

### What Is Atomic Reimport?

Atomic reimport allows you to reimport Wikipedia data while preserving all enrichment data. This is accomplished using:

1. **Deterministic event keys** - SHA-256 hash of title + dates + description
2. **Temporary table import** - Import into `historical_events_temp` first
3. **Atomic table swap** - Swap tables in a single transaction (< 1 second downtime)
4. **Automatic orphan cleanup** - Foreign key constraints remove stale enrichments

### When to Use Atomic Reimport

#### Use Atomic Reimport When:
- Refreshing Wikipedia content monthly/quarterly
- Updating specific time periods after Wikipedia corrections
- Preserving user-assigned categories and AI classifications
- Maintaining interest counts and engagement metrics

#### Use Standard Reimport When:
- Starting completely fresh with no existing enrichments
- Testing with sample data
- Schema has changed significantly

### Basic Usage

#### Full Reimport (All Configured Years)

```bash
./scripts/atomic-reimport
```

This reimports the full date range configured in your `.env` file.

#### Partial Reimport (Specific Date Range)

```bash
./scripts/atomic-reimport "1000 BC" "2026 AD"
```

This reimports only events within the specified range.

### How It Works

The atomic reimport process follows these steps:

#### Step 1: Extract (Generate Artifacts)

```bash
# Run with ETL Extract stage
WIKI_MIN_YEAR="1000 BC" WIKI_MAX_YEAR="2026 AD" \
  docker-compose run --rm wikipedia-ingestion
```

This generates JSON artifact files in `wikipedia-ingestion/logs/`.

#### Step 2: Load with Upsert

```bash
# Run with ETL Load stage (upsert mode)
LOADER_MODE=upsert docker-compose run --rm database-loader
```

**Upsert Process:**
1. **Collect URLs**: Gather all unique URLs from all artifacts
2. **Delete by URL**: Remove all events with matching URLs from database
3. **Insert events**: Insert all events from artifacts

**Key guarantee:** All deletions complete before any insertions, even if the same URL appears in multiple artifacts.

### What Gets Preserved?

#### ✅ Preserved (if event content unchanged)
- User-assigned categories
- AI-generated categorizations
- Interest counts from user engagement
- Last enrichment timestamp
- Any custom enrichment data

#### ❌ Not Preserved (orphaned automatically)
- Enrichments for events no longer in Wikipedia
- Enrichments for events whose core content changed significantly
  - Different title → new event_key
  - Different dates → new event_key
  - Different description → new event_key

### Verification

After running atomic reimport, verify the results:

```bash
# Check event count
docker-compose exec database psql -U timeline -d timeline \
  -c "SELECT COUNT(*) FROM historical_events;"

# Check enrichment preservation
docker-compose exec database psql -U timeline -d timeline \
  -c "SELECT 
        (SELECT COUNT(*) FROM event_enrichments) as enrichments,
        (SELECT COUNT(*) FROM event_categories) as categories,
        (SELECT COUNT(*) FROM historical_events) as events;"

# Sample enriched events
docker-compose exec database psql -U timeline -d timeline \
  -c "SELECT he.title, he.start_year, ee.interest_count, 
       STRING_AGG(ec.category, ', ') as categories
      FROM historical_events he
      LEFT JOIN event_enrichments ee ON he.event_key = ee.event_key
      LEFT JOIN event_categories ec ON he.event_key = ec.event_key
      WHERE ee.event_key IS NOT NULL
      GROUP BY he.title, he.start_year, ee.interest_count
      LIMIT 10;"
```

---

## Event Key System

### What Is an Event Key?

An **event key** is a deterministic SHA-256 hash computed from an event's core content:
- Title
- Start year
- End year
- Description

Because the hash is deterministic, the same event always produces the same key, allowing enrichments to persist across reimports.

### Computing Event Keys

```python
from event_key import compute_event_key

# Compute from individual fields
key = compute_event_key(
    title="Battle of Hastings",
    start_year=1066,
    end_year=1066,
    description="William the Conqueror defeats Harold II at Hastings"
)
# Returns: "e4f2c1b8a9d3..." (64-character hexadecimal string)

# Compute from event dict
from event_key import compute_event_key_from_dict

event = {
    "title": "Battle of Hastings",
    "start_year": 1066,
    "end_year": 1066,
    "description": "William the Conqueror defeats Harold II at Hastings"
}
key = compute_event_key_from_dict(event)
```

### Key Properties

- **Deterministic**: Same input always produces same output
- **Collision-resistant**: 64-character hex (256-bit hash space)
- **Normalized**: Handles whitespace, None values, Unicode consistently
- **Validated**: Format validation function available

### Validation

```python
from event_key import validate_event_key

if validate_event_key(key):
    print("Valid event key")
else:
    print("Invalid event key format")
```

Valid format: Exactly 64 hexadecimal characters (SHA-256 output).

---

## Enrichment Architecture

### Database Schema

#### historical_events (First-Order Data)

```sql
CREATE TABLE historical_events (
    id SERIAL PRIMARY KEY,
    event_key TEXT UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    start_year INTEGER,
    end_year INTEGER,
    is_bc_start BOOLEAN NOT NULL,
    is_bc_end BOOLEAN NOT NULL,
    -- ... other fields
);

CREATE INDEX idx_event_key ON historical_events(event_key);
```

#### event_enrichments (Second-Order Data)

```sql
CREATE TABLE event_enrichments (
    event_key TEXT PRIMARY KEY,
    interest_count INTEGER DEFAULT 0,
    last_enriched_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (event_key) 
        REFERENCES historical_events(event_key) 
        ON DELETE CASCADE
);
```

#### event_categories (Second-Order Data)

```sql
CREATE TABLE event_categories (
    event_key TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    PRIMARY KEY (event_key, category),
    FOREIGN KEY (event_key) 
        REFERENCES historical_events(event_key) 
        ON DELETE CASCADE
);

CREATE INDEX idx_category ON event_categories(category);
```

### Data Flow Diagram

```
┌─────────────────────────┐
│   historical_events     │  ← Raw Wikipedia data (first-order)
│  (event_key, title,     │     Reimported regularly
│   dates, description)   │
└──────────┬──────────────┘
           │
           │ event_key (deterministic hash)
           │ Foreign key with ON DELETE CASCADE
           │
           ├─────────────────────────┐
           │                         │
           ▼                         ▼
┌──────────────────────┐   ┌──────────────────────┐
│  event_enrichments   │   │  event_categories    │
│  (event_key,         │   │  (event_key,         │
│   interest_count,    │   │   category)          │
│   last_enriched_at)  │   │                      │
└──────────────────────┘   └──────────────────────┘
        ↑                           ↑
        └───── Enriched data (second-order)
               Persists across reimports
```

### Key Features

#### 1. Persistence Across Reimports

When Wikipedia data is reimported:
- Each event gets the same `event_key` if content is unchanged
- Enrichments remain associated via `event_key`
- No manual reconciliation needed

#### 2. Automatic Orphan Cleanup

The `ON DELETE CASCADE` constraint ensures:
- When an event is deleted, enrichments are automatically removed
- When event content changes (new event_key), old enrichments become orphans
- Orphans are cleaned up during the next reimport or manually with pruning script

#### 3. Multiple Categories Per Event

The `event_categories` table uses a composite primary key `(event_key, category)`, allowing:
- Multiple categories per event
- Efficient filtering by category
- No duplicate category assignments

---

## Usage Examples

### Adding Enrichments During Ingestion

```python
from event_key import compute_event_key

# During ingestion
event_key = compute_event_key(
    title=event["title"],
    start_year=event.get("start_year") or 0,
    end_year=event.get("end_year") or 0,
    description=event.get("description")
)

# Insert event with event_key
cursor.execute("""
    INSERT INTO historical_events 
        (event_key, title, description, start_year, end_year, ...)
    VALUES (%s, %s, %s, %s, %s, ...)
""", (event_key, title, description, start_year, end_year, ...))
```

### Adding User Interest

```python
from event_key import compute_event_key_from_dict

# Get event from database
event = get_event_by_id(event_id)

# Compute its key
key = compute_event_key_from_dict(event)

# Increment interest count
cursor.execute("""
    INSERT INTO event_enrichments (event_key, interest_count)
    VALUES (%s, 1)
    ON CONFLICT (event_key) 
    DO UPDATE SET 
        interest_count = event_enrichments.interest_count + 1,
        last_enriched_at = NOW()
""", (key,))
```

### Adding Categories

```python
from event_key import compute_event_key_from_dict

# Get event from database
event = get_event_by_id(event_id)

# Compute its key
key = compute_event_key_from_dict(event)

# Add category (idempotent)
cursor.execute("""
    INSERT INTO event_categories (event_key, category)
    VALUES (%s, %s)
    ON CONFLICT DO NOTHING
""", (key, "War & Conflict"))
```

### Querying Enriched Events

```sql
-- Get events with their enrichments
SELECT 
    he.id,
    he.title,
    he.start_year,
    he.end_year,
    ee.interest_count,
    ee.last_enriched_at,
    ARRAY_AGG(ec.category) FILTER (WHERE ec.category IS NOT NULL) as categories
FROM historical_events he
LEFT JOIN event_enrichments ee ON he.event_key = ee.event_key
LEFT JOIN event_categories ec ON he.event_key = ec.event_key
GROUP BY he.id, he.title, he.start_year, he.end_year, ee.interest_count, ee.last_enriched_at;
```

### Manual Orphan Pruning

```bash
# Dry run (see what would be deleted)
docker-compose run --rm wikipedia-ingestion \
  python scripts/prune_orphaned_enrichments.py --dry-run --verbose

# Actually delete orphans
docker-compose run --rm wikipedia-ingestion \
  python scripts/prune_orphaned_enrichments.py --verbose
```

---

## Troubleshooting

### Enrichments Missing After Reimport

**Symptom:** Categories or interest counts missing after running atomic reimport.

**Cause:** Event content changed, resulting in a new event_key.

**Diagnosis:**
```python
from event_key import compute_event_key

old_key = compute_event_key("Old Title", 2020, 2020, "Old description")
new_key = compute_event_key("New Title", 2020, 2020, "Old description")
# These will be different!
```

**Solution:** This is expected behavior. The event has changed, so it gets a new identity. Old enrichments are considered stale and are cleaned up.

### Import Failed Mid-Process

**Symptom:** Error during atomic reimport.

**What happens:**
1. Artifacts remain in `logs/` directory
2. Database unchanged (upsert mode rolls back on error)
3. Check logs for the error

**Fix:**
```bash
# Check error logs
cat wikipedia-ingestion/logs/ingest_*.error.log

# Fix the issue, then retry
./scripts/atomic-reimport
```

### Want to Keep Old Data for Comparison

**Solution:** Backup enrichments before reimport:

```bash
docker-compose exec database pg_dump -U timeline \
  -t event_enrichments -t event_categories timeline \
  > enrichments_backup_$(date +%Y%m%d).sql
```

### Check Orphan Count

```bash
# Count orphaned enrichments
docker-compose exec database psql -U timeline -d timeline -c "
  SELECT COUNT(*) as orphaned_enrichments
  FROM event_enrichments ee
  WHERE NOT EXISTS (
    SELECT 1 FROM historical_events he 
    WHERE he.event_key = ee.event_key
  );
"

# Count orphaned categories
docker-compose exec database psql -U timeline -d timeline -c "
  SELECT COUNT(*) as orphaned_categories
  FROM event_categories ec
  WHERE NOT EXISTS (
    SELECT 1 FROM historical_events he 
    WHERE he.event_key = ec.event_key
  );
"
```

---

## Related Documentation

- **`SPEC.md`** - Implementation specification and history
- **`../wikipedia-ingestion/README.md`** - Ingestion system usage guide
- **`../wikipedia-ingestion/SPEC.md`** - Ingestion refactoring chronology
- **`../database/init.sql`** - Database schema definition
- **`../scripts/atomic-reimport`** - Atomic reimport orchestration script
- **`../scripts/prune_orphaned_enrichments.py`** - Manual orphan cleanup utility

---

## Next Steps

1. **API Integration**: Update `/events` endpoint to join and return enrichment data
2. **LLM Categorization**: Implement automated event categorization
3. **User Tracking**: Add interest tracking when users view events
4. **Frontend UI**: Display categories and interest counts
5. **Scheduled Reimports**: Set up monthly cron job for automatic refreshes
