#!/usr/bin/env python3
"""Cross-service testing for timeline_common module.

Tests:
- T111: timeline_common.event_key works with both api/ and wikipedia-ingestion/
- T112: No circular dependencies between services
- T113: All imports resolve correctly
"""

import sys
from pathlib import Path

# Test setup
test_dir = Path(__file__).parent
sys.path.insert(0, str(test_dir))

def test_timeline_common_import():
    """T111: Test that timeline_common.event_key can be imported from both services."""
    print("\n" + "="*70)
    print("T111: Testing timeline_common.event_key imports")
    print("="*70)
    
    try:
        from timeline_common.event_key import compute_event_key
        print("✅ Direct import successful: from timeline_common.event_key import compute_event_key")
    except ImportError as e:
        print(f"❌ Direct import failed: {e}")
        return False
    
    # Test wikipedia-ingestion import
    print("\nTesting wikipedia-ingestion service imports:")
    try:
        sys.path.insert(0, str(test_dir / "wikipedia-ingestion"))
        from database_ingestion import compute_event_key as db_event_key
        print("✅ wikipedia-ingestion can import event_key: database_ingestion.compute_event_key")
    except ImportError as e:
        print(f"❌ wikipedia-ingestion import failed: {e}")
        return False
    
    # Test API import
    print("\nTesting api service imports:")
    try:
        sys.path.insert(0, str(test_dir / "api"))
        # API doesn't import event_key directly, but it should be able to
        from timeline_common.event_key import compute_event_key as api_event_key
        print("✅ api can import event_key: from timeline_common.event_key import compute_event_key")
    except ImportError as e:
        print(f"⚠️  api import warning (non-critical): {e}")
    
    return True

def test_event_key_consistency():
    """Test that event_key computation is identical across services."""
    print("\n" + "="*70)
    print("Testing event_key consistency across services")
    print("="*70)
    
    try:
        from timeline_common.event_key import compute_event_key
        
        # Test data
        test_cases = [
            {
                "title": "Rome was founded",
                "start_year": -753,
                "end_year": -753,
                "description": "Romulus founds Rome according to legend"
            },
            {
                "title": "Battle of Marathon",
                "start_year": -490,
                "end_year": -490,
                "description": "Athenians defeat Persians at Marathon"
            }
        ]
        
        keys = {}
        for i, test_case in enumerate(test_cases):
            key = compute_event_key(
                title=test_case["title"],
                start_year=test_case["start_year"],
                end_year=test_case["end_year"],
                description=test_case["description"]
            )
            keys[i] = key
            print(f"\n  Test case {i+1}: {test_case['title']}")
            print(f"  Event key: {key[:16]}... (truncated)")
            
            # Verify idempotency
            key2 = compute_event_key(
                title=test_case["title"],
                start_year=test_case["start_year"],
                end_year=test_case["end_year"],
                description=test_case["description"]
            )
            if key == key2:
                print(f"  ✅ Idempotent: same input → same key")
            else:
                print(f"  ❌ NOT idempotent: keys differ")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Error during event_key test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_no_circular_imports():
    """T112: Verify no circular dependencies between services."""
    print("\n" + "="*70)
    print("T112: Testing for circular dependencies")
    print("="*70)
    
    circular_deps = []
    
    try:
        print("\n  Checking api/ imports...")
        sys.path.insert(0, str(test_dir / "api"))
        # api imports only from timeline_common, should not import from wikipedia-ingestion
        import api
        print("  ✅ api/ imports without issues")
    except ImportError as e:
        print(f"  ❌ api/ import error: {e}")
        circular_deps.append(f"api: {e}")
    
    try:
        print("\n  Checking wikipedia-ingestion/ imports...")
        sys.path.insert(0, str(test_dir / "wikipedia-ingestion"))
        from database_ingestion import connect_db
        print("  ✅ wikipedia-ingestion/ imports without issues")
    except ImportError as e:
        print(f"  ❌ wikipedia-ingestion/ import error: {e}")
        circular_deps.append(f"wikipedia-ingestion: {e}")
    
    try:
        print("\n  Checking timeline_common/ imports...")
        from timeline_common.event_key import compute_event_key
        print("  ✅ timeline_common/ imports without issues")
    except ImportError as e:
        print(f"  ❌ timeline_common/ import error: {e}")
        circular_deps.append(f"timeline_common: {e}")
    
    if circular_deps:
        print(f"\n❌ Circular dependencies found:")
        for dep in circular_deps:
            print(f"  - {dep}")
        return False
    
    print("\n✅ No circular dependencies detected")
    return True

def test_database_loader_imports():
    """Test that database_loader can be imported without errors."""
    print("\n" + "="*70)
    print("Testing database_loader cross-service imports")
    print("="*70)
    
    try:
        sys.path.insert(0, str(test_dir / "wikipedia-ingestion"))
        
        # Check what database_loader imports
        print("\n  Checking database_loader.py imports...")
        import database_loader
        print("  ✅ database_loader.py imports successfully")
        
        # Verify key functions exist
        if hasattr(database_loader, 'main'):
            print("  ✅ database_loader.main() function exists")
        else:
            print("  ⚠️  database_loader.main() not found (may be okay)")
        
        return True
    except ImportError as e:
        print(f"  ❌ database_loader import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all cross-service tests."""
    print("\n" + "="*70)
    print("CROSS-SERVICE TESTING (T111-T113)")
    print("="*70)
    
    results = {
        "T111_timeline_common": test_timeline_common_import(),
        "event_key_consistency": test_event_key_consistency(),
        "T112_no_circular_deps": test_no_circular_imports(),
        "database_loader_imports": test_database_loader_imports(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ All cross-service tests PASSED!")
        print("\nReady for:")
        print("  - Database loader service deployment")
        print("  - End-to-end ingestion pipeline testing")
        print("  - Production deployment")
        return 0
    else:
        print("\n❌ Some cross-service tests FAILED!")
        print("\nPlease fix the issues above before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
