#!/usr/bin/env python3
"""
Test script to verify event distribution across viewport.
"""
import requests
import json

API_URL = "http://localhost:8000"

def test_distribution():
    """Test that events are distributed across the viewport."""
    
    # Test viewport: 500 BC to 500 BC (around ancient Greece/Rome)
    params = {
        "viewport_start": 800,
        "viewport_end": 200,
        "viewport_is_bc_start": True,
        "viewport_is_bc_end": True,
        "limit": 200
    }
    
    response = requests.get(f"{API_URL}/events", params=params)
    events = response.json()
    
    print(f"Loaded {len(events)} events")
    print(f"Viewport: 800 BC to 200 BC")
    print()
    
    # Convert to negative years for easier math
    event_years = []
    for e in events:
        year = -e['start_year'] if e['is_bc_start'] else e['start_year']
        event_years.append(year)
    
    # Sort by year
    event_years.sort()
    
    # Divide into 10 bins and count events per bin
    viewport_min = -800
    viewport_max = -200
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
        print(f"Bin {i:2d} ({int(-bin_start):4d}-{int(-bin_end):4d} BC): {count:3d} events {bar}")
    
    print()
    print(f"Min year: {-max(event_years)} BC" if max(event_years) < 0 else f"Min year: {min(event_years)} AD")
    print(f"Max year: {-min(event_years)} BC" if min(event_years) < 0 else f"Max year: {max(event_years)} AD")
    
    # Calculate standard deviation of bin counts
    import statistics
    std_dev = statistics.stdev(bin_counts) if len(bin_counts) > 1 else 0
    mean = statistics.mean(bin_counts)
    print(f"\nMean events per bin: {mean:.1f}")
    print(f"Std deviation: {std_dev:.1f}")
    print(f"Coefficient of variation: {(std_dev / mean * 100):.1f}%" if mean > 0 else "N/A")

if __name__ == "__main__":
    test_distribution()
