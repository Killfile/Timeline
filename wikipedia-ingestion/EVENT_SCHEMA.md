# Event Schema Documentation

## Overview

All ingestion strategies MUST produce events conforming to the **canonical event schema** defined in `event_schema.py`. This ensures consistency across all data sources and simplifies database loading and validation.

## Canonical Schema

The canonical schema uses a **flat structure** with all date fields at the top level (NOT nested in a `span` object).

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | `str` | Event title/summary (max 500 chars, truncate with "..." if needed) |
| `description` | `str` | Full event description (max 500 chars) |
| `url` | `str` | Source Wikipedia URL |
| `start_year` | `int` | Start year (positive integer, era indicated by `is_bc_start`) |
| `end_year` | `int` | End year (positive integer, era indicated by `is_bc_end`) |
| `is_bc_start` | `bool` | `True` if start year is BC/BCE |
| `is_bc_end` | `bool` | `True` if end year is BC/BCE |
| `weight` | `int` | Event duration in days (used for packing priority) |
| `precision` | `float` | Date precision value (represents uncertainty, NOT a scaling factor) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `start_month` | `int \| None` | Start month (1-12), or `None` for year-only precision |
| `start_day` | `int \| None` | Start day (1-31), or `None` |
| `end_month` | `int \| None` | End month (1-12), or `None` |
| `end_day` | `int \| None` | End day (1-31), or `None` |
| `category` | `str \| None` | Event category/tag from extraction |
| `pageid` | `int \| None` | Wikipedia page ID (for deduplication) |

### Debug/Internal Fields

Fields prefixed with `_` are for debugging and internal use only:

| Field | Type | Description |
|-------|------|-------------|
| `_debug_extraction` | `dict \| None` | Debug metadata from extraction process |

## Example Event (Canonical Format)

```json
{
  "title": "Industrial Age",
  "description": "Period of industrialization and mechanization",
  "url": "https://en.wikipedia.org/wiki/Industrial_Age",
  "start_year": 1760,
  "end_year": 1970,
  "start_month": null,
  "start_day": null,
  "end_month": null,
  "end_day": null,
  "is_bc_start": false,
  "is_bc_end": false,
  "weight": 76650,
  "precision": 365.0,
  "category": "Technological periods",
  "pageid": null,
  "_debug_extraction": {
    "method": "list_of_time_periods",
    "original_date_str": "1760-1970"
  }
}
```

## Non-Canonical Format (DO NOT USE)

The following format with a nested `span` object is **NOT canonical** and will be rejected:

```json
{
  "title": "Industrial Age",
  "description": "Period of industrialization",
  "url": "https://en.wikipedia.org/wiki/Industrial_Age",
  "span": {
    "start_year": 1760,
    "end_year": 1970,
    "start_year_is_bc": false,
    "end_year_is_bc": false,
    "weight": 76650,
    "precision": 365.0
  },
  "category": "Technological periods"
}
```

**Why this is wrong:**
- Date fields must be at top level, not nested in `span`
- Field naming must match canonical schema (`is_bc_start` not `start_year_is_bc`)

## Using CanonicalEvent in Code

### Method 1: Direct Construction

```python
from event_schema import CanonicalEvent

event = CanonicalEvent(
    title="Battle of Hastings",
    description="Norman conquest of England",
    url="https://en.wikipedia.org/wiki/Battle_of_Hastings",
    start_year=1066,
    end_year=1066,
    start_month=10,
    start_day=14,
    end_month=10,
    end_day=14,
    is_bc_start=False,
    is_bc_end=False,
    weight=1,
    precision=1.0,
    category="Medieval battles",
    pageid=4775,
)

# Convert to dict for JSON serialization
event_dict = event.to_dict()
```

### Method 2: From Span Dictionary

If your parser produces span dictionaries (like the span parsing framework), use the `from_span_dict` helper:

```python
from event_schema import CanonicalEvent

# Span dict from parser (may have nested structure)
span_dict = {
    "start_year": 1066,
    "end_year": 1066,
    "start_month": 10,
    "start_day": 14,
    "end_month": 10,
    "end_day": 14,
    "start_year_is_bc": False,
    "end_year_is_bc": False,
    "weight": 1,
    "precision": 1.0,
}

# Create canonical event (automatically flattens)
event = CanonicalEvent.from_span_dict(
    title="Battle of Hastings",
    description="Norman conquest of England",
    url="https://en.wikipedia.org/wiki/Battle_of_Hastings",
    span_dict=span_dict,
    category="Medieval battles",
    pageid=4775,
)

event_dict = event.to_dict()
```

## Validation

