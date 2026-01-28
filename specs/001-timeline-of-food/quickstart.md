# Quickstart: Timeline of Food Ingestion Strategy

**Date**: 2026-01-25  
**For**: Developers implementing the Timeline of Food ingestion strategy

---

## Overview

The Timeline of Food strategy extracts ~3,000-5,000 food-related historical events from Wikipedia's "Timeline of food" article (https://en.wikipedia.org/wiki/Timeline_of_food) and loads them into the timeline database.

The strategy follows the standard ETL pattern:
1. **Extract**: Fetch HTML from Wikipedia
2. **Translate**: Parse events, extract dates, create HistoricalEvent objects
3. **Load**: Insert into database via standard orchestrator

---

## Quick Start (5 minutes)

### 1. Run the Strategy (Standalone)

```bash
cd /Users/chris/Timeline/wikipedia-ingestion

# Activate venv
source .venv/bin/activate

# Run just the Timeline of Food strategy
python -c "
from strategies.ingestion_strategy_factory import IngestionStrategyFactory, IngestionStrategies
from pathlib import Path

strategy = IngestionStrategyFactory.get_strategy(
    IngestionStrategies.TIMELINE_OF_FOOD,
    run_id='test_run_001',
    output_dir=Path('artifacts')
)

fetch_result = strategy.fetch()
print(f'Fetched {fetch_result.fetch_count} pages')

parse_result = strategy.parse(fetch_result)
print(f'Parsed {len(parse_result.events)} events')

artifact_result = strategy.generate_artifacts(parse_result)
print(f'Artifact saved to {artifact_result.artifact_path}')
"
```

### 2. Run with Full Orchestrator

```bash
cd /Users/chris/Timeline/wikipedia-ingestion

# Run all strategies (including Timeline of Food)
python ingest_wikipedia.py timeline-of-food

# Or import and run programmatically:
from orchestrators.ingestion_orchestrator import IngestionOrchestrator

orchestrator = IngestionOrchestrator()
orchestrator.run_strategy('timeline-of-food')
```

### 3. View Generated Artifacts

```bash
# Check the generated JSON artifact
cat artifacts/timeline_of_food_*.json | jq '.metadata'

# Check the strategy log
cat logs/timeline_of_food_*.log | head -20
```

---

## Architecture

### Strategy Structure

```
wikipedia-ingestion/strategies/timeline_of_food/
├── __init__.py                      # Exports TimelineOfFoodStrategy
├── timeline_of_food_strategy.py     # Main strategy class (inherits IngestionStrategy)
├── date_extraction.py               # DateExtraction logic & patterns
├── hierarchical_parser.py           # Section/hierarchy parsing
├── tests/
│   ├── test_strategy.py
│   ├── test_dates.py
│   ├── test_hierarchy.py
│   └── fixtures/
│       ├── sample_article.html      # Test Wikipedia HTML snippet
│       └── expected_events.json      # Expected parse results
└── logs/                            # Runtime logs (created during execution)
```

### Key Classes

#### TimelineOfFoodStrategy (Main)

```python
class TimelineOfFoodStrategy(IngestionStrategy):
    """Extract food events from Timeline of Food Wikipedia article."""
    
    def fetch(self) -> FetchResult:
        """Fetch HTML from Wikipedia."""
        
    def parse(self, fetch_result: FetchResult) -> ParseResult:
        """Parse HTML → extract events."""
        
    def generate_artifacts(self, parse_result: ParseResult) -> ArtifactResult:
        """Generate JSON artifact file."""
```

#### DateExtraction (Date parsing)

```python
class DateExtractor:
    """Extract dates from event text using multiple strategies."""
    
    def extract(self, text: str) -> DateExtraction:
        """Parse date from text using regex patterns."""
        # Returns DateExtraction with confidence level
```

#### HierarchicalParser (Section context)

```python
class HierarchicalParser:
    """Parse Wikipedia sections to infer date ranges."""
    
    def parse_sections(self, html: str) -> list[TextSection]:
        """Extract section headers and infer date ranges."""
```

---

## Data Flow Example

### Input
```html
<h2>Neolithic</h2>
<ul>
  <li>• ~9300 BCE: Figs cultivated in the Jordan Valley[17]</li>
  <li>• ~8000 BCE: Squash was grown in Mexico</li>
</ul>
```

### Processing

