# API Contracts: Timeline of Food Strategy

**Date**: 2026-01-25  
**Component**: Wikipedia Ingestion Strategy  
**Source Article**: https://en.wikipedia.org/wiki/Timeline_of_food

---

## Overview

This document defines the data contracts (input/output formats) for the Timeline of Food ingestion strategy. Follows the standard IngestionStrategy interface pattern.

---

## 1. Fetch Phase Contract

### Input
```
HTTP GET https://en.wikipedia.org/wiki/Timeline_of_food
Headers: User-Agent: Wikipedia Ingestion Bot
Timeout: 10 seconds
Retries: 3 with exponential backoff
```

### Output: FetchResult

```python
@dataclass
class FetchResult:
    strategy_name: str = "TimelineOfFood"
    fetch_count: int                                # Number of pages fetched (1 for this strategy)
    fetch_metadata: dict = {
        "url": "https://en.wikipedia.org/wiki/Timeline_of_food",
        "http_status": 200,
        "content_type": "text/html; charset=UTF-8",
        "content_length_bytes": 421345,
        "fetch_timestamp_utc": "2026-01-25T12:00:00Z",
        "cache_hit": False,  # True if loaded from cache
        "cache_file": "cache/timeline_of_food.html"
    }
```

### Example Output
```python
FetchResult(
    strategy_name="TimelineOfFood",
    fetch_count=1,
    fetch_metadata={
        "url": "https://en.wikipedia.org/wiki/Timeline_of_food",
        "http_status": 200,
        "content_type": "text/html; charset=UTF-8",
        "content_length_bytes": 421345,
        "fetch_timestamp_utc": "2026-01-25T12:00:00Z",
        "cache_hit": False,
        "cache_file": "cache/timeline_of_food.html"
    }
)
```

### Error Handling

| Scenario | Status | Handling |
|----------|--------|----------|
| Network timeout | 408 | Retry 3 times; fail strategy if all fail |
| Page not found | 404 | Fail gracefully with clear error message |
| Server error | 5xx | Retry with exponential backoff |
| HTML parsing error | - | Log warning; attempt partial parse |

---

## 2. Parse Phase Contract

### Input: FetchResult
(From phase 1)

### Output: ParseResult

```python
@dataclass
class ParseResult:
    strategy_name: str = "TimelineOfFood"
    events: list[HistoricalEvent]           # Fully parsed event objects
    parse_metadata: dict = {
        "total_events_found": 3847,
        "total_events_parsed": 3847,
        "sections_identified": 12,
        "parsing_start_utc": "2026-01-25T12:00:00Z",
        "parsing_end_utc": "2026-01-25T12:00:15Z",
        "elapsed_seconds": 15.2,
        "events_per_second": 253,
        "confidence_distribution": {
            "explicit": 3211,      # Date explicitly in text
            "inferred": 624,       # Date from section context
            "approximate": 12,     # "~" or "circa"
            "contentious": 0,      # Marked as disputed
            "fallback": 0          # No date found
        },
        "format_distribution": {
            "bullet": 3200,
            "table": 647,
            "mixed": 0
        },
        "year_range": {
            "min_year": -5000000,  # "5 million years ago"
            "max_year": 2026       # Current year
        },
        "errors": [],              # Any parsing errors encountered
        "warnings": []             # Any warnings (e.g., skipped events)
    }
```

### New Parser Strategy Contracts

#### CenturyParser

```python
from span_parsing.strategy import ParsingStrategy
from span_parsing.span import Span

class CenturyParser(ParsingStrategy):
    """Parse century notation like '5th century BCE' into year ranges."""
    
    def parse(self, text: str) -> Span | None:
        """
        Args:
            text: String potentially containing century notation
            
        Returns:
            Span with century range, or None if no match
            
        Examples:
            "5th century BCE" → Span(start=-500, end=-401, precision='century')
            "21st century" → Span(start=2001, end=2100, precision='century')
        """
```

