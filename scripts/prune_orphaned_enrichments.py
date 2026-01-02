#!/usr/bin/env python3
"""
Prune Orphaned Enrichments Script

This script removes enrichment data (event_enrichments and event_categories)
that no longer has a corresponding event in the historical_events table.

This is expected to happen when:
- Wikipedia content changes (event text or dates are modified)
- Events are removed from Wikipedia
- The event_key hash changes due to content updates

Usage:
    python prune_orphaned_enrichments.py [--dry-run] [--verbose]

Options:
    --dry-run: Show what would be deleted without actually deleting
    --verbose: Show detailed information about orphaned enrichments
"""

import argparse
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """Get database connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'timeline_history'),
        user=os.getenv('DB_USER', 'timeline_user'),
        password=os.getenv('DB_PASSWORD', 'timeline_pass')
    )


def find_orphaned_enrichments(conn, verbose=False):
    """Find enrichments whose event_key is no longer in historical_events."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Find orphaned enrichments
    cursor.execute("""
        SELECT event_key, interest_count, last_enriched_at
        FROM event_enrichments
        WHERE event_key NOT IN (SELECT event_key FROM historical_events)
    """)
    orphaned_enrichments = cursor.fetchall()
    
    # Find orphaned categories
    cursor.execute("""
        SELECT event_key, category
        FROM event_categories
        WHERE event_key NOT IN (SELECT event_key FROM historical_events)
    """)
    orphaned_categories = cursor.fetchall()
    
    cursor.close()
    
    if verbose:
        print(f"\nFound {len(orphaned_enrichments)} orphaned enrichment records:")
        for enrich in orphaned_enrichments[:10]:  # Show first 10
            print(f"  - {enrich['event_key'][:16]}... "
                  f"(interest_count={enrich['interest_count']}, "
                  f"last_enriched={enrich['last_enriched_at']})")
        if len(orphaned_enrichments) > 10:
            print(f"  ... and {len(orphaned_enrichments) - 10} more")
        
        print(f"\nFound {len(orphaned_categories)} orphaned category records:")
        for cat in orphaned_categories[:10]:  # Show first 10
            print(f"  - {cat['event_key'][:16]}... category={cat['category']}")
        if len(orphaned_categories) > 10:
            print(f"  ... and {len(orphaned_categories) - 10} more")
    
    return len(orphaned_enrichments), len(orphaned_categories)


def prune_orphaned_enrichments(conn, dry_run=False):
    """Delete orphaned enrichments and categories."""
    cursor = conn.cursor()
    
    # Delete orphaned enrichments
    enrichments_sql = """
        DELETE FROM event_enrichments
        WHERE event_key NOT IN (SELECT event_key FROM historical_events)
    """
    
    # Delete orphaned categories
    categories_sql = """
        DELETE FROM event_categories
        WHERE event_key NOT IN (SELECT event_key FROM historical_events)
    """
    
    if dry_run:
        print("\n[DRY RUN] Would execute:")
        print(f"  {enrichments_sql}")
        print(f"  {categories_sql}")
        return 0, 0
    
    cursor.execute(enrichments_sql)
    enrichments_deleted = cursor.rowcount
    
    cursor.execute(categories_sql)
    categories_deleted = cursor.rowcount
    
    conn.commit()
    cursor.close()
    
    return enrichments_deleted, categories_deleted


def main():
    parser = argparse.ArgumentParser(
        description="Prune orphaned enrichments from the database"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed information about orphaned enrichments'
    )
    
    args = parser.parse_args()
    
    try:
        print("Connecting to database...")
        conn = get_db_connection()
        
        print("Scanning for orphaned enrichments...")
        enrichments_count, categories_count = find_orphaned_enrichments(
            conn, verbose=args.verbose
        )
        
        if enrichments_count == 0 and categories_count == 0:
            print("\n✓ No orphaned enrichments found. Database is clean.")
            return 0
        
        print(f"\nFound {enrichments_count} orphaned enrichment(s) "
              f"and {categories_count} orphaned category record(s)")
        
        if args.dry_run:
            print("\n[DRY RUN] No changes will be made.")
        
        print("\nPruning orphaned data...")
        deleted_enrichments, deleted_categories = prune_orphaned_enrichments(
            conn, dry_run=args.dry_run
        )
        
        if args.dry_run:
            print(f"\n[DRY RUN] Would delete {enrichments_count} enrichment(s) "
                  f"and {categories_count} category record(s)")
        else:
            print(f"\n✓ Deleted {deleted_enrichments} enrichment(s) "
                  f"and {deleted_categories} category record(s)")
        
        conn.close()
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