1. **Extract Section**: "Neolithic" → `TextSection(date_range_start=9300, date_range_end=3000, ...)`
2. **Extract Event 1**:
   - Raw text: "~9300 BCE: Figs cultivated in the Jordan Valley[17]"
   - Date extraction: `DateExtraction(year_start=9300, is_approximate=True, confidence='approximate')`
   - Title: "Figs cultivated"
   - Description: "Figs cultivated in the Jordan Valley"
   - Result: `FoodEvent(..., date_explicit=9300, confidence_level='approximate', ...)`

3. **Extract Event 2**: Similar process for squash event

### Output (JSON Artifact)

```json
{
  "strategy": "TimelineOfFood",
  "run_id": "20260125_abc123",
  "event_count": 2,
  "events": [
    {
      "event_key": "abc123...",
      "title": "Figs cultivated",
      "description": "Figs cultivated in the Jordan Valley",
      "date_year": 9300,
      "confidence_level": "approximate",
      "section_name": "Neolithic"
    },
    ...
  ]
}
```

---

## Common Tasks

### Task 1: Test Date Extraction (using new FoodTimelineParseOrchestrator)

```python
from span_parsing.orchestrators.parse_orchestrator_factory import (
    ParseOrchestratorFactory,
    ParseOrchestratorTypes
)

# Get the custom orchestrator for Timeline of Food
orchestrator = ParseOrchestratorFactory.get_orchestrator(
    ParseOrchestratorTypes.FOOD_TIMELINE  # NEW orchestrator type
)

# Test various date formats (including NEW parser formats)
test_cases = [
    "~9300 BCE",          # Approximate (existing circa_year_parser)
    "8000-5000 BCE",      # Range (existing year_range_parser)
    "5th century BCE",    # Century (NEW century_parser)
    "11th-14th centuries", # Century range (NEW century_range_parser)
  "~1450",              # Tilde circa year (NEW tilde_circa_year_parser)
  "Early 1700s",        # Early century third (NEW century_with_modifier_parser)
  "Late 16th century",  # Late century third (NEW century_with_modifier_parser)
  "Before 17th century",# Maps to Late 16th (NEW century_with_modifier_parser)
  "Late 16th century–17th century", # Hybrid range (NEW century_with_modifier_parser)
    "250,000 years ago",  # Years ago (NEW years_ago_parser)
    "1516 AD",            # Absolute year (existing year_with_era_parser)
]

for text in test_cases:
    span = orchestrator.parse(text)
    if span:
        print(f"Input: '{text}'")
        print(f"  → Span(start={span.start}, end={span.end}, precision='{span.precision}', circa={span.circa})")
    else:
        print(f"Input: '{text}' → No span parsed (FAILURE)")
```

**Expected output**:
```
Input: '~9300 BCE'
  → Span(start=-9300, end=-9300, precision='year', circa=True)
Input: '8000-5000 BCE'
  → Span(start=-8000, end=-5000, precision='year', circa=False)
Input: '5th century BCE'
  → Span(start=-500, end=-401, precision='century', circa=False)
Input: '11th-14th centuries'
  → Span(start=1001, end=1400, precision='century_range', circa=False)
Input: "Early 1700s"
  → Span(start=1700, end=1733, precision='century_modifier', circa=False)
Input: "Late 16th century"
  → Span(start=1567, end=1600, precision='century_modifier', circa=False)
Input: "Before 17th century"
  → Span(start=1567, end=1600, precision='century_modifier', circa=False)
Input: "Late 16th century–17th century"
  → Span(start=1567, end=1700, precision='century_modifier', circa=False)
Input: "~1450"
  → Span(start=1450, end=1450, precision='year', circa=True)
Input: '250,000 years ago'
  → Span(start=-248000, end=-248000, precision='years_ago', circa=True)
Input: '1516 AD'
  → Span(start=1516, end=1516, precision='year', circa=False)
```

### Task 2: Test Section Hierarchy

```python
from strategies.timeline_of_food.hierarchical_parser import HierarchicalParser

parser = HierarchicalParser()

html = """
<h2>4000-2000 BCE</h2>
<ul><li>• ~4000 BCE: Event 1</li></ul>
<h2>1000-1500</h2>
<ul><li>• ~1200: Event 2</li></ul>
"""

sections = parser.parse_sections(html)
for section in sections:
    print(f"Section: {section.name}, Date range: {section.date_range_start}-{section.date_range_end}")
```

### Task 3: Generate Artifacts