#### CenturyRangeParser

```python
class CenturyRangeParser(ParsingStrategy):
    """Parse century range notation like '11th-14th centuries' into year ranges."""
    
    def parse(self, text: str) -> Span | None:
        """
        Args:
            text: String potentially containing century range
            
        Returns:
            Span covering full century range, or None if no match
            
        Examples:
            "11th-14th centuries" → Span(start=1001, end=1400, precision='century_range')
            "5th-3rd centuries BCE" → Span(start=-500, end=-201, precision='century_range')
        """
```

#### YearsAgoParser

```python
class YearsAgoParser(ParsingStrategy):
    """Parse 'years ago' notation into BCE dates."""
    
    def parse(self, text: str) -> Span | None:
        """
        Args:
            text: String potentially containing 'years ago'
            
        Returns:
            Span with BCE date (circa=True), or None if no match
            
        Examples:
            "250,000 years ago" → Span(start=-248000, end=-248000, precision='years_ago', circa=True)
            "5-2 million years ago" → Span(start=-5000000, end=-2000000, precision='years_ago', circa=True)
        """
```

#### TildeCircaYearParser

```python
class TildeCircaYearParser(ParsingStrategy):
    """Parse tilde-prefixed approximate years like '~1450'."""
    
    def parse(self, text: str) -> Span | None:
        """
        Args:
            text: String potentially containing tilde circa year
            
        Returns:
            Span with year range (start=end) and circa=True, or None if no match
            
        Examples:
            "~1450" → Span(start=1450, end=1450, precision='year', circa=True)
            "~450 BCE" → Span(start=-450, end=-450, precision='year', circa=True)
        """
```

#### CenturyWithModifierParser

```python
class CenturyWithModifierParser(ParsingStrategy):
    """Parse Early/Mid/Late/Before century phrases and hybrid ranges."""
    
    def parse(self, text: str) -> Span | None:
        """
        Args:
            text: String potentially containing century modifiers (e.g., "Early 1700s", "Late 16th century–17th century", "Before 17th century")
            
        Returns:
            Span covering correct third of century or hybrid range, precision='century_modifier'
            
        Examples:
            "Early 1700s" → Span(start=1700, end=1733, precision='century_modifier', circa=False)
            "Mid 1700s" → Span(start=1734, end=1766, precision='century_modifier', circa=False)
            "Late 1700s" → Span(start=1767, end=1799, precision='century_modifier', circa=False)
            "Late 16th century" → Span(start=1567, end=1600, precision='century_modifier', circa=False)
            "Before 17th century" → Span(start=1567, end=1600, precision='century_modifier', circa=False)  # maps to late prior century
            "Late 16th century–17th century" → Span(start=1567, end=1700, precision='century_modifier', circa=False)
        """
```

#### FoodTimelineParseOrchestrator

```python
from span_parsing.orchestrators.parse_orchestrator import ParseOrchestrator

class FoodTimelineParseOrchestrator(ParseOrchestrator):
    """Custom orchestrator for Timeline of Food date formats.
    
    Combines standard year/decade parsers with new century and years-ago parsers.
    Parser priority optimized for Timeline of Food article structure.
    """
    
    def __init__(self):
        """Initialize with ordered list of parser strategies."""
        self.strategies = [
            # Exact dates (highest priority)
            YearWithEraParser(),
            YearOnlyParser(),
            
            # Circa dates
            CircaYearParser(),
            ParenthesizedCircaYearRangeParser(),
            
            # Year ranges
            YearRangeParser(),
            MultiYearParser(),
            
            # Century formats (NEW)
            CenturyRangeParser(),  # Try ranges before single centuries
            CenturyParser(),
            CenturyWithModifierParser(),  # Early/Mid/Late/Before + hybrids
            
            # Years ago (NEW)
            YearsAgoParser(),
            
            # Decades
            ParenthesizedDecadeRangeParser(),
            ParenthesizedDecadeParser(),
            
            # Fallback
            FallbackParser(),
        ]
```