### Validate Before Database Load

Use `validate_canonical_event` for lightweight validation:

```python
from event_schema import validate_canonical_event

is_valid, error = validate_canonical_event(event_dict)
if not is_valid:
    print(f"Invalid event: {error}")
```

### Comprehensive Validation

For full type checking and field validation, use `validate_event_dict` from `strategy_base`:

```python
from strategy_base import validate_event_dict

is_valid, error = validate_event_dict(event_dict)
if not is_valid:
    print(f"Validation failed: {error}")
```

## Date Handling Guidelines

### BC/AD Years

- Use positive integers for year values
- Set `is_bc_start` and `is_bc_end` to indicate era
- Examples:
  - 753 BC → `start_year=753`, `is_bc_start=True`
  - 476 AD → `start_year=476`, `is_bc_start=False`
  - BC to AD span: 100 BC - 100 AD → `start_year=100`, `is_bc_start=True`, `end_year=100`, `is_bc_end=False`

### Weight Computation

- `weight` represents event **duration in days**
- Used for packing priority (longer events = higher weight)
- DO NOT scale weight by precision (precision represents uncertainty, not duration)
- Examples:
  - Single day: `weight=1`
  - One year (365 days): `weight=365`
  - 10 years (3650 days): `weight=3650`

### Precision Values

Precision represents date **uncertainty**, not duration scaling:

| Precision | Meaning | Example |
|-----------|---------|---------|
| `1.0` | Day-level precision | "October 14, 1066" |
| `30.0` | Month-level precision | "October 1066" |
| `365.0` | Year-level precision | "1066" |
| `3650.0` | Decade-level precision | "1060s" |
| `36500.0` | Century-level precision | "11th century" |

**Important:** Precision is a constant from `SpanPrecision` class, not a multiplier for weight.

## Implementation Checklist

When creating or updating an ingestion strategy:

- [ ] Use `CanonicalEvent` class or `from_span_dict` helper
- [ ] Flatten all date fields to top level (no nested `span` object)
- [ ] Use correct field names (`is_bc_start`, not `start_year_is_bc`)
- [ ] Truncate `title` and `description` to 500 chars if needed
- [ ] Compute `weight` as duration in days (don't scale by precision)
- [ ] Set `precision` from `SpanPrecision` constants
- [ ] Include `_debug_extraction` for troubleshooting
- [ ] Call `event.to_dict()` before adding to events list
- [ ] Validate with `validate_canonical_event` before writing artifacts

## Current Strategy Status

| Strategy | Status | Notes |
|----------|--------|-------|
| `list_of_years` | ✅ Canonical | Already uses flat schema |
| `list_of_time_periods` | ✅ Canonical | Updated to use `CanonicalEvent.from_span_dict` |
| `bespoke_events` | ✅ Canonical | Uses flat schema |

## Artifact File Naming Convention

All strategies MUST generate artifact files using this naming pattern:

```
events_{strategy_name}_{run_id}.json
```

Examples:
- `events_list_of_years_20260110T183707Z.json`
- `events_list_of_time_periods_20260110T184955Z.json`
- `events_bespoke_events_20260110T183707Z.json`

**Why this matters:**
- The `events_` prefix clearly identifies event artifacts vs. other JSON files (load_report, load_errors, exclusions)
- Consistent naming makes pattern matching in database_loader reliable
- The `{strategy_name}_{run_id}` format prevents collisions and aids debugging

## Artifact Structure Requirements

All artifact files must have these top-level fields:

```json
{
  "strategy": "strategy_name",
  "run_id": "20260110T183707Z",
  "event_count": 123,
  "generated_at": "2026-01-10T18:37:07.123456",
  "metadata": { ... },
  "events": [ ... ]
}
```

**Required top-level fields:**
- `strategy` - Name of the ingestion strategy
- `run_id` - Timestamp-based run identifier
- `event_count` - Number of events in the artifact
- `events` - Array of event objects (each using canonical schema)

**Optional top-level fields:**
- `generated_at` - ISO timestamp of artifact generation
- `metadata` - Strategy-specific metadata

## Migration Notes

If you have old artifact files with nested `span` objects:

1. They will fail validation in `database_loader.py`
2. Re-run the ingestion strategy to generate new artifacts
3. Old artifacts will be replaced with canonical format

## Testing

Run tests to verify schema compliance:

```bash
cd wikipedia-ingestion
python -m pytest test_event_schema.py -v
```

Tests cover:
- Basic event construction
- `from_span_dict` helper
- Validation of canonical format
- Detection of non-canonical formats (nested `span`)
- BC year handling
- Optional field handling
