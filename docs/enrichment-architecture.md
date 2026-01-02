# Event Key and Enrichment Architecture

## Overview

This document describes the implementation of a two-tier data architecture that allows enrichment data (AI categories, user interest, etc.) to persist across reimports of the `historical_events` table.

## Problem Statement

The `historical_events` table contains raw Wikipedia data that may be frequently dropped and reimported. We need a way to:
1. Store enrichment data (second-order data) that survives these reimports
2. Associate enrichments with events across reimports
3. Automatically prune enrichments when events are removed or significantly changed

## Solution: Deterministic Event Keys

### Event Key Computation

Each event gets a deterministic `event_key` computed as a SHA-256 hash of stable fields:

```python
from event_key import compute_event_key

key = compute_event_key(
    title="Battle of Hastings",
    start_year=1066,
    end_year=1066,
    description="William the Conqueror defeats Harold II..."
)
# Returns: "a1b2c3d4e5f6..." (64-char hex string)
```

The key is computed from:
- Event title (normalized, whitespace trimmed)
- Start year
- End year  
- Description (normalized, whitespace trimmed)

### Database Schema

**historical_events** (first-order data)
```sql
CREATE TABLE historical_events (
    id SERIAL PRIMARY KEY,
    event_key TEXT UNIQUE NOT NULL,  -- SHA-256 hash for enrichment association
    title VARCHAR(500) NOT NULL,
    description TEXT,
    start_year INTEGER,
    end_year INTEGER,
    -- ... other fields
);
```

**event_enrichments** (second-order data)
```sql
CREATE TABLE event_enrichments (
    event_key TEXT PRIMARY KEY REFERENCES historical_events(event_key) ON DELETE CASCADE,
    interest_count INTEGER DEFAULT 0,
    last_enriched_at TIMESTAMPTZ DEFAULT NOW()
);
```

**event_categories** (second-order data, supports multiple categories)
```sql
CREATE TABLE event_categories (
    event_key TEXT REFERENCES historical_events(event_key) ON DELETE CASCADE,
    category TEXT NOT NULL,
    PRIMARY KEY (event_key, category)
);
```

## Key Features

### 1. Persistence Across Reimports

When Wikipedia data is reimported:
- Each event gets the same `event_key` if content is unchanged
- Enrichments remain associated via `event_key`
- No manual reconciliation needed

### 2. Automatic Orphan Cleanup

The `ON DELETE CASCADE` constraint ensures that when an event is deleted, its enrichments are automatically removed. Additionally, a pruning script can be run periodically:

```bash
python scripts/prune_orphaned_enrichments.py --dry-run
```

### 3. Expected Orphaning

If Wikipedia content changes (even slightly), the event gets a new `event_key`. This causes expected orphaning of old enrichments, which is correct behavior - the event has changed.

## File Structure

```
Timeline/
├── api/
│   ├── event_key.py                    # Event key computation (API copy)
│   └── api.py                          # API endpoints (to be updated for enrichments)
├── wikipedia-ingestion/
│   ├── event_key.py                    # Event key computation (ingestion copy)
│   ├── ingestion_common.py             # Updated to compute event_key
│   └── tests/
│       └── test_event_key.py           # Unit tests for event_key
├── database/
│   └── init.sql                        # Schema with enrichment tables
└── scripts/
    └── prune_orphaned_enrichments.py   # Cleanup script
```

## Usage

### During Ingestion

The ingestion pipeline automatically computes and stores `event_key`:

```python
# In ingestion_common.py
from event_key import compute_event_key

event_key = compute_event_key(
    title=event["title"],
    start_year=event.get("start_year") or 0,
    end_year=event.get("end_year") or 0,
    description=event.get("description")
)

# Insert with event_key
cursor.execute("""
    INSERT INTO historical_events 
        (event_key, title, description, ...)
    VALUES (%s, %s, %s, ...)
""", (event_key, ...))
```

### Adding Enrichments

```python
from event_key import compute_event_key_from_dict

# Get event from database
event = get_event_by_id(event_id)

# Compute its key
key = compute_event_key_from_dict(event)

# Add enrichment
cursor.execute("""
    INSERT INTO event_enrichments (event_key, interest_count)
    VALUES (%s, %s)
    ON CONFLICT (event_key) 
    DO UPDATE SET interest_count = event_enrichments.interest_count + 1
""", (key, 1))

# Add category
cursor.execute("""
    INSERT INTO event_categories (event_key, category)
    VALUES (%s, %s)
    ON CONFLICT DO NOTHING
""", (key, "War & Conflict"))
```

### Periodic Cleanup

```bash
# Check for orphaned enrichments
python scripts/prune_orphaned_enrichments.py --verbose --dry-run

# Prune orphaned enrichments
python scripts/prune_orphaned_enrichments.py
```

## Testing

Unit tests ensure event_key computation is:
- Deterministic (same input → same output)
- Unique (different events → different keys)
- Stable (handles edge cases consistently)

```bash
pytest wikipedia-ingestion/tests/test_event_key.py -v
```

## Next Steps

1. **Reset and reimport database** with new schema
2. **Update API endpoints** to join and return enrichment data
3. **Integrate LLM categorization** to populate event_categories
4. **Add user interest tracking** to populate event_enrichments
5. **Schedule periodic pruning** (e.g., daily cron job)

## Benefits

✅ **Separation of concerns**: Raw and enriched data are decoupled  
✅ **Persistence**: Enrichments survive reimports  
✅ **Maintainability**: Clear, testable, modular code  
✅ **Extensibility**: Easy to add new enrichment types  
✅ **Automatic cleanup**: Orphaned data is identified and removed  
✅ **SOLID principles**: Single responsibility, dependency inversion  
✅ **Microservices-ready**: Clean boundaries between services