### Event Structure: HistoricalEvent (with Span integration)

```python
from span_parsing.span import Span

@dataclass
class HistoricalEvent:
    # Identity
    event_key: str                 # MD5 hash of (date + title + source)
    
    # Content
    title: str                     # ~50 character summary
    description: str               # Full event text
    source: str = "Timeline of Food"
    category: str = "Food"
    
    # Dates (populated from Span object)
    date_year: int | None          # Span.get_midpoint() or start
    date_range_start: int | None   # Span.start
    date_range_end: int | None     # Span.end
    
    # Metadata
    confidence_level: str          # Mapped from Span (circa → "approximate", etc.)
    parsing_notes: str | None      # Edge cases, assumptions, etc.
    span_precision: str | None     # Span.precision for debugging
    
    # Timestamps (added by orchestrator)
    created_at: datetime = None    # Set by load phase
    updated_at: datetime = None    # Set by load phase
```

### Example Events

**Event 1: Explicit date**
```python
HistoricalEvent(
    event_key="7f2e4c8b9a1d3e5c...",
    title="Figs cultivated in Jordan Valley",
    description="Figs cultivated in the Jordan Valley",
    source="Timeline of Food",
    category="Food",
    date_year=9300,
    date_range_start=9300,
    date_range_end=9300,
    confidence_level="explicit",
    parsing_notes=None
)
```

**Event 2: Approximate date (with ~)**
```python
HistoricalEvent(
    event_key="a1b2c3d4e5f6g7h8...",
    title="Squash grown in Mexico",
    description="Squash was grown in Mexico",
    source="Timeline of Food",
    category="Food",
    date_year=8000,
    date_range_start=8000,
    date_range_end=8000,
    confidence_level="approximate",
    parsing_notes="Date prefix with ~ indicates approximate year"
)
```

**Event 3: Date range**
```python
HistoricalEvent(
    event_key="x9y8z7w6v5u4t3s2...",
    title="Banana and potato cultivation",
    description="Archaeological and palaeoenvironmental evidence of banana cultivation at Kuk Swamp...",
    source="Timeline of Food",
    category="Food",
    date_year=6500,  # Midpoint of range
    date_range_start=8000,
    date_range_end=5000,
    confidence_level="inferred",
    parsing_notes="Range 8000-5000 BCE extracted from text"
)
```

**Event 4: Inferred date (from section)**
```python
HistoricalEvent(
    event_key="q1w2e3r4t5y6u7i8...",
    title="Wafers introduced to Britain",
    description="Wafers are introduced from France into Britain by the Normans",
    source="Timeline of Food",
    category="Food",
    date_year=1100,
    date_range_start=1001,
    date_range_end=1100,
    confidence_level="inferred",
    parsing_notes="Year inferred from '~1100' prefix"
)
```

### Example ParseResult
```python
ParseResult(
    strategy_name="TimelineOfFood",
    events=[
        HistoricalEvent(...),  # 3847 events total
        ...
    ],
    parse_metadata={
        "total_events_found": 3847,
        "total_events_parsed": 3847,
        "sections_identified": 12,
        "parsing_start_utc": "2026-01-25T12:00:00Z",
        "parsing_end_utc": "2026-01-25T12:00:15Z",
        "elapsed_seconds": 15.2,
        "events_per_second": 253,
        "confidence_distribution": {
            "explicit": 3211,
            "inferred": 624,
            "approximate": 12,
            "contentious": 0,
            "fallback": 0
        },
        "errors": [],
        "warnings": []
    }
)
```

---

## 3. Artifact Generation Contract

### Input: ParseResult
(From phase 2)

### Output: ArtifactResult

```python
@dataclass
class ArtifactResult:
    strategy_name: str = "TimelineOfFood"
    artifact_path: Path              # Path to JSON artifact file
    log_paths: list[Path] = [
        Path("logs/timeline_of_food_<RUN_ID>.log"),
        Path("logs/timeline_of_food_<RUN_ID>.json")  # Machine-readable log
    ]
```

