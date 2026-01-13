#!/usr/bin/env python3
"""
Test script to validate all candidate_5_4_5_* variants
"""

import requests
import time
import json
from pathlib import Path

def test_candidate(candidate_name):
    """Test a specific candidate by checking if its files exist and are valid"""
    candidate_path = Path(f"frontend/{candidate_name}")

    if not candidate_path.exists():
        print(f"❌ {candidate_name}: Directory not found")
        return False

    required_files = ["index.html", "timeline.js", "style.css"]
    for file in required_files:
        if not (candidate_path / file).exists():
            print(f"❌ {candidate_name}: Missing {file}")
            return False

    # Check if HTML file contains the candidate title
    html_file = candidate_path / "index.html"
    with open(html_file, 'r') as f:
        content = f.read()
        # For the main candidate, check for "Timeline Candidate"
        if candidate_name == "candidate":
            if "Timeline Candidate" not in content:
                print(f"❌ {candidate_name}: HTML title doesn't match (expected: Timeline Candidate)")
                return False
        else:
            # For numbered candidates, check the old format
            display_name = candidate_name.replace('candidate_', 'Candidate ').replace('_', '.')
            if display_name not in content:
                print(f"❌ {candidate_name}: HTML title doesn't match (expected: {display_name})")
                return False

    # Check if JavaScript file is syntactically valid
    js_file = candidate_path / "timeline.js"
    try:
        with open(js_file, 'r') as f:
            js_content = f.read()
            # Basic syntax check - look for obvious issues
            if js_content.count('{') != js_content.count('}'):
                print(f"❌ {candidate_name}: JavaScript has mismatched braces")
                return False
            if js_content.count('(') != js_content.count(')'):
                print(f"❌ {candidate_name}: JavaScript has mismatched parentheses")
                return False
    except Exception as e:
        print(f"❌ {candidate_name}: JavaScript file error: {e}")
        return False

    print(f"✅ {candidate_name}: All files present and valid")
    return True

def test_api_connectivity():
    """Test that the API is responding"""
    try:
        response = requests.get("http://localhost:8000/events/bins?viewport_center=0&viewport_span=2000&zone=center&limit=10&max_weight=5000", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                print("✅ API: Connected and returning events data")
                return True
            else:
                print("❌ API: Connected but returned empty or invalid data")
                return False
        else:
            print(f"❌ API: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API: Connection failed: {e}")
        return False

def main():
    print("🧪 Testing Timeline Candidates 5.4.5.*\n")

    # Test API connectivity first
    if not test_api_connectivity():
        print("\n❌ Cannot proceed without working API")
        return

    print()

    # Test all candidates
    candidates = [
        "candidate"
    ]

    passed = 0
    total = len(candidates)

    for candidate in candidates:
        if test_candidate(candidate):
            passed += 1

    print(f"\n📊 Results: {passed}/{total} candidates passed validation")

    if passed == total:
        print("🎉 All candidates are ready for testing!")
        print("\nYou can now open each candidate in your browser:")
        for candidate in candidates:
            print(f"  http://localhost:3000/{candidate}/")
    else:
        print("⚠️  Some candidates need attention before testing")

if __name__ == "__main__":
    main()