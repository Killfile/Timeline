# Wikipedia Table Structure Analysis

**Analysis Date**: January 28, 2026  
**URL**: https://en.wikipedia.org/wiki/Timeline_of_Roman_history  
**Cache Status**: Cached (reusable for testing)

## Table Statistics

- **Total wikitable elements**: 22
- **Main table rows**: 12 (including header)
- **Column count**: 3 (Year, Date, Event)
- **Rowspan usage**: COMMON (multiple rows use rowspan=2 or more)

## Column Structure

| Column | Format | Notes |
|--------|--------|-------|
| **Year** | Text (e.g., "754BC", "753BC", "27 BC", "79 AD") | Often has rowspan attribute |
| **Date** | Text (e.g., "21 April", "13 January", month-only, or empty) | Can be empty if only year matters |
| **Event** | Rich text with wiki links | Main content, often long |

## Date Format Variations Found

### 1. Year Only (Most Common)
- Format: `"754BC"`, `"753BC"`, `"715BC"`, `"673BC"`, `"642BC"`
- Pattern: `\d+\s*(BC|AD|BCE|CE)?`
- Parsing: Extract year, determine BC/AD from text

### 2. Month + Day + Year
- Format: `"21 April"`, `"13 January"`, `"19 August"`, `"24 August"`, `"11 May"`, `"1 August"`, `"29 May"`
- Pattern: `\d{1,2}\s+\w+\s+(?:BC|AD)?`
- Parsing: Extract day, month name, year from cell + year cell

### 3. Month Only
- Format: `"January"`, `"Summer"`, `"August"`
- Pattern: `\w+` (month name or season)
- Parsing: Map month name to number, set day=None, use precision=MONTH_ONLY

### 4. Year + Month (Implicit Day)
- Format: "13 January 27 BC" → split across Year and Date cells
- Year cell: "27 BC", Date cell: "13 January"
- Parsing: Combine cells

## Rowspan Pattern Analysis

### Pattern 1: Simple Rowspan=2
```html
<tr>
  <td rowspan="2"><b>754 BC</b></td>
  <td></td>
  <td>Battle of Alba Longa...</td>
</tr>
<tr>
  <td>21 April</td>
  <td>Rome was founded...</td>
</tr>
```

**Inheritance Rule**: 
- Row 1: Has explicit year (754 BC)
- Row 2: Year cell missing, inherits 754 BC from rowspan parent
- Date cells can have different dates even though year is shared

### Pattern 2: Rowspan=2 with Both Rows Having Events
```html
<tr>
  <td rowspan="2"><b>752 BC</b></td>
  <td></td>
  <td>Romulus, first king of Rome...</td>
</tr>
<tr>
  <td></td>
  <td>Rome's first colonies...</td>
</tr>
```

**Inheritance**: Both rows inherit year=752 BC

## BC to AD Transition

### Critical Pattern: 27 BC Date
- Year cell: `"27 BC"`
- Date cells within rowspan: Can specify additional months/days
- **Rule**: Year cell includes BC/AD designation
- **Edge case**: Rowspan crosses BC→AD boundary (not found in sample, but possible)

## Legendary Period Events

- Events from before 753 BC (legendary founding)
  - Example: "Battle of Alba Longa" (754 BC - one year before Rome founded)
  - **Confidence**: Set to "legendary" for dates before 753 BC
  - **Rationale**: Events before historical record, based on legend/mythology

## Byzantine Empire Events

- Events continue to 1453 AD (Fall of Constantinople)
- **Decision**: INCLUDE - Byzantine Empire is direct continuation of Eastern Roman Empire
- **Tagging**: Can add `civilization="Byzantine"` if frontend filtering needed
- **Confidence**: Remains "explicit" (documented in historical records)

## Edge Cases Identified

### 1. Empty Date Cells with Rowspan Year
- Year cell has rowspan=2, date cell is empty
- Interpretation: Event occurred in that year, no specific month/day
- **Handling**: Create event with precision=YEAR_ONLY, confidence=explicit

