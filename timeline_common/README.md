# timeline_common

Shared utilities module for the Timeline project, resolving circular dependencies between `api/` and `wikipedia-ingestion/` services.

## Purpose

The `timeline_common` module contains functionality that needs to be accessed by multiple services without creating circular import dependencies. Currently, it provides event key computation for deterministic event deduplication across reimports.

## Architecture

```
timeline_common/
├── __init__.py              # Module initialization, public API exports
├── event_key.py             # SHA-256 event key computation
└── tests/
    ├── __init__.py          # Pytest discovery marker
    └── test_event_key.py    # Unit tests (32 tests, 100% coverage)
```

## Modules

### event_key.py

Provides deterministic SHA-256 event key computation for associating enrichment data with historical events across reimports.

**Public Functions**:

#### `compute_event_key(title: str, start_year: int, end_year: int, description: Optional[str] = None) -> str`

Compute a deterministic SHA-256 event key from event fields.

**Arguments**:
- `title` (str): Event title. Must not be empty or whitespace-only. Required.
- `start_year` (int): Event start year. BC dates are negative (e.g., -753 for 753 BC).
- `end_year` (int): Event end year. BC dates are negative.
- `description` (str, optional): Event description. Defaults to empty string.

**Returns**: 64-character hexadecimal SHA-256 hash string.

**Raises**: `ValueError` if title is empty, None, or whitespace-only.

**Example**:
```python
from timeline_common.event_key import compute_event_key

key = compute_event_key(
    title="Rome Founded",
    start_year=-753,
    end_year=-753,
    description="Founding of Rome by Romulus"
)
# Returns: "abc123def456789..." (64-char hex string)
```

**Algorithm**: Computes SHA-256 hash of payload: `{title}|{start_year}|{end_year}|{description}`

---

#### `compute_event_key_from_dict(event: dict) -> str`

Convenience wrapper for computing event keys from event dictionaries.

**Arguments**:
- `event` (dict): Dictionary with keys: `title`, `start_year`, `end_year`, [optional `description`]

**Returns**: 64-character hexadecimal SHA-256 hash string.

**Raises**: 
- `KeyError` if required keys (`title`, `start_year`, `end_year`) are missing
- `ValueError` if title is empty

**Example**:
```python
from timeline_common.event_key import compute_event_key_from_dict

event = {
    'title': 'Battle of Hastings',
    'start_year': 1066,
    'end_year': 1066,
    'description': 'Norman conquest of England'
}
key = compute_event_key_from_dict(event)
```

---

#### `validate_event_key(key: str) -> bool`

Validate that a string is a valid event key format (64-character hexadecimal).

**Arguments**:
- `key` (str): String to validate

**Returns**: `True` if valid SHA-256 hex format, `False` otherwise.

**Note**: Returns `False` for non-string types, empty strings, wrong lengths, or non-hex characters.

**Example**:
```python
from timeline_common.event_key import validate_event_key

key = compute_event_key("Test", 1066, 1066, "test")
assert validate_event_key(key) == True  # 64-char hex
assert validate_event_key("invalid") == False  # Not hex
assert validate_event_key("a" * 63) == False  # Wrong length
```

## Usage

### From api/

```python
# Backward compatibility - can still import from api.event_key
from api.event_key import compute_event_key

key = compute_event_key("Battle", 1066, 1066, "Norman victory")
```

### From wikipedia-ingestion/

```python
# New pattern - import directly from timeline_common
from timeline_common.event_key import compute_event_key

key = compute_event_key("Battle", 1066, 1066, "Norman victory")
```

### Direct Import (Recommended)

```python
# Direct import (most explicit)
from timeline_common.event_key import (
    compute_event_key,
    compute_event_key_from_dict,
    validate_event_key
)
```

## Testing

### Running Tests

```bash
# Run all timeline_common tests
pytest timeline_common/tests/test_event_key.py -v

# Run with coverage
pytest timeline_common/tests/test_event_key.py --cov=timeline_common.event_key --cov-report=term-missing

# Run specific test class
pytest timeline_common/tests/test_event_key.py::TestComputeEventKey -v
```

### Test Coverage

- **Test Count**: 32 unit tests
- **Coverage**: 100% (21/21 statements)
- **Test Classes**:
  - `TestComputeEventKey` (13 tests): Core function behavior, edge cases
  - `TestComputeEventKeyFromDict` (6 tests): Dictionary wrapper behavior
  - `TestValidateEventKey` (10 tests): Format validation
  - `TestEventKeyIntegration` (2 tests): Integration scenarios

### Test Examples

```python
# Idempotency - same input always produces same output
key1 = compute_event_key("Battle", 1066, 1066, "test")
key2 = compute_event_key("Battle", 1066, 1066, "test")
assert key1 == key2

# Sensitivity - different inputs produce different keys
key1 = compute_event_key("Battle A", 1066, 1066, "")
key2 = compute_event_key("Battle B", 1066, 1066, "")
assert key1 != key2

# BC dates work correctly
key = compute_event_key("Rome", -753, -753, "753 BC")
assert validate_event_key(key)

# Empty title raises error
with pytest.raises(ValueError):
    compute_event_key("", 1066, 1066, "")
```

## Design Decisions

### Deterministic Hashing (SHA-256)

- **Why SHA-256?**: Widely available, cryptographically secure, deterministic
- **Payload**: Includes title, years, and description to capture event identity
- **Idempotency**: Same event fields always produce same key across runs and reimports
- **Deduplication**: Enables enrichment data (categories, images) to survive reimports

### BC Date Representation

- **Storage**: BC years stored as negative integers
- **Example**: 753 BC → -753, 1 AD → 1
- **Chronological ordering**: Negative years sort correctly (-200 < -100 < 1 < 100)

### Whitespace Normalization

- Title and description are trimmed of leading/trailing whitespace
- Empty descriptions treated same as None
- Improves deduplication robustness

## Module Dependencies

- Standard library: `hashlib` (SHA-256)
- No external dependencies

## Integration with Other Modules

### api/event_key.py
- Acts as backward compatibility wrapper
- Re-exports all functions from `timeline_common.event_key`
- Allows existing code to continue using `from api.event_key import ...`

### wikipedia-ingestion/database_ingestion.py
- Imports from `timeline_common.event_key` directly
- Uses event keys to associate enrichments with events

### Future Modules
- `timeline_of_roman_history_strategy` will use `compute_event_key()` for RomanEvent deduplication
- Other ingestion strategies can reuse without circular dependencies

## Contributing

When adding new shared utilities:

1. **Check for duplication**: Ensure functionality doesn't exist elsewhere
2. **Evaluate scope**: Is this truly shared between services?
3. **Consider alternatives**: Could circular dependencies be resolved differently?
4. **Add tests**: Minimum 95% code coverage required
5. **Document**: Include docstrings and README updates
6. **Version compatibility**: Test with all services that import this module

## Related Documentation

- [api/event_key.py](../api/event_key.py) - Backward compatibility wrapper
- [wikipedia-ingestion/database_ingestion.py](../wikipedia-ingestion/database_ingestion.py) - Database insertion using event keys
- [Specification](../specs/001-timeline-of-roman-history/spec.md) - Roman History timeline requirements
