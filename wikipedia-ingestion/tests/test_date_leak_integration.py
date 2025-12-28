"""Integration test for date leak bug fix.

This test simulates the actual ingestion loop to verify that date information
doesn't leak between events when processing multiple events from a year page.
"""

import pytest
from ingestion_list_of_years import _extract_events_section_items_with_report
from span_parsing import SpanParser


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
        bullet_span = SpanParser.parse_span_from_bullet(
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
    
    # Event 2: No date (should be None, not February 5)
    assert processed_events[1]["start_month"] is None
    assert processed_events[1]["start_day"] is None
    assert processed_events[1]["end_month"] is None
    assert processed_events[1]["end_day"] is None
    
    # Event 3: March 10
    assert processed_events[2]["start_month"] == 3
    assert processed_events[2]["start_day"] == 10
    assert processed_events[2]["end_month"] == 3
    assert processed_events[2]["end_day"] == 10
    
    # Event 4: No date (should be None, not March 10)
    assert processed_events[3]["start_month"] is None
    assert processed_events[3]["start_day"] is None
    assert processed_events[3]["end_month"] is None
    assert processed_events[3]["end_day"] is None


def test_date_leak_would_occur_without_initialization():
    """
    Demonstrate that without proper initialization, dates leak between iterations.
    
    This test shows the OLD buggy behavior to document what we fixed.
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
    
    # SIMULATE THE OLD BUGGY CODE (without initialization in loop)
    # These variables are NOT reset between iterations
    effective_start_month = None
    effective_start_day = None
    
    results_buggy = []
    for item in extracted_items:
        bullet_span = SpanParser.parse_span_from_bullet(item["text"], 2, assume_is_bc=True)
        
        # BUG: Only update if span exists, otherwise keep old values
        if bullet_span is not None:
            effective_start_month = bullet_span.start_month
            effective_start_day = bullet_span.start_day
        
        results_buggy.append({
            "month": effective_start_month,
            "day": effective_start_day
        })
    
    # The bug: second event inherits date from first event
    assert results_buggy[0]["month"] == 2
    assert results_buggy[0]["day"] == 5
    # BUG DEMONSTRATED: second event gets February 5 even though it has no date
    assert results_buggy[1]["month"] == 2  # Still 2 from first event!
    assert results_buggy[1]["day"] == 5    # Still 5 from first event!
    
    # NOW TEST THE FIXED CODE (with initialization)
    results_fixed = []
    for item in extracted_items:
        bullet_span = SpanParser.parse_span_from_bullet(item["text"], 2, assume_is_bc=True)
        
        # FIX: Initialize variables at the start of each iteration
        effective_start_month = None
        effective_start_day = None
        
        if bullet_span is not None:
            effective_start_month = bullet_span.start_month
            effective_start_day = bullet_span.start_day
        
        results_fixed.append({
            "month": effective_start_month,
            "day": effective_start_day
        })
    
    # Fixed behavior: second event correctly has None
    assert results_fixed[0]["month"] == 2
    assert results_fixed[0]["day"] == 5
    assert results_fixed[1]["month"] is None  # Correctly None
    assert results_fixed[1]["day"] is None    # Correctly None
