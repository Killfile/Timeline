# Table Date Extraction - User Story 2 Validation Checklist

**Purpose**: Verify that table row dates with decade notation and BC/BCE ranges work correctly after User Story 2 implementation

**Status**: Complete (T027a, T032/T032a, T033 implemented and validated; all test cases passing)

**Note**: These test cases depend on User Story 2 features:
- T027a: BC/BCE range notation fix in YearRangeParser
- T032/T032a: DecadeParser implementation
- T033: Logging updates for decade-parsed dates

## Test Cases from User Story 1 Validation

### Case 1: Decade Notation "1800s" (Depends on T032/T032a)
- [X] **Description**: "New potato varieties are brought from Chile to Europe, in an attempt..."
- [X] **Table column 1**: "1800s"
- [X] **Expected start_year**: 1800
- [X] **Expected end_year**: 1809
- [X] **Expected span_match_notes**: Should indicate DecadeParser match
- [X] **Expected parsing_notes**: Should note decade notation interpretation
- [X] **Status**: ✅ PASSING

### Case 3: Decade Notation "1990s" (Depends on T032/T032a)
- [X] **Description**: "Goldschläger, a gold-infused cinnamon schnapps based on goldwasser..."
- [X] **Table column 1**: "1990s"
- [X] **Expected start_year**: 1990
- [X] **Expected end_year**: 1999
- [X] **Expected span_match_notes**: Should indicate DecadeParser match
- [X] **Expected parsing_notes**: Should note decade notation interpretation
- [X] **Status**: ✅ PASSING

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
- [X] Create DecadeParser class to match "####s" pattern
- [X] Parse "1990s" → (1990, 1999)
- [X] Parse "1800s" → (1800, 1809) per specification
- [X] Handle edge cases: 1000s, 2000s, etc.
- [X] Integrate with FoodTimelineParseOrchestrator

### For T033 (Logging Updates):
- [X] Log decade-parsed dates with specific notation
- [X] Log BC/BCE range notation with appropriate flags
- [X] Update span_match_notes to indicate parser type
- [X] Update parsing_notes with decade interpretation details

## Testing Requirements (User Story 2)

- [X] Unit tests for YearRangeParser BC/BCE handling (T027a)
- [X] Unit tests for DecadeParser all decade patterns (T032a)
- [X] Integration tests for Case 1, 3, 4, 5 producing correct dates
- [X] Verify logging output distinguishes decade vs explicit dates
- [X] Verify BC/BCE ranges have correct negative years

## Completion Criteria (User Story 2)

- [X] T027a: YearRangeParser BC/BCE bug fixed
- [X] T032/T032a: DecadeParser implemented and tested
- [X] T033: Logging updated for all new date types
- [X] All test cases 1, 3, 4, 5 passing with correct dates
- [X] Checklist items show all ✅ PASSING status
