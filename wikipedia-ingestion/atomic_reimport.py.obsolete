"""Atomic reimport strategy for Wikipedia data.

This module provides functionality to reimport Wikipedia data into a temporary
table and then atomically swap it with the production table. This approach:

1. Preserves enrichment data (event_enrichments, event_categories) via event_key
2. Minimizes downtime - the table swap is near-instantaneous
3. Allows rollback if the import fails
4. Maintains referential integrity through foreign key constraints

Usage:
    python atomic_reimport.py

Environment Variables:
    Same as ingest_wikipedia.py (WIKI_MIN_YEAR, WIKI_MAX_YEAR, etc.)
"""

from __future__ import annotations

import os
import sys

try:
    from .ingestion_common import connect_db, log_error, log_info
    from .ingestion_list_of_years import ingest_wikipedia_list_of_years
except ImportError:
    from ingestion_common import connect_db, log_error, log_info
    from ingestion_list_of_years import ingest_wikipedia_list_of_years


def create_temp_table(conn, temp_table_name: str = "historical_events_temp") -> None:
    """Create a temporary table with the same schema as historical_events.
    
    Args:
        conn: Database connection
        temp_table_name: Name for the temporary table
    """
    log_info(f"Creating temporary table: {temp_table_name}")
    
    cursor = conn.cursor()
    try:
        # Create temp table with same schema as historical_events
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {temp_table_name} (
                LIKE historical_events INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
            );
        """)
        
        # Clear the temp table if it already exists
        cursor.execute(f"TRUNCATE TABLE {temp_table_name} RESTART IDENTITY CASCADE;")
        
        conn.commit()
        log_info(f"Temporary table {temp_table_name} ready")
    except Exception as e:
        conn.rollback()
        log_error(f"Failed to create temporary table: {e}")
        raise
    finally:
        cursor.close()


def drop_temp_table(conn, temp_table_name: str = "historical_events_temp") -> None:
    """Drop the temporary table.
    
    Args:
        conn: Database connection
        temp_table_name: Name of the temporary table to drop
    """
    log_info(f"Dropping temporary table: {temp_table_name}")
    
    cursor = conn.cursor()
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {temp_table_name} CASCADE;")
        conn.commit()
        log_info(f"Dropped {temp_table_name}")
    except Exception as e:
        conn.rollback()
        log_error(f"Failed to drop temporary table: {e}")
        raise
    finally:
        cursor.close()


def swap_tables(conn, temp_table_name: str = "historical_events_temp") -> None:
    """Atomically swap the temporary table with the production table.
    
    This operation:
    1. Drops foreign key constraints on enrichment tables
    2. Renames historical_events to historical_events_old
    3. Renames temp table to historical_events
    4. Recreates foreign key constraints
    5. Drops the old table
    
    Args:
        conn: Database connection
        temp_table_name: Name of the temporary table to promote
    """
    log_info("Beginning atomic table swap...")
    
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN;")
        
        # Drop foreign key constraints temporarily
        log_info("Dropping foreign key constraints...")
        cursor.execute("""
            ALTER TABLE event_enrichments 
            DROP CONSTRAINT IF EXISTS event_enrichments_event_key_fkey;
        """)
        cursor.execute("""
            ALTER TABLE event_categories 
            DROP CONSTRAINT IF EXISTS event_categories_event_key_fkey;
        """)
        
        # Rename current table to _old
        log_info("Renaming historical_events to historical_events_old...")
        cursor.execute("ALTER TABLE historical_events RENAME TO historical_events_old;")
        
        # Rename indexes to avoid conflicts
        cursor.execute("""
            ALTER INDEX IF EXISTS historical_events_pkey 
            RENAME TO historical_events_old_pkey;
        """)
        cursor.execute("""
            ALTER INDEX IF EXISTS uq_historical_events_identity 
            RENAME TO uq_historical_events_identity_old;
        """)
        cursor.execute("""
            ALTER INDEX IF EXISTS idx_historical_events_event_key 
            RENAME TO idx_historical_events_event_key_old;
        """)
        
        # Rename temp table to production
        log_info(f"Renaming {temp_table_name} to historical_events...")
        cursor.execute(f"ALTER TABLE {temp_table_name} RENAME TO historical_events;")
        
        # Rename temp table's indexes to production names
        cursor.execute(f"""
            ALTER INDEX IF EXISTS {temp_table_name}_pkey 
            RENAME TO historical_events_pkey;
        """)
        cursor.execute(f"""
            ALTER INDEX IF EXISTS {temp_table_name}_title_start_year_end_year_description_key 
            RENAME TO uq_historical_events_identity;
        """)
        cursor.execute(f"""
            ALTER INDEX IF EXISTS {temp_table_name}_event_key_idx 
            RENAME TO idx_historical_events_event_key;
        """)
        
        # Recreate foreign key constraints
        log_info("Recreating foreign key constraints...")
        cursor.execute("""
            ALTER TABLE event_enrichments
            ADD CONSTRAINT event_enrichments_event_key_fkey
            FOREIGN KEY (event_key) REFERENCES historical_events(event_key)
            ON DELETE CASCADE;
        """)
        cursor.execute("""
            ALTER TABLE event_categories
            ADD CONSTRAINT event_categories_event_key_fkey
            FOREIGN KEY (event_key) REFERENCES historical_events(event_key)
            ON DELETE CASCADE;
        """)
        
        # Drop the old table
        log_info("Dropping historical_events_old...")
        cursor.execute("DROP TABLE IF EXISTS historical_events_old CASCADE;")
        
        cursor.execute("COMMIT;")
        log_info("✅ Atomic table swap completed successfully!")
        
    except Exception as e:
        cursor.execute("ROLLBACK;")
        log_error(f"❌ Table swap failed, rolling back: {e}")
        raise
    finally:
        cursor.close()


def atomic_reimport() -> None:
    """Perform an atomic reimport of Wikipedia data.
    
    This function:
    1. Creates a temporary table
    2. Imports data into the temporary table
    3. Atomically swaps the temp table with the production table
    4. Cleans up
    
    Enrichment data (event_enrichments, event_categories) is preserved
    because it references events by event_key, not by table row ID.
    """
    temp_table_name = "historical_events_temp"
    conn = None
    
    try:
        conn = connect_db()
        
        # Step 1: Create temporary table
        create_temp_table(conn, temp_table_name)
        
        # Step 2: Set target table to temp table via environment
        log_info("Starting import into temporary table...")
        os.environ["INGEST_TARGET_TABLE"] = temp_table_name
        
        # Force reload of ingestion_common to pick up new table name
        import importlib
        import ingestion_common
        importlib.reload(ingestion_common)
        
        # Run the ingestion (this will populate the temp table)
        strategy = os.getenv("WIKIPEDIA_INGEST_STRATEGY", "list_of_years").strip().lower()
        
        if strategy in {"list_of_years", "years"}:
            ingest_wikipedia_list_of_years(conn)
        else:
            raise ValueError(f"Unsupported strategy for atomic reimport: {strategy}")
        
        log_info("Import completed successfully")
        
        # Step 3: Verify we have data
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {temp_table_name};")
        count = cursor.fetchone()[0]
        cursor.close()
        
        if count == 0:
            log_error("⚠️  No events were imported! Aborting table swap.")
            drop_temp_table(conn, temp_table_name)
            sys.exit(1)
        
        log_info(f"✅ Imported {count} events into temporary table")
        
        # Step 4: Atomic swap
        swap_tables(conn, temp_table_name)
        
        log_info(f"🎉 Atomic reimport completed! {count} events now in production.")
        
    except Exception as e:
        log_error(f"❌ Atomic reimport failed: {e}")
        if conn:
            try:
                drop_temp_table(conn, temp_table_name)
            except Exception:
                pass
        raise
    finally:
        if conn:
            conn.close()
        # Reset environment variable
        if "INGEST_TARGET_TABLE" in os.environ:
            del os.environ["INGEST_TARGET_TABLE"]


def main() -> None:
    try:
        atomic_reimport()
    except Exception as e:
        log_error(f"Atomic reimport failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    log_info("Starting atomic reimport of Wikipedia data...")
    main()