```python
from strategies.timeline_of_food import TimelineOfFoodStrategy
from pathlib import Path

strategy = TimelineOfFoodStrategy(
    run_id='manual_test',
    output_dir=Path('artifacts')
)

# Run the full pipeline
fetch_result = strategy.fetch()
parse_result = strategy.parse(fetch_result)
artifact_result = strategy.generate_artifacts(parse_result)

print(f"Artifact: {artifact_result.artifact_path}")
print(f"Events: {len(parse_result.events)}")
```

---

## Testing

### Run Unit Tests

```bash
cd /Users/chris/Timeline/wikipedia-ingestion

# Run all Timeline of Food tests
pytest strategies/timeline_of_food/tests/ -v

# Run specific test
pytest strategies/timeline_of_food/tests/test_dates.py::test_date_range_extraction -v

# Run with coverage
pytest strategies/timeline_of_food/tests/ --cov=strategies.timeline_of_food --cov-report=html
```

### Run Integration Test

```bash
# Test against real Wikipedia article (with timeout)
python -c "
from strategies.timeline_of_food import TimelineOfFoodStrategy
from pathlib import Path
import time

start = time.time()
strategy = TimelineOfFoodStrategy('integration_test', Path('artifacts'))
fetch_result = strategy.fetch()
parse_result = strategy.parse(fetch_result)
elapsed = time.time() - start

print(f'Parsed {len(parse_result.events)} events in {elapsed:.2f} seconds')
assert len(parse_result.events) > 1000, 'Too few events parsed'
print('Integration test PASSED')
"
```

---

## Configuration

### Environment Variables

```bash
# (None required - uses sensible defaults)

# Optional: Override Wikipedia URL (for testing)
export TIMELINE_OF_FOOD_URL="file:///path/to/test.html"

# Optional: Override output directory
export INGESTION_OUTPUT_DIR="/custom/artifacts/path"
```

### Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or configure in code:
logger = logging.getLogger('strategies.timeline_of_food')
logger.setLevel(logging.DEBUG)
```

---

## Troubleshooting

### Problem: "Strategy not found" error

**Error**:
```
ValueError: Unknown ingestion strategy: TIMELINE_OF_FOOD
```

**Solution**: 
1. Check that `TimelineOfFood` is added to `IngestionStrategies` enum in `ingestion_strategy_factory.py`
2. Ensure strategy class is imported in factory
3. Verify class name matches enum value

### Problem: Very few events parsed

**Symptoms**: Only 100-200 events instead of 3,000+

**Possible causes**:
1. HTML structure changed on Wikipedia → Check HTML format
2. Date extraction failing → Run date extraction tests
3. Filtering too strict → Lower confidence level threshold

**Debug**:
```python
parse_result = strategy.parse(fetch_result)
print(f"Events by confidence:")
from collections import Counter
counts = Counter(e.confidence_level for e in parse_result.events)
print(counts)
```

### Problem: Date parsing incorrect

**Example**: "5th century" parsed as year 500 instead of range 401-500

**Solution**:
1. Add test case for this pattern
2. Fix regex or parsing logic
3. Re-run tests

```python
from strategies.timeline_of_food.date_extraction import DateExtractor
extractor = DateExtractor()
result = extractor.extract("5th century")
print(f"Result: {result.year_start}-{result.year_end}")
# Expected: 401-500 (for century-based logic)
```

---

## Development Workflow

1. **Make changes** to `timeline_of_food_strategy.py` or date extraction
2. **Run tests**: `pytest strategies/timeline_of_food/tests/ -v`
3. **Check coverage**: `pytest --cov=strategies.timeline_of_food`
4. **Run integration test** with real Wikipedia data
5. **Check artifacts** (JSON + log files) for correctness
6. **Commit** with clear message

---

## Next Steps

- [ ] Implement Phase 1 design (data model + strategy classes)
- [ ] Write unit tests for all date formats
- [ ] Test with real Wikipedia article
- [ ] Handle table-based entries (Phase 2)
- [ ] Add event categorization (Phase 3)
- [ ] Optimize for performance (if needed)

---

## Resources

- **Spec**: [spec.md](spec.md) - Feature requirements
- **Research**: [research.md](research.md) - Wikipedia article analysis
- **Data Model**: [data-model.md](data-model.md) - Entity definitions
- **Strategy Base**: `/strategies/strategy_base.py` - IngestionStrategy interface
- **Example**: `/strategies/list_of_years/list_of_years_strategy.py` - Reference implementation

---

**Questions?** Check the test files for working examples and usage patterns.
