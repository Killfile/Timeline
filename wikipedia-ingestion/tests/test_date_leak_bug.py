"""Test for date information leaking between events.

This test verifies that when processing multiple events from the same year,
date information from one event doesn't leak into subsequent events that
don't have explicit date information.
"""

import pytest
from pathlib import Path
from ingestion_list_of_years import _extract_events_section_items_with_report
from span_parsing import SpanParser


def test_date_does_not_leak_between_events():
    """Test that month/day information from first event doesn't leak to second event without that data."""
    # Simulate HTML with two events: one with a date, one without
    html = """
    <html><body>
      <h2><span class="mw-headline">Events</span></h2>
      <ul>
        <li>February 5 – Augustus is proclaimed pater patriae</li>
        <li>Dedication of the Forum Augustum</li>
      </ul>
    </body></html>
    """
    
    items, report = _extract_events_section_items_with_report(html)
    
    # We should have two items
    assert len(items) == 2
    
    # First event has explicit date
    first_bullet = items[0]["text"]
    first_span = SpanParser.parse_span_from_bullet(first_bullet, 2, assume_is_bc=True)
    assert first_span is not None
    assert first_span.start_month == 2
    assert first_span.start_day == 5
    
    # Second event has no date information
    second_bullet = items[1]["text"]
    second_span = SpanParser.parse_span_from_bullet(second_bullet, 2, assume_is_bc=True)
    # Jan 1 is assumed due to the fallback parser behavior
    assert second_span.start_month == 1
    assert second_span.start_day == 1
    


def test_multiple_events_with_varying_dates():
    """Test that date parsing is independent for each event."""
    html = """
    <html><body>
      <h2><span class="mw-headline">Events</span></h2>
      <ul>
        <li>February 5 – First event with date</li>
        <li>March 10 – Second event with different date</li>
        <li>Event without date which will be parsed by the fallback parser</li>
        <li>April 15 – Third event with yet another date</li>
      </ul>
    </body></html>
    """
    
    items, report = _extract_events_section_items_with_report(html)
    assert len(items) == 4
    
    # Parse each event's span independently
    spans = [
        SpanParser.parse_span_from_bullet(item["text"], 100, assume_is_bc=False)
        for item in items
    ]
    
    # First event: February 5
    assert spans[0] is not None
    assert spans[0].start_month == 2
    assert spans[0].start_day == 5
    
    # Second event: March 10
    assert spans[1] is not None
    assert spans[1].start_month == 3
    assert spans[1].start_day == 10
    
    # Third event: no date
    assert spans[2] is not None
    assert spans[2].start_month == 1
    assert spans[2].start_day == 1
    
    # Fourth event: April 15
    assert spans[3] is not None
    assert spans[3].start_month == 4
    assert spans[3].start_day == 15