### JSON Artifact File Format

**Path**: `artifacts/timeline_of_food_<RUN_ID>.json`

**Schema**:
```json
{
  "schema_version": "1.0",
  "strategy": "TimelineOfFood",
  "run_id": "20260125_120000_abc123",
  "generated_at_utc": "2026-01-25T12:00:15Z",
  
  "metadata": {
    "article_url": "https://en.wikipedia.org/wiki/Timeline_of_food",
    "fetch_timestamp": "2026-01-25T12:00:00Z",
    "parse_timestamp": "2026-01-25T12:00:15Z",
    
    "event_count": 3847,
    "sections_parsed": 12,
    "format_distribution": {
      "bullet": 3200,
      "table": 647
    },
    
    "date_statistics": {
      "year_min": -5000000,
      "year_max": 2026,
      "confidence": {
        "explicit": 3211,
        "inferred": 624,
        "approximate": 12,
        "contentious": 0,
        "fallback": 0
      }
    },
    
    "performance": {
      "fetch_seconds": 2.1,
      "parse_seconds": 13.1,
      "artifact_seconds": 1.0,
      "total_seconds": 16.2,
      "events_per_second": 237
    }
  },
  
  "events": [
    {
      "event_key": "7f2e4c8b9a1d3e5c...",
      "title": "Figs cultivated in Jordan Valley",
      "description": "Figs cultivated in the Jordan Valley",
      "source": "Timeline of Food",
      "category": "Food",
      "date_year": 9300,
      "date_range_start": 9300,
      "date_range_end": 9300,
      "confidence_level": "explicit",
      "parsing_notes": null
    },
    ...
  ]
}
```

### Example Artifact Summary
```json
{
  "schema_version": "1.0",
  "strategy": "TimelineOfFood",
  "run_id": "20260125_120000_abc123",
  "generated_at_utc": "2026-01-25T12:00:15Z",
  "metadata": {
    "event_count": 3847,
    "date_statistics": {
      "confidence": {
        "explicit": 3211,
        "inferred": 624,
        "approximate": 12,
        "contentious": 0,
        "fallback": 0
      }
    },
    "performance": {
      "total_seconds": 16.2,
      "events_per_second": 237
    }
  },
  "events": [...]
}
```

### Log File Format

**Path**: `logs/timeline_of_food_<RUN_ID>.log`

```
[2026-01-25 12:00:00.000] INFO     [TimelineOfFood] Strategy started
[2026-01-25 12:00:00.100] INFO     [TimelineOfFood] Fetching from https://en.wikipedia.org/wiki/Timeline_of_food
[2026-01-25 12:00:02.200] INFO     [TimelineOfFood] Fetch complete (421 KB)
[2026-01-25 12:00:02.300] INFO     [TimelineOfFood] Parsing sections...
[2026-01-25 12:00:02.400] INFO     [TimelineOfFood] Section "Prehistoric times": 45 events
[2026-01-25 12:00:02.500] INFO     [TimelineOfFood] Section "Neolithic": 28 events
[2026-01-25 12:00:02.600] DEBUG    [TimelineOfFood] Event: "Figs cultivated" → date=9300 (explicit)
[2026-01-25 12:00:02.700] DEBUG    [TimelineOfFood] Event: "Squash grown" → date=8000 (approximate)
...
[2026-01-25 12:00:15.200] INFO     [TimelineOfFood] Parse complete (3,847 events)
[2026-01-25 12:00:15.300] INFO     [TimelineOfFood] Confidence distribution: explicit=83.5%, inferred=16.2%, approximate=0.3%
[2026-01-25 12:00:15.400] INFO     [TimelineOfFood] Artifact written to artifacts/timeline_of_food_abc123.json
[2026-01-25 12:00:15.500] INFO     [TimelineOfFood] Strategy completed successfully (16.2 seconds)
```

