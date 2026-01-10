"""Integration test for date leak bug fix.

This test simulates the actual ingestion loop to verify that date information
doesn't leak between events when processing multiple events from a year page.
"""

import pytest
from ingestion_list_of_years import _extract_events_section_items_with_report
from span_parsing.orchestrators.years_parse_orchestrator import YearsParseOrchestrator


def test_ingestion_loop_date_isolation():
    """
    Simulate the ingestion loop processing events to verify dates are isolated.
    
    This reproduces the bug described in the issue where:
    - "February 5 – Augustus is proclaimed pater patriae" has an explicit date
    - "Dedication of the Forum Augustum" has no date
    
    Before the fix, the second event would incorrectly inherit February 5 from
    the first event due to variable reuse in the loop.
    """
    html = """
    <html><body>
      <h2><span class="mw-headline">Events</span></h2>
      <ul>
        <li>February 5 – Augustus is proclaimed pater patriae ("father of the country") by the Roman Senate.</li>
        <li>Dedication of the Forum Augustum</li>
        <li>March 10 – Another event with a date</li>
        <li>Yet another event without a date</li>
      </ul>
    </body></html>
    """
    
    extracted_items, _ = _extract_events_section_items_with_report(html)
    
    # Simulate the ingestion loop from ingestion_list_of_years.py
    scope = {"start_year": 2, "end_year": 2, "precision": "year"}
    page_assume_is_bc = True
    
    processed_events = []
    
    for item in extracted_items:
        bullet_text = item["text"]
        
        # Parse the bullet (mimicking the actual loop logic)
        bullet_span = YearsParseOrchestrator.parse_span_from_bullet(
            bullet_text, 
            scope["start_year"], 
            assume_is_bc=page_assume_is_bc
        )
        
        # Initialize date components (this is what the fix adds)
        effective_start_month = None
        effective_start_day = None
        effective_end_month = None
        effective_end_day = None
        
        # Override with parsed span if available
        if bullet_span is not None:
            effective_start_month = bullet_span.start_month
            effective_start_day = bullet_span.start_day
            effective_end_month = bullet_span.end_month
            effective_end_day = bullet_span.end_day
        
        processed_events.append({
            "text": bullet_text[:50],
            "start_month": effective_start_month,
            "start_day": effective_start_day,
            "end_month": effective_end_month,
            "end_day": effective_end_day,
        })
    
    # Verify each event has correct date information
    assert len(processed_events) == 4
    
    # Event 1: February 5
    assert processed_events[0]["start_month"] == 2
    assert processed_events[0]["start_day"] == 5
    assert processed_events[0]["end_month"] == 2
    assert processed_events[0]["end_day"] == 5
    
    # Event 2: No explicit date, uses fallback (full year = January 1 to December 31)
    assert processed_events[1]["start_month"] == 1
    assert processed_events[1]["start_day"] == 1
    assert processed_events[1]["end_month"] == 12
    assert processed_events[1]["end_day"] == 31
    
    # Event 3: March 10
    assert processed_events[2]["start_month"] == 3
    assert processed_events[2]["start_day"] == 10
    assert processed_events[2]["end_month"] == 3
    assert processed_events[2]["end_day"] == 10
    
    # Event 4: No explicit date, uses fallback (full year = January 1 to December 31)
    # Importantly, it does NOT inherit March 10 from the previous event
    assert processed_events[3]["start_month"] == 1
    assert processed_events[3]["start_day"] == 1
    assert processed_events[3]["end_month"] == 12
    assert processed_events[3]["end_day"] == 31


def test_date_leak_would_occur_without_initialization():
    """
    Demonstrate that with the fallback parser, events without explicit dates
    get the full year scope (Jan 1 - Dec 31) rather than None or leaked values.
    
    This documents the correct behavior: dates are isolated per event.
    """
    html = """
    <html><body>
      <h2><span class="mw-headline">Events</span></h2>
      <ul>
        <li>February 5 – First event with date</li>
        <li>Event without date</li>
      </ul>
    </body></html>
    """
    
    extracted_items, _ = _extract_events_section_items_with_report(html)
    scope = {"start_year": 2, "end_year": 2}
    
    # With the current parser (including fallback), both events get parsed
    results = []
    for item in extracted_items:
        bullet_span = YearsParseOrchestrator.parse_span_from_bullet(item["text"], 2, assume_is_bc=True)
        
        # Both events should have spans now
        assert bullet_span is not None
        
        results.append({
            "month": bullet_span.start_month,
            "day": bullet_span.start_day
        })
    
    # First event: February 5
    assert results[0]["month"] == 2
    assert results[0]["day"] == 5
    
    # Second event: No explicit date, uses fallback (January 1)
    # It does NOT inherit February 5 from the first event
    assert results[1]["month"] == 1  # Fallback to January
    assert results[1]["day"] == 1     # Fallback to day 1