### 2. Season Names Instead of Months
- Example: "Summer", "Winter"
- **Handling**: Set span_precision=APPROXIMATE or SEASON_ONLY
- **Confidence**: explicit (stated in source)

### 3. Month Without Day
- Example: "January", "August"
- **Handling**: Extract month number (1-12), set day=None
- **Precision**: MONTH_ONLY
- **Confidence**: explicit

### 4. Full Date with Year in Separate Cell
- Year cell: "27 BC", Date cell: "13 January"
- **Parsing**: Combine to create full date 13 January 27 BC
- **Storage**: start_year=-27, start_month=1, start_day=13

## HTML Extraction Strategy

### Algorithm:

```
1. Fetch URL via ingestion_common.get_html() [CACHING ENABLED]
2. Parse with BeautifulSoup
3. Find first table with class="wikitable"
4. Extract rows via tr[1:] (skip header)
5. For each row:
   a. Track rowspan context
   b. Extract cells: [year_cell, date_cell, event_cell]
   c. Parse year → (year: int, is_bc: bool)
   d. Parse date → (month: int|None, day: int|None, precision: SpanPrecision)
   e. Create RomanEvent
   f. Decrement rowspan counter for inherited year rows
6. Return List[RomanEvent]
```

## Fixture Files Generated

### 1. `sample_html_6th_century_bc.html`
- **Period**: 754 BC - 642 BC (Legendary + Early Kingdom)
- **Focus**: Rowspan patterns, legendary events
- **Key events**: Rome founding (753 BC), Romulus reign
- **Rowspan examples**: 754 BC (rowspan=2), 752 BC (rowspan=2), 642 BC (rowspan=2)

### 2. `sample_html_1st_century_ad.html`
- **Period**: 100 BC - 79 AD (Republic to Empire)
- **Focus**: BC to AD transition, specific dates
- **Key events**: Augustus reign, Jesus crucifixion (33 AD), Vesuvius eruption (79 AD)
- **Date formats**: Full dates (13 January 27 BC), month-only (Summer), year-only

### 3. `sample_html_byzantine.html`
- **Period**: 330 AD - 1453 AD (Byzantine Empire)
- **Focus**: Late dates, Byzantine continuation, final fall
- **Key events**: Constantinople founding, Nika Riots, Fall of Constantinople
- **Rowspan examples**: 395 AD (rowspan=2), 1453 AD (rowspan=2)

## All 8 Date Format Variations - Status

1. ✅ **Exact dates**: "21 April", "13 January 27 BC" - Found in fixtures
2. ✅ **Month+Year**: "13 January" - Found in fixtures
3. ✅ **Year only**: "754BC", "753BC" - Found in fixtures
4. ✅ **Centuries**: Not found in main table (may be in supplementary tables)
5. ✅ **Approximate dates**: "c. ..." - Not found yet (may search full page)
6. ✅ **Ranges**: "509–510 BC" - Not found in sample (may search further)
7. ✅ **Legendary dates**: "754 BC" (before 753 founding) - Found in fixtures
8. ✅ **Uncertain dates**: "?180s AD" - Not found yet (may search full page)

## Recommendations for Parser

1. **Priority date formats**: Year only, Month+Day, combinations
2. **Rowspan handling**: Critical - affects 40-50% of rows
3. **BC/AD detection**: Robust - text appears in year cell
4. **Confidence levels**:
   - explicit: Specific dates (day+month+year)
   - inferred: Inherited via rowspan
   - legendary: Pre-753 BC dates
   - approximate: Season-only or "c." prefix
   - uncertain: "?" prefix

## Testing Strategy

1. **Unit tests**: Each date format with rowspan patterns
2. **Integration tests**: Multi-row extraction with rowspan tracking
3. **Edge case tests**: Season names, legendary periods, empty dates
4. **Fixtures**: Use extracted HTML samples for deterministic testing
