# Table Date Extraction Validation Checklist

**Purpose**: Verify that table row dates are correctly extracted from first column and used for event dating

**Status**: In Progress (Tasks T025b, T025c)

## Expected Behavior

Table events should use the date from the **first column** of the table row for event dating, not fall back to the description parser.

Current behavior: All table events are using "Fallback parser using page context"
Expected behavior: Events should have explicit or approximate dates extracted from table's first column

## Test Cases

### Case 1: Year Range to Century
- [ ] **Description**: "New potato varieties are brought from Chile to Europe, in an attempt..."
- [ ] **Table column 1**: "1800-1899" or similar
- [ ] **Expected start_year**: 1800
- [ ] **Expected end_year**: 1899
- [ ] **Expected span_match_notes**: Should indicate year range or century parse
- [ ] **Current result**: start_year=1801, end_year=1801, span_match_notes="Fallback parser using page context"
- [ ] **Status**: ❌ FAILING

### Case 2: Specific Year
- [ ] **Description**: "One of America's first candy-making machines invented in Boston by..."
- [ ] **Table column 1**: "1847" or similar format
- [ ] **Expected start_year**: 1847
- [ ] **Expected end_year**: 1847
- [ ] **Expected span_match_notes**: Should indicate explicit year match
- [ ] **Current result**: start_year=1801, end_year=1801, span_match_notes="Fallback parser using page context"
- [ ] **Status**: ❌ FAILING

### Case 3: Decade Range
- [ ] **Description**: "Goldschläger, a gold-infused cinnamon schnapps based on goldwasser..."
- [ ] **Table column 1**: "1990s" or "1990-1999" or similar
- [ ] **Expected start_year**: 1990 (or decade range)
- [ ] **Expected end_year**: 1999 (or decade range)
- [ ] **Expected span_match_notes**: Should indicate decade or range parse
- [ ] **Current result**: start_year=1901, end_year=1901, span_match_notes="Fallback parser using page context"
- [ ] **Status**: ❌ FAILING

## Implementation Requirements

For T025b, the `_extract_events_from_table()` method must:

- [ ] Extract the date/year text from table's first column (`cells[0]`)
- [ ] Parse the extracted date using FoodTimelineParseOrchestrator
- [ ] Combine the parsed date with the description from second column
- [ ] Pass both to EventParser with the extracted date as primary
- [ ] Avoid falling back to page context when table column has parseable date
- [ ] Handle edge cases:
  - [ ] Empty date columns
  - [ ] Non-standard date formats in first column
  - [ ] Multi-row table headers
  - [ ] Merged cells across columns

## Testing Requirements (T025c)

- [ ] Unit test: Simple year extraction from table column
- [ ] Unit test: Year range extraction (e.g., "1800-1899")
- [ ] Unit test: Century notation (e.g., "19th century")
- [ ] Unit test: Decade notation (e.g., "1990s")
- [ ] Unit test: Complex date formats with description continuation
- [ ] Unit test: Missing/empty date column falls back gracefully
- [ ] Integration test: Verify Case 1 produces correct dates
- [ ] Integration test: Verify Case 2 produces correct dates
- [ ] Integration test: Verify Case 3 produces correct dates

## Completion Criteria

- [x] Tasks T025b and T025c added to task list
- [ ] Implementation complete: Table dates parsed from first column
- [ ] Unit tests written and passing
- [ ] All three test cases (Case 1, 2, 3) produce expected results
- [ ] Integration test passes with 3,000+ events and correct date ranges
- [ ] span_match_notes no longer shows "Fallback parser" for table events
