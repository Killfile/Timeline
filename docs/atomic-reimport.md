# Atomic Reimport Guide

## Overview

The atomic reimport feature allows you to reimport Wikipedia data while preserving all enrichment data (categories, interest counts, etc.). This is accomplished by:

1. **Creating a temporary table** (`historical_events_temp`)
2. **Importing data** into the temp table
3. **Atomically swapping** tables (near-zero downtime)
4. **Preserving enrichments** via deterministic `event_key` references

## Why Use Atomic Reimport?

### Problem
When you need to refresh Wikipedia data, you don't want to lose:
- User-assigned categories
- AI-generated categorizations
- Interest counts / engagement metrics
- Manual edits or notes

### Solution
Atomic reimport uses the `event_key` system to maintain referential integrity between:
- **First-order data**: `historical_events` (raw Wikipedia content)
- **Second-order data**: `event_enrichments`, `event_categories` (derived/enriched data)

Because `event_key` is a deterministic SHA-256 hash of the event's core content (title + dates + description), the same event will have the same key across reimports.

## Usage

### Basic Reimport (Full Range)

```bash
./scripts/atomic-reimport
```

This reimports the full configured range from your `.env` file.

### Partial Reimport (Specific Range)

```bash
./scripts/atomic-reimport "1000 BC" "2026 AD"
```

This reimports only events within the specified date range.

## How It Works

### Step 1: Create Temporary Table

```sql
CREATE TABLE historical_events_temp (
    LIKE historical_events INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
);
```

This creates an exact copy of the `historical_events` schema.

### Step 2: Import Data

The ingestion pipeline runs normally, but inserts into `historical_events_temp` instead of `historical_events`. This is controlled by the `INGEST_TARGET_TABLE` environment variable.

### Step 3: Atomic Swap

```sql
BEGIN;

-- Drop foreign key constraints temporarily
ALTER TABLE event_enrichments DROP CONSTRAINT event_enrichments_event_key_fkey;
ALTER TABLE event_categories DROP CONSTRAINT event_categories_event_key_fkey;

-- Rename tables
ALTER TABLE historical_events RENAME TO historical_events_old;
ALTER TABLE historical_events_temp RENAME TO historical_events;

-- Recreate foreign key constraints
ALTER TABLE event_enrichments 
  ADD CONSTRAINT event_enrichments_event_key_fkey
  FOREIGN KEY (event_key) REFERENCES historical_events(event_key) ON DELETE CASCADE;

ALTER TABLE event_categories
  ADD CONSTRAINT event_categories_event_key_fkey
  FOREIGN KEY (event_key) REFERENCES historical_events(event_key) ON DELETE CASCADE;

-- Drop old table
DROP TABLE historical_events_old CASCADE;

COMMIT;
```

This entire operation is atomic - either it all succeeds or all rolls back.

### Step 4: Automatic Orphan Cleanup

When the foreign key constraints are recreated with `ON DELETE CASCADE`, any enrichments whose `event_key` no longer exists in the new data are automatically removed. This happens for:

- **Deleted events**: Events that existed in old data but not new data
- **Modified events**: Events whose title/dates/description changed (resulting in a new event_key)

## What Gets Preserved?

✅ **Preserved** (if event content unchanged):
- Categories assigned via LLM or manually
- Interest counts from user engagement
- Last enrichment timestamp
- Any custom enrichment data

❌ **Not Preserved** (orphaned):
- Enrichments for events no longer in Wikipedia
- Enrichments for events whose core content changed significantly

## Verification

After running atomic reimport, verify the results:

```bash
# Check event count
docker-compose exec database psql -U timeline_user -d timeline_history \
  -c "SELECT COUNT(*) FROM historical_events;"

# Check enrichment preservation
docker-compose exec database psql -U timeline_user -d timeline_history \
  -c "SELECT 
        (SELECT COUNT(*) FROM event_enrichments) as enrichments,
        (SELECT COUNT(*) FROM event_categories) as categories,
        (SELECT COUNT(*) FROM historical_events) as events;"

# Sample enriched events
docker-compose exec database psql -U timeline_user -d timeline_history \
  -c "SELECT he.title, he.start_year, ee.interest_count, 
       STRING_AGG(ec.category, ', ') as categories
      FROM historical_events he
      LEFT JOIN event_enrichments ee ON he.event_key = ee.event_key
      LEFT JOIN event_categories ec ON he.event_key = ec.event_key
      WHERE ee.event_key IS NOT NULL
      GROUP BY he.title, he.start_year, ee.interest_count
      LIMIT 10;"
```

## Comparison with Standard Reimport

### Standard Reimport (`./scripts/reset-and-reimport`)
- ✅ Simple and fast
- ❌ Loses ALL enrichment data
- ❌ Requires volume recreation (slower)
- Use when: You want a clean slate

### Atomic Reimport (`./scripts/atomic-reimport`)
- ✅ Preserves enrichments via event_key
- ✅ Minimal downtime (< 1 second)
- ✅ Rollback on failure
- ✅ Automatic orphan cleanup
- Use when: You want to refresh data while keeping enrichments

## Troubleshooting

### Import Failed Mid-Process

The atomic swap only happens if import succeeds. If import fails:
1. The temp table is dropped automatically
2. Production table remains unchanged
3. Check logs for the error
4. Fix the issue and retry

### Enrichments Missing After Reimport

This is expected if the event's core content changed:
- Different title → different event_key
- Different dates → different event_key
- Different description → different event_key

To verify, compute the old and new event_keys:

```python
from event_key import compute_event_key

old_key = compute_event_key("Old Title", 2020, 2020, "Old description")
new_key = compute_event_key("New Title", 2020, 2020, "Old description")
# These will be different!
```

### Want to Keep Old Data for Comparison?

Before running atomic reimport, backup the enrichments:

```bash
docker-compose exec database pg_dump -U timeline_user \
  -t event_enrichments -t event_categories timeline_history \
  > enrichments_backup.sql
```

## Advanced: Manual Orphan Pruning

The atomic swap handles orphan cleanup automatically, but you can also manually prune orphans:

```bash
docker-compose run --rm wikipedia-ingestion \
  python scripts/prune_orphaned_enrichments.py --verbose

# Dry run first
docker-compose run --rm wikipedia-ingestion \
  python scripts/prune_orphaned_enrichments.py --dry-run --verbose
```

## See Also

- [Enrichment Architecture Documentation](enrichment-architecture.md)
- [Event Key System](enrichment-architecture.md#event-key-system)
- [Database Schema](../database/init.sql)
