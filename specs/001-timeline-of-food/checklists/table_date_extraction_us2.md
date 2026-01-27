# Table Date Extraction - User Story 2 Validation Checklist

**Purpose**: Verify that table row dates with decade notation and BC/BCE ranges work correctly after User Story 2 implementation

**Status**: Pending (Tasks T027a, T032, T032a, T033)

**Note**: These test cases depend on User Story 2 features:
- T027a: BC/BCE range notation fix in YearRangeParser
- T032/T032a: DecadeParser implementation
- T033: Logging updates for decade-parsed dates

## Test Cases from User Story 1 Validation

### Case 1: Decade Notation "1800s" (Depends on T032/T032a)
- [ ] **Description**: "New potato varieties are brought from Chile to Europe, in an attempt..."
- [ ] **Table column 1**: "1800s"
- [ ] **Expected start_year**: 1800
- [ ] **Expected end_year**: 1809
- [ ] **Expected span_match_notes**: Should indicate DecadeParser match
- [ ] **Expected parsing_notes**: Should note decade notation interpretation
- [ ] **Status**: ⏳ BLOCKED - Requires DecadeParser (T032, T032a)

### Case 3: Decade Notation "1990s" (Depends on T032/T032a)
- [ ] **Description**: "Goldschläger, a gold-infused cinnamon schnapps based on goldwasser..."
- [ ] **Table column 1**: "1990s"
- [ ] **Expected start_year**: 1990
- [ ] **Expected end_year**: 1999
- [ ] **Expected span_match_notes**: Should indicate DecadeParser match
- [ ] **Expected parsing_notes**: Should note decade notation interpretation
- [ ] **Status**: ⏳ BLOCKED - Requires DecadeParser (T032, T032a)

## Additional Test Cases for User Story 2

### Case 4: BC/BCE Range Notation (Depends on T027a)
- [X] **Description**: "Time range of several sites with archaeological evidence..."
- [X] **Table column 1**: "2500–1500 BCE"
- [X] **Expected start_year**: -2500
- [X] **Expected end_year**: -1500
- [X] **Expected is_bc_start**: true
- [X] **Expected is_bc_end**: true
- [X] **Expected span_match_notes**: Should indicate YearRangeParser with BC/BCE handling
- [X] **Status**: ✅ PASSING

### Case 5: Mixed Range (Depends on T027a)
- [X] **Description**: "Archaeological evidence of early grains..."
- [X] **Table column 1**: "4000–2000 BCE"
- [X] **Expected start_year**: -4000
- [X] **Expected end_year**: -2000
- [X] **Expected span_match_notes**: Should indicate YearRangeParser match
- [X] **Status**: ✅ PASSING

## Implementation Requirements (User Story 2)

### For T027a (YearRangeParser BC/BCE Fix):
- [X] When BC/BCE marker appears on second part of range, apply to first part
- [X] Example: "2500–1500 BCE" → both years are BC
- [X] Update YearRangeParser.parse() to detect trailing BC/BCE and apply retroactively
- [X] Add test cases for all BC/BCE range combinations

### For T032/T032a (DecadeParser):
- [ ] Create DecadeParser class to match "####s" pattern
- [ ] Parse "1990s" → (1990, 1999)
- [ ] Parse "1800s" → (1800, 1809) per specification
- [ ] Handle edge cases: 1000s, 2000s, etc.
- [ ] Integrate with FoodTimelineParseOrchestrator

### For T033 (Logging Updates):
- [ ] Log decade-parsed dates with specific notation
- [ ] Log BC/BCE range notation with appropriate flags
- [ ] Update span_match_notes to indicate parser type
- [ ] Update parsing_notes with decade interpretation details

## Testing Requirements (User Story 2)

	- [X] Unit tests for YearRangeParser BC/BCE handling (T027a)
- [ ] Unit tests for DecadeParser all decade patterns (T032a)
- [ ] Integration tests for Case 1, 3, 4, 5 producing correct dates
- [ ] Verify logging output distinguishes decade vs explicit dates
- [ ] Verify BC/BCE ranges have correct negative years

## Completion Criteria (User Story 2)

- [X] T027a: YearRangeParser BC/BCE bug fixed
- [ ] T032/T032a: DecadeParser implemented and tested
- [ ] T033: Logging updated for all new date types
- [ ] All test cases 1, 3, 4, 5 passing with correct dates
- [ ] Integration test confirms 3,500+ events with proper date handling
- [ ] Checklist items show all ✅ PASSING status