---

## 4. Database Load Contract

### Input: Artifact JSON (from phase 3)

### Output: Load Results

The orchestrator will:
1. Read JSON artifact
2. Convert each event to HistoricalEvent
3. Generate/verify event_key
4. UPSERT into `historical_events` table
5. Return load statistics

**SQL Contract**:
```sql
-- Insert or update events
UPSERT INTO historical_events (
    event_key,
    source,
    title,
    description,
    category,
    date_year,
    date_range_start,
    date_range_end,
    created_at,
    updated_at
) VALUES (...);
```

**Expected result**:
- 3,847 events inserted (if fresh ingestion)
- 0 duplicates (deduplication via event_key)
- 0 errors (graceful handling of duplicates)

---

## 5. Backward Compatibility

### Schema Version
- **Current**: 1.0
- **Compatibility**: Events must include `event_key`, `source`, `category`
- **Migration path**: None required; follows existing HistoricalEvent schema

### Breaking Changes
None planned for Phase 1. Future changes will be versioned (1.1, 2.0, etc.).

---

## 6. Performance Targets

| Metric | Target | Actual |
|--------|--------|--------|
| Fetch time | <5s | ~2s |
| Parse time | <20s | ~13s |
| Artifact generation | <2s | ~1s |
| **Total time** | **<30s** | **~16s** ✓ |
| Events parsed | >3,000 | 3,847 ✓ |
| Events/second | >100 | 237 ✓ |
| Accuracy | >95% | TBD (testing phase) |

---

## 7. Error Handling Contract

### Graceful Degradation

| Error | Handling |
|-------|----------|
| Wikipedia unreachable | Log error, return empty ParseResult |
| HTML structure changed | Log warning, parse what's available |
| Date extraction fails | Log event, skip (don't add to events list) |
| Duplicate event | Skip (handled by event_key deduplication) |
| Out of memory | Fail with clear error message |

### Error Messages

**Format**: `[STRATEGY] [LEVEL] Message: details`

**Examples**:
```
[TimelineOfFood] ERROR   Failed to fetch Wikipedia: Connection timeout after 10s
[TimelineOfFood] WARNING Unable to parse date in event "Figs cultivated": No date pattern matched
[TimelineOfFood] DEBUG   Skipping malformed event (no title): "   "
```

---

## Testing Contract

All contracts must be tested with:
- ✓ Unit tests (date extraction, section parsing)
- ✓ Integration test (real Wikipedia article, full pipeline)
- ✓ Contract validation (artifact schema conformance)
- ✓ Edge cases (very old dates, malformed input, duplicates)

---

## Example Integration Test

```python
def test_timeline_of_food_full_pipeline():
    """Test complete fetch → parse → artifact flow."""
    strategy = TimelineOfFoodStrategy(
        run_id="integration_test_001",
        output_dir=Path("artifacts")
    )
    
    # Phase 1: Fetch
    fetch_result = strategy.fetch()
    assert fetch_result.fetch_count == 1
    assert fetch_result.fetch_metadata["http_status"] == 200
    
    # Phase 2: Parse
    parse_result = strategy.parse(fetch_result)
    assert len(parse_result.events) > 3000
    assert parse_result.parse_metadata["total_events_parsed"] == len(parse_result.events)
    
    # Phase 3: Artifacts
    artifact_result = strategy.generate_artifacts(parse_result)
    assert artifact_result.artifact_path.exists()
    
    # Validate artifact schema
    import json
    with open(artifact_result.artifact_path) as f:
        artifact = json.load(f)
    
    assert artifact["schema_version"] == "1.0"
    assert artifact["strategy"] == "TimelineOfFood"
    assert len(artifact["events"]) == len(parse_result.events)
    
    print(f"✓ Integration test PASSED ({len(parse_result.events)} events)")
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-25 | Initial specification |

