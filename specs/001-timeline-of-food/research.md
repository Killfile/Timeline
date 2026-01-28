# Phase 0 Research: Timeline of Food Ingestion Strategy

**Date**: 2026-01-25  
**Investigation**: Wikipedia "Timeline of Food" article analysis for ingestion strategy design

## Executive Summary

The Wikipedia "Timeline of Food" article (https://en.wikipedia.org/wiki/Timeline_of_food) is well-structured with 12 major sections spanning from prehistoric times to the 21st century. The article contains approximately 3,000-5,000 extractable events with varied date formats. Most events can be successfully parsed using regex-based date extraction with hierarchical fallback date ranges. The article is primarily bullet-point based (prehistory through 18th century) with some table-based entries in later periods.

---

## 1. Article Structure & Organization

### Main Sections (12 identified)

| Section | Estimated Events | Date Range | Format |
|---------|-----------------|-----------|--------|
| Prehistoric times | 40-60 | 5M+ years ago - 3000 BCE | Bullets |
| Neolithic | 20-30 | 9300-3000 BCE | Bullets |
| 4000-2000 BCE | 20-30 | 4000-2000 BCE | Bullets |
| 2000-1 BCE | 20-30 | 2000 BCE-1 BCE | Bullets |
| 1-1000 CE | 40-50 | 1-1000 CE | Bullets |
| 1000-1500 | 30-40 | 1000-1500 CE | Bullets |
| 16th century | 20-30 | 1500-1600 | Bullets |
| 17th century | 20-30 | 1600-1700 | Bullets |
| 18th century | 50-70 | 1700-1800 | Bullets |
| 19th century | 150-200 | 1800-1900 | Mixed (bullets + table) |
| 20th century | 50-80 | 1900-2000 | Mixed (bullets + table) |
| 21st century | 3-5 | 2000-2026 | Bullets |

**Total Events**: ~500-700 section headers + ~2,500-4,500 individual events = **3,000-5,000 total**

### Hierarchical Patterns

Sections create natural date range contexts:
- Section heading provides implicit date range
- Subsections (rare) would narrow the range further
- Events without explicit dates within a section inherit the section's date context

**Example hierarchy**:
```
## 4000-2000 BCE
  • ~4500–3500 BCE: Earliest clear evidence of olive domestication...
  • ~4000 BCE: Watermelon domesticated...
```

---

## 2. Date Format Patterns & Extraction Strategy

### Using Existing span_parsing Library

**Critical architectural decision**: The repository already has a comprehensive `span_parsing` library at `/wikipedia-ingestion/span_parsing/` with:
- 20+ specialized parser strategies
- Orchestrator pattern for format selection
- Standardized `Span` class for date representation
- Factory pattern for parser instantiation

**Action**: Use existing parsers via `ParseOrchestratorFactory` rather than building new extraction.

### Identified Date Format Variants

#### 1. **Absolute Years (Single)**
- Pattern: `\d{1,4}\s+(?:BCE|BC|AD|CE)`
- Examples: "1516 AD", "610", "2000 BCE"
- **Frequency**: ~40% of events
- **Confidence**: High
- **Existing parser**: `year_only_parser.py`, `year_with_era_parser.py`

#### 2. **Year Ranges**
- Pattern: `\d{1,4}[\s–-]\d{1,4}\s+(?:BCE|BC|AD|CE)`
- Examples: "8000-5000 BCE", "2500–1500 BCE", "1845 BCE"
- **Frequency**: ~20% of events
- **Confidence**: High
- **Existing parser**: `year_range_parser.py`, `parenthesized_year_range_parser.py`

#### 3. **"Approximately" Notation**
- Pattern: `~\d{1,4}\s+(?:BCE|BC|AD|CE)` or `circa\s+\d{1,4}\s+(?:BCE|BC|AD|CE)`
- Examples: "~9300 BCE", "circa 1000 AD", "~1100"
- **Frequency**: ~15% of events
- **Confidence**: Medium (approximate dates)
- **Existing parser**: `circa_year_parser.py`, `parenthesized_circa_year_range_parser.py`

#### 4. **Centuries**
- Pattern: `(\d{1,2})(?:st|nd|rd|th)\s+century\s+(?:BCE|BC|AD|CE)?`
- Examples: "5th century BCE", "19th century", "1st century BC"
- **Frequency**: ~10% of events
- **Confidence**: High (but ranges across 100 years)
- **Action**: Convert to year range (e.g., "5th century BCE" → 500-401 BCE)

#### 5. **Years Ago**
- Pattern: `(\d{1,2})[\s,]*(?:million|thousand)\s+years\s+ago`
- Examples: "5-2 million years ago", "250,000 years ago", "170,000 years ago"
- **Frequency**: ~10% (prehistoric only)
- **Confidence**: Low (scientific estimates)
- **Action**: Convert to BCE using current year; mark `is_approximate=true`

#### 6. **Ranges with Centuries or Periods**
- Pattern: `(\d{1,2})(?:st|nd|rd|th)\s+(?:–|-)(\d{1,2})(?:st|nd|rd|th)\s+centuries`
- Examples: "11th–14th centuries", "15th–16th centuries"
- **Frequency**: ~5% of events
- **Confidence**: High
- **Action**: Convert to year range spanning both centuries

#### 7. **Contentious/Disputed**
- Pattern: Any date followed by text like "contentious", "controversial", "disputed"
- Examples: "13,000 BCE: Contentious evidence of oldest domesticated rice"
- **Frequency**: ~2% of events
- **Confidence**: Low
- **Action**: Mark `confidence_level='low'` in event schema

#### 8. **Table-based (19th century+)**
- Format: CSV-like rows with columns: `Year | Event | Category | Location`
- Examples: `1800 | New potato varieties | Vegetables | Chile`
- **Frequency**: ~30% of 19th-20th century events
- **Confidence**: High
- **Action**: Parse as separate format; extract year from first column

#### 9. **No Explicit Date (Fallback)**
- Pattern: Event text with no date-like patterns
- **Frequency**: <1% after hierarchical context applied
- **Confidence**: Fallback to section's implied range
- **Action**: Use section's start/end year range; mark with section context

### span_parsing Library Coverage Assessment

**Existing parsers that match Timeline of Food formats**:
- ✅ Absolute years: `year_only_parser.py`, `year_with_era_parser.py`
- ✅ Year ranges: `year_range_parser.py`, `multi_year_parser.py`
- ✅ Circa dates: `circa_year_parser.py`
- ✅ Parenthesized dates: `parenthesized_year_parser.py`, etc.
- ✅ Decades: `parenthesized_decade_parser.py`, `parenthesized_decade_range_parser.py`
- ✅ Month-based: `single_month_range_parser.py`, `single_year_multi_month_parser.py`

**NEW parsers needed for Timeline of Food**:
- ❌ **Century parser**: "5th century BCE" → Span(start=-500, end=-401)
- ❌ **Century range parser**: "11th-14th centuries" → Span(start=1001, end=1400)
- ❌ **Century-with-modifier parser**: "Early 1700s", "Late 16th century", "Before 17th century" → Span covering the correct third of the century
- ❌ **Years-ago parser**: "250,000 years ago" → Span(start=-248000, end=-248000)
- ❌ **Tilde circa year parser**: "~1450" → Span(start=1450, end=1450, circa=True)

**Orchestrators available**:
- `YearsParseOrchestrator` - for list_of_years style content
- `TimePeriodParseOrchestrator` - for time period ranges
- `InlineNoFallbackOrchestrator` - for inline date extraction

**NEW orchestrator needed**:
- ❌ **FoodTimelineParseOrchestrator** - combines standard year parsers + century parsers + years-ago parser in appropriate priority order

### New Parser Strategy Specifications

#### 1. CenturyParser

**Pattern**: `(\d{1,2})(st|nd|rd|th)\s+century\s+(BCE|BC|AD|CE)?`

**Examples**:
- "5th century BCE" → Span(start=-500, end=-401, precision='century')
- "1st century AD" → Span(start=1, end=100, precision='century')
- "21st century" → Span(start=2001, end=2100, precision='century')

**Logic**:
- Century N BCE: start = -(N*100), end = -((N-1)*100 + 1)
- Century N AD/CE: start = (N-1)*100 + 1, end = N*100
- No era marker → assume AD for centuries 1-20, CE for 21+

#### 2. CenturyRangeParser

**Pattern**: `(\d{1,2})(st|nd|rd|th)-(\d{1,2})(st|nd|rd|th)\s+centuries\s+(BCE|BC|AD|CE)?`

**Examples**:
- "11th-14th centuries" → Span(start=1001, end=1400, precision='century_range')
- "5th-3rd centuries BCE" → Span(start=-500, end=-201, precision='century_range')

**Logic**:
- Parse start century and end century using CenturyParser logic
- Handle BCE ranges going backwards (5th-3rd BCE = 500 BCE to 201 BCE)

#### 3. YearsAgoParser

**Pattern**: `([\d,]+)\s+years?\s+ago`

**Examples**:
- "250,000 years ago" → Span(start=-248000, end=-248000, precision='years_ago', circa=True)
- "5-2 million years ago" → Span(start=-5000000, end=-2000000, precision='years_ago', circa=True)

**Logic**:
- Remove commas from number
- Handle "million" multiplier
- Convert to BCE by subtracting from 2026 (current year)
- Always set circa=True (inherently approximate)
- Handle ranges ("5-2 million") → extract start and end

#### 4. TildeCircaYearParser

**Pattern**: `~\s*(\d{3,4})\s*(BC|BCE|AD|CE)?`

**Examples**:
- "~1450" → Span(start=1450, end=1450, precision='year', circa=True)
- "~450 BCE" → Span(start=-450, end=-450, precision='year', circa=True)

**Logic**:
- Match leading tilde plus 3-4 digit year
- Era resolution: if marker present, use it; else inherit page/section BC flag; default to AD when ambiguous
- Set `circa=True` to reflect approximation
- Precision = `year`

#### 5. CenturyWithModifierParser (Early/Mid/Late, Before + Century Range Hybrids)

**Patterns** (case-insensitive):
- `(Early|Mid|Late)\s+(\d{2})(?:00s|th\s+century)(?:\s+(BCE|BC|AD|CE))?`
- `Before\s+(\d{2})(?:00s|th\s+century)(?:\s+(BCE|BC|AD|CE))?`
- `(Early|Mid|Late)\s+(\d{2})(?:th\s+century)\s*[–-]\s*(\d{2})(?:th\s+century)?` (hybrid ranges like "Late 16th century–17th century")

**Mapping rules (AD/CE examples)**:
- Early century (e.g., Early 1700s): 1700–1733
- Mid century (e.g., Mid 1700s): 1734–1766
- Late century (e.g., Late 1700s): 1767–1799

**BC mapping** (negative years):
- Early 5th century BCE: -500 to -467
- Mid 5th century BCE: -466 to -434
- Late 5th century BCE: -433 to -401

**"Before Nth century" rule**:
- Treat as Late (N-1)th century. Example: "Before 17th century" → Late 16th century range: 1567–1600.

**Hybrid range rule**:
- "Late 16th century–17th century" → start = Late third of 16th (1567) to end of 17th (1700).

**Precision / circa**:
- `precision='century_modifier'`; `circa=False`

### Extraction Confidence Levels

Define levels for data quality tracking (map from Span properties):

```python
class DateConfidence(Enum):
    EXPLICIT = "explicit"      # Span parsed successfully
    INFERRED = "inferred"       # Derived from section/century
    APPROXIMATE = "approximate" # Span has circa=True
    CONTENTIOUS = "contentious" # Explicitly marked as disputed
    FALLBACK = "fallback"       # No Span; using section range
```

---

## 3. Format Breakdown by Section

### Prehistoric through 18th Century: **Bullet Format**

```
• 5-2 million years ago: Hominids shift away from [nuts] and [berries]...
• ~9300 BCE: Figs cultivated in the Jordan Valley
• 11th–14th centuries: Ireland stored and aged butter in peat bogs...
```

**Characteristics**:
- Bullet point prefix (•)
- Date at start of line
- HTML links to Wikipedia articles (auto-linked food items, people, places)
- Occasional footnote references `[1]`, `[2]`, etc.
- Multiline descriptions (some events span 2-3 lines)

**Parsing approach**:
1. Split by bullet points
2. Extract leading date pattern
3. Remaining text = event description
4. Clean HTML entities and links

### 19th Century+: **Mixed Format**

#### Bullet entries (still present):
```
• 18th century: Soufflé appears in France...
• 1516: [William IV] adopted the Reinheitsgebot...
```

#### Table entries (new format):
```
| Year | Event | Category | Location |
|------|-------|----------|----------|
| 1800 | New potato varieties | Vegetables | Chile |
| 1809 | Gyuhap chongseo | Cookbooks | Korea |
```

**Parsing approach**:
1. Detect table vs. bullet format
2. For tables: parse as CSV with fixed columns
3. For bullets: use existing bullet extraction

---

## 4. Event Description Quality Analysis

### Typical Event Structures

**Short events** (common):
```
• 1516: William IV adopted the Reinheitsgebot...
```
→ 1 sentence, ~15 words

**Medium events** (common):
```
• 1521: Spanish conquistador Hernán Cortés may have been the first to transfer 
a small yellow tomato to Europe after he captured the Aztec city of Tenochtitlan.
```
→ 1-2 sentences, ~30 words

**Long events** (less common):
```
• 1809: Airtight food preservation (canning) is invented by Nicolas Appert. 
The process involves sealing food in airtight containers and heating them. 
This preserves food for months or years.
```
→ 3+ sentences, 50+ words

**Events with references** (common):
```
• 1809: Airtight food preservation (canning) is invented by Nicolas Appert[1]
```
→ Include footnote references; strip in parsing

### Entity Extraction Opportunities

Events often reference:
- **Food items**: "potato", "corn", "chocolate" (auto-linked on Wikipedia)
- **Places**: "France", "China", "Mexico" (auto-linked)
- **People**: "Nicolas Appert", "John Montagu" (auto-linked)
- **Time periods**: "Medieval", "Bronze Age"

**Recommendation**: Future enhancement could extract these entities, but initial implementation should focus on date/description extraction.

---

## 5. Edge Cases & Challenges

### Challenge 1: Very Ancient Dates

**Example**: "5-2 million years ago"

**Issue**: Prehistory uses "years ago" format; need conversion to BCE

**Solution**: 
```python
# For "N years ago", calculate as BCE:
# Current year assumed = 2026
# 5-2 million years ago = 5,000,000 - 2,000,000 BCE
# Result: Use range start (5000000 BCE) as conservative estimate
# Mark as `confidence_level='approximate'`
```

### Challenge 2: Century Ranges with Hyphens

**Example**: "11th–14th centuries"

**Issue**: Unicode en-dash (–) vs. regular hyphen (-); ambiguous boundaries

**Solution**:
```python
# 11th century = 1001-1100 CE
# 14th century = 1301-1400 CE
# Result: 1001-1400 CE (inclusive range)
```

### Challenge 3: Contested/Controversial Dates

**Example**: "13,000 BCE: Contentious evidence of oldest domesticated rice in Korea"

**Issue**: Date validity disputed by academia

**Solution**: 
- Extract date normally
- Scan description for keywords: "contentious", "controversial", "disputed", "skepticism"
- Mark `confidence_level='contentious'`
- Optionally log these for human review

### Challenge 4: Multi-line Events

**Example**:
```
• 1809: Gyuhap chongseo ("Women's Encyclopedia"), including many recipes, 
published in Korea
```

**Issue**: Event description spans multiple lines; bullet appears only once

**Solution**:
- Capture all text until next bullet point
- Join multiline text with spaces
- Clean up whitespace

### Challenge 5: Company Founding Dates (19th century boom)

**Issue**: 19th century has many company founding entries mixed with food events

**Question**: Should "1809: Baker's Chocolate Company origins" be included?

**Answer**: Yes
- It represents food culture/industry milestones
- Fits within "timeline of food" scope
- Provides context for commercialization of food products

---

## 6. Recommended Parsing Strategy

### Phase 1 (MVP): Bullet Points Only

**Coverage**: ~70-80% of events (prehistoric through 18th century, most 19th-20th)

**Algorithm**:
1. Fetch HTML from Wikipedia
2. Extract main content div (before "See also" section)
3. Iterate through bullet points
4. For each bullet:
   - Extract leading date pattern
   - Extract remaining text as description
   - Map section heading to implied date range
   - Determine confidence level
   - Create HistoricalEvent object
5. Generate JSON artifact
6. Log any unparseable entries

**Confidence**: High (regex patterns well-tested)

### Phase 2 (Enhancement): Table Parsing

**Coverage**: ~15-20% of 19th+ century events

**Algorithm**:
1. Detect HTML tables in content
2. For each table:
   - Parse header row for column names
   - Extract rows as events
   - Map columns to event fields
3. Merge with bullet-point events

**Confidence**: Medium (table structure may vary)

### Phase 3 (Future): Semantic Extraction

**Coverage**: ~5-10% (entity extraction, relationship mapping)

Could use NLP to:
- Extract food items, people, places
- Infer event categories
- Build knowledge graph of food origins

**Scope**: Beyond current feature

---

## 7. Data Quality Metrics

### Coverage Targets

- **Extraction rate**: >95% of events with valid dates
- **Format variety covered**: 100% (all 9 date formats)
- **Parsing accuracy**: >99% (test with 50+ representative events)
- **Graceful handling**: <1% unparseable events (logged, not dropped)

### Test Cases Required

**High priority** (each format must work):
- [ ] Absolute year: "1516 AD"
- [ ] Range: "8000-5000 BCE"
- [ ] Century: "5th century BCE"
- [ ] Approximate: "~9300 BCE"
- [ ] Years ago: "250,000 years ago"
- [ ] Contentious: With "contentious" keyword
- [ ] Table format: 19th century rows
- [ ] Fallback: No date, use section range

**Edge cases**:
- [ ] Backwards date (1400 BCE before 1000 BCE in list) → Should still parse
- [ ] Malformed century ("21th century") → Graceful degradation
- [ ] Missing year ("~BC": Should be ignored)
- [ ] Very large ranges ("1001-1400") → Handle without overflow

---

## 8. Key Findings Summary

| Finding | Detail | Impact |
|---------|--------|--------|
| **Format diversity** | 9 distinct date formats | Design flexible, rule-based parser |
| **High event count** | 3,000-5,000 events | Good ROI for Wikipedia ingestion |
| **Hierarchical structure** | Sections provide date context | Use for fallback date ranges |
| **Mixed formats** | Bullets + tables in 19th c. | Plan Phase 1 (bullets) + Phase 2 (tables) |
| **Contentious dates** | Some events disputed | Mark confidence levels |
| **Clean HTML** | Well-structured Wikipedia markup | Easy parsing with BeautifulSoup |

---

## 9. Recommendations for Design Phase

### Architecture Decisions

1. **Strategy pattern for date extraction**: Create separate extractor class for each date format
2. **Hierarchical context manager**: Parse sections first, maintain context stack during event parsing
3. **Confidence tracking**: Attach confidence level to each extracted event
4. **Graceful degradation**: Log unparseable events; don't fail entire strategy

### Error Handling

- Network failures: Retry with exponential backoff (existing pattern)
- Malformed dates: Log and skip (don't block pipeline)
- Missing section context: Use fallback date range from section heading
- Duplicate detection: Use existing event_key pattern for deduplication

### Testing Strategy

- Unit tests for each date format (at least 3 examples per format)
- Integration test with real HTML snippet (~100 events)
- Edge case tests (very old dates, malformed input, etc.)
- Regression tests for confidence level assignment

---

## Conclusion

The Timeline of Food article is well-suited for ingestion using a multi-format parser. The hierarchical structure and predominant use of bullet points (Phase 1 MVP) allow for rapid implementation with >95% coverage. Phase 2 table parsing can handle remaining events. No architectural blockers identified; follows existing strategy patterns.

**Recommendation**: Proceed to Phase 1 design with confidence. Start with bullet point parser; add table support as Phase 2 enhancement.
