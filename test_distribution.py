#!/usr/bin/env python3
"""
Test script to verify event distribution across viewport.
"""
import requests
import json

API_URL = "http://localhost:8000"

def test_distribution():
    """Test that events are distributed across the viewport."""
    
    # Test viewport: 2005 AD to 2015 AD (around the events we have)
    params = {
        "viewport_start": 2005,
        "viewport_end": 2015,
        "viewport_is_bc_start": False,
        "viewport_is_bc_end": False,
        "limit": 200
    }
    
    response = requests.get(f"{API_URL}/events", params=params)
    events = response.json()
    
    print(f"Loaded {len(events)} events")
    print(f"Viewport: 2005 AD to 2015 AD")
    print()
    
    # Convert to negative years for easier math
    event_years = []
    for e in events:
        year = -e['start_year'] if e['is_bc_start'] else e['start_year']
        event_years.append(year)
    
    # Sort by year
    event_years.sort()
    
    # Divide into 10 bins and count events per bin
    viewport_min = 2005
    viewport_max = 2015
    span = viewport_max - viewport_min
    bins = 10
    
    bin_counts = [0] * bins
    for year in event_years:
        if viewport_min <= year <= viewport_max:
            bin_idx = min(int((year - viewport_min) / span * bins), bins - 1)
            bin_counts[bin_idx] += 1
    
    print("Distribution across viewport:")
    for i, count in enumerate(bin_counts):
        bin_start = viewport_min + (span * i / bins)
        bin_end = viewport_min + (span * (i + 1) / bins)
        bar = "█" * (count // 2)
        print(f"Bin {i:2d} ({int(bin_start):4d}-{int(bin_end):4d} AD): {count:3d} events {bar}")
    
    print()
    if not event_years:
        print("No events found in viewport!")
        return
    
    print(f"Min year: {-max(event_years)} BC" if max(event_years) < 0 else f"Min year: {min(event_years)} AD")
    print(f"Max year: {-min(event_years)} BC" if min(event_years) < 0 else f"Max year: {max(event_years)} AD")
    
    # Calculate standard deviation of bin counts
    import statistics
    std_dev = statistics.stdev(bin_counts) if len(bin_counts) > 1 else 0
    mean = statistics.mean(bin_counts)
    cv = (std_dev / mean * 100) if mean > 0 else 0
    print(f"\nMean events per bin: {mean:.1f}")
    print(f"Std deviation: {std_dev:.1f}")
    print(f"Coefficient of variation: {cv:.1f}%")
    
    # Test passes if we have events and they're reasonably distributed
    total_events = sum(bin_counts)
    if total_events == 0:
        print("\n❌ FAIL: No events found in viewport")
        return False
    elif total_events < 5:
        print(f"\n⚠️  WARNING: Only {total_events} events found - distribution test may not be meaningful")
        return True
    elif cv > 200:  # Very high variation indicates poor distribution
        print(f"\n❌ FAIL: Events are poorly distributed (CV = {cv:.1f}%)")
        return False
    else:
        print(f"\n✅ PASS: Events are reasonably distributed across viewport")
        return True

if __name__ == "__main__":
    success = test_distribution()
    exit(0 if success else 1)
