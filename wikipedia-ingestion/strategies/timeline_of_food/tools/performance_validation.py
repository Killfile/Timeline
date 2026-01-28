#!/usr/bin/env python3
"""Performance validation for Timeline of Food ingestion strategy.

Measures:
1. Fetch phase time
2. Parse phase time
3. Total processing time
4. Events per second throughput

Target: <30 seconds total, >100 events/second
"""

import sys
import time
from pathlib import Path
from statistics import mean, stdev
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from strategies.timeline_of_food.timeline_of_food_strategy import TimelineOfFoodStrategy


class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.elapsed = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.elapsed = time.time() - self.start_time


def run_performance_validation(num_runs: int = 3):
    """Run performance validation with multiple runs for averaging."""
    print("=" * 70)
    print("Timeline of Food - Performance Validation")
    print("=" * 70)
    print()
    
    fetch_times = []
    parse_times = []
    total_times = []
    event_counts = []
    
    for run in range(1, num_runs + 1):
        print(f"Run {run}/{num_runs}:")
        
        run_id = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        output_dir = Path("/tmp/timeline_of_food_perf")
        output_dir.mkdir(parents=True, exist_ok=True)
        strategy = TimelineOfFoodStrategy(run_id, output_dir)
        
        try:
            # Measure fetch time
            with PerformanceTimer("fetch") as timer:
                fetch_result = strategy.fetch()
                html = strategy.html_content
            
            if not html:
                print(f"  ✗ Fetch failed")
                continue
            
            fetch_time = timer.elapsed
            fetch_times.append(fetch_time)
            html_size = len(html)
            print(f"  Fetch: {fetch_time:.2f}s ({html_size} bytes)")
            
            # Measure parse time
            with PerformanceTimer("parse") as timer:
                parse_result = strategy.parse(fetch_result)
            
            parse_time = timer.elapsed
            parse_times.append(parse_time)
            events = parse_result.events
            event_counts.append(len(events))
            print(f"  Parse: {parse_time:.2f}s ({len(events)} events)")
            
            total_time = fetch_time + parse_time
            total_times.append(total_time)
            print(f"  Total: {total_time:.2f}s")
            
            # Calculate throughput
            if parse_time > 0:
                throughput = len(events) / parse_time
                print(f"  Throughput: {throughput:.0f} events/second")
            
            print()
            
        except Exception as e:
            print(f"  ✗ Run {run} failed: {e}")
            continue
    
    if not fetch_times:
        print("✗ No successful runs - cannot generate performance report")
        return False
    
    # Generate performance report
    print("=" * 70)
    print("PERFORMANCE REPORT")
    print("=" * 70)
    print()
    
    # Fetch metrics
    print("FETCH PHASE")
    print(f"  Runs: {len(fetch_times)}")
    print(f"  Average: {mean(fetch_times):.2f}s")
    if len(fetch_times) > 1:
        print(f"  StdDev: {stdev(fetch_times):.2f}s")
    print(f"  Min: {min(fetch_times):.2f}s")
    print(f"  Max: {max(fetch_times):.2f}s")
    print()
    
    # Parse metrics
    print("PARSE PHASE")
    print(f"  Runs: {len(parse_times)}")
    print(f"  Average: {mean(parse_times):.2f}s")
    if len(parse_times) > 1:
        print(f"  StdDev: {stdev(parse_times):.2f}s")
    print(f"  Min: {min(parse_times):.2f}s")
    print(f"  Max: {max(parse_times):.2f}s")
    print()
    
    # Total time metrics
    print("TOTAL TIME")
    avg_total = mean(total_times)
    print(f"  Average: {avg_total:.2f}s")
    if len(total_times) > 1:
        print(f"  StdDev: {stdev(total_times):.2f}s")
    print(f"  Min: {min(total_times):.2f}s")
    print(f"  Max: {max(total_times):.2f}s")
    print(f"  Target: <30s")
    total_check_passed = max(total_times) < 30.0
    print(f"  Result: {'✓ PASS' if total_check_passed else '✗ FAIL'}")
    print()
    
    # Throughput metrics
    print("THROUGHPUT")
    avg_events = mean(event_counts)
    avg_throughput = mean([count / parse_time for count, parse_time in zip(event_counts, parse_times)])
    print(f"  Average events extracted: {avg_events:.0f}")
    print(f"  Average throughput: {avg_throughput:.0f} events/second")
    print(f"  Target: >100 events/second")
    throughput_check_passed = avg_throughput > 100.0
    print(f"  Result: {'✓ PASS' if throughput_check_passed else '✗ FAIL'}")
    print()
    
    # Summary
    print("=" * 70)
    all_checks_passed = total_check_passed and throughput_check_passed
    if all_checks_passed:
        print("✓ ALL PERFORMANCE CHECKS PASSED")
    else:
        print("✗ SOME PERFORMANCE CHECKS FAILED")
    print("=" * 70)
    
    return all_checks_passed


if __name__ == "__main__":
    success = run_performance_validation()
    sys.exit(0 if success else 1)
