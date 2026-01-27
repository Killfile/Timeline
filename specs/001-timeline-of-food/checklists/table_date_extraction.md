# Table Date Extraction Validation Checklist

**Purpose**: Verify that table row dates are correctly extracted from first column and used for event dating

**Status**: In Progress (Tasks T025b, T025c) - User Story 1 MVP

**Note**: Cases 1 and 3 depend on User Story 2 features (DecadeParser, BC/BCE range notation). See `table_date_extraction_us2.md` for full validation.

## Expected Behavior

Table events should use the date from the **first column** of the table row for event dating, not fall back to the description parser.

## Test Cases

### Case 2: Specific Year (User Story 1 MVP)
- [ ] **Description**: "One of America's first candy-making machines invented in Boston by..."
- [ ] **Table column 1**: "1847" or similar format
- [ ] **Expected start_year**: 1847
- [ ] **Expected end_year**: 1847
- [ ] **Expected span_match_notes**: Should indicate explicit year match
- [ ] **Current result**: PASS - Table extraction working for simple years
- [ ] **Status**: ✅ PASSING

### Case 1: Decade Notation (User Story 2 - Depends on T032/T032a)
- [ ] **Description**: "New potato varieties are brought from Chile to Europe, in an attempt..."
- [ ] **Table column 1**: "1800s" 
- [ ] **Expected start_year**: 1800
- [ ] **Expected end_year**: 1809
- [ ] **Expected span_match_notes**: Should indicate decade parse
- [ ] **Status**: ⏳ BLOCKED - Requires DecadeParser (T032, T032a)

### Case 3: Decade Notation 1990s (User Story 2 - Depends on T032/T032a)
- [ ] **Description**: "Goldschläger, a gold-infused cinnamon schnapps based on goldwasser..."
- [ ] **Table column 1**: "1990s"
- [ ] **Expected start_year**: 1990
- [ ] **Expected end_year**: 1999
- [ ] **Expected span_match_notes**: Should indicate decade parse
- [ ] **Status**: ⏳ BLOCKED - Requires DecadeParser (T032, T032a)

## Implementation Requirements (User Story 1)

For T025b, the `_extract_events_from_table()` method must:

- [x] Extract the date/year text from table's first column (`cells[0]`)
- [x] Parse the extracted date using FoodTimelineParseOrchestrator
- [x] Combine the parsed date with the description from second column
- [x] Pass both to EventParser with the extracted date as primary
- [x] Avoid falling back to page context when table column has parseable date
- [x] Handle edge cases:
  - [x] Empty date columns
  - [x] Non-standard date formats in first column
  - [x] Multi-row table headers
  - [x] Merged cells across columns

## Testing Requirements (User Story 1)

- [x] Unit test: Simple year extraction from table column
- [x] Unit test: Complex date formats with description continuation
- [x] Unit test: Missing/empty date column falls back gracefully
- [x] Integration test: Verify Case 2 (1847) produces correct dates

## Completion Criteria (User Story 1)

- [x] Tasks T025b and T025c added to task list
- [x] Implementation complete: Table dates parsed from first column
- [x] Unit tests written and passing (25+ tests)
- [x] Case 2 (1847 simple year) produces expected results
- [x] Integration test passes with 316 events extracted from tables
- [x] span_match_notes no longer shows "Fallback parser" for table events with parseable dates

## User Story 2 Validation

Cases 1 and 3 require User Story 2 features and are documented in a separate checklist:
- **table_date_extraction_us2.md**: Validation for decade notation (T032/T032a) and BC/BCE ranges (T027a)
