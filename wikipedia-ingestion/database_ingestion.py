"""Database helper functions extracted from ingestion_common.

This module owns DB configuration and insertion helpers so the core
ingestion utilities can remain focused on HTTP and parsing.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from event_key import compute_event_key
from span_parsing.span import SpanEncoder

# psycopg2 is only required for DB IO (not for HTML parsing/unit tests).
try:
    import psycopg2  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    psycopg2 = None


def _require_psycopg2():
    if psycopg2 is None:  # pragma: no cover
        raise RuntimeError(
            "psycopg2 is required for database operations. "
            "For local unit tests you can run pytest inside the Docker container, "
            "or install wikipedia-ingestion/requirements.txt in your host environment."
        )


# Database configuration
INGEST_TARGET_TABLE = os.getenv("INGEST_TARGET_TABLE", "historical_events")
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "database"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "timeline_history"),
    "user": os.getenv("DB_USER", "timeline_user"),
    "password": os.getenv("DB_PASSWORD", "timeline_pass"),
}


logger = logging.getLogger("timeline.database")


def connect_db():
    """Connect to the database with retry logic."""
    _require_psycopg2()
    max_retries = 5
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.autocommit = True
            logger.info(f"Successfully connected to database at {DB_CONFIG['host']}")
            return conn
        except psycopg2.OperationalError:
            if attempt < max_retries - 1:
                logger.error(
                    f"DB connection attempt {attempt + 1} failed. Retrying in {retry_delay} seconds..."
                )
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts")
                raise


def clear_previously_ingested(conn) -> None:
    """Clear previously ingested events."""
    _require_psycopg2()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN;")
        cur.execute("TRUNCATE TABLE event_date_extraction_debug RESTART IDENTITY;")
        cur.execute(f"TRUNCATE TABLE {INGEST_TARGET_TABLE} RESTART IDENTITY CASCADE;")
        cur.execute("COMMIT;")
        logger.info(f"Cleared {INGEST_TARGET_TABLE} + event_date_extraction_debug")
    except Exception:
        cur.execute("ROLLBACK;")
        raise
    finally:
        cur.close()


def get_or_create_strategy(conn, strategy_name: str) -> int:
    """Get or create a strategy record and return its ID."""
    _require_psycopg2()
    cur = conn.cursor()
    try:
        # First try to get existing strategy
        cur.execute("SELECT id FROM strategies WHERE name = %s", (strategy_name,))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # If not found, create it
        cur.execute(
            "INSERT INTO strategies (name) VALUES (%s) RETURNING id",
            (strategy_name,)
        )
        result = cur.fetchone()
        if result:
            conn.commit()
            return result[0]
        else:
            raise RuntimeError(f"Failed to create strategy: {strategy_name}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def insert_event(conn, event: dict, category: str | None, strategy_id: int | None = None):
    """Insert an event into the database.

    The event dict should include a 'weight' field with the pre-computed weight in days.
    If weight is not provided or is None, the event will be inserted without a weight.
    """
    _require_psycopg2()
    title = (event.get("title") or "").strip()
    if not title or len(title) < 3:
        return False

    try:
        conn.rollback()
    except Exception:
        pass

    # Compute deterministic event_key for enrichment association
    event_key = compute_event_key(
        title=event["title"],
        start_year=event.get("start_year") or 0,
        end_year=event.get("end_year") or 0,
        description=event.get("description"),
    )

    insert_sql = f"""
        INSERT INTO {INGEST_TARGET_TABLE}
            (event_key, title, description, start_year, start_month, start_day, 
             end_year, end_month, end_day, 
             is_bc_start, is_bc_end, weight, precision, category, wikipedia_url, strategy_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT ON CONSTRAINT uq_historical_events_identity DO NOTHING
        RETURNING id
    """

    insert_params = (
        event_key,
        event["title"],
        event.get("description"),
        event.get("start_year"),
        event.get("start_month"),
        event.get("start_day"),
        event.get("end_year"),
        event.get("end_month"),
        event.get("end_day"),
        event.get("is_bc_start", False),
        event.get("is_bc_end", False),
        event.get("weight"),
        event.get("precision"),
        category,
        event.get("url"),
        strategy_id,
    )

    if not hasattr(insert_event, "_seen_first_db_error"):
        insert_event._seen_first_db_error = False  # type: ignore[attr-defined]
    if not hasattr(insert_event, "_aborted_count"):
        insert_event._aborted_count = 0  # type: ignore[attr-defined]

    cursor = None
    try:
        cursor = conn.cursor()
        try:
            cursor.execute(insert_sql, insert_params)
        except psycopg2.errors.UndefinedObject:
            cursor.execute(
                f"""
                INSERT INTO {INGEST_TARGET_TABLE}
                    (event_key, title, description, start_year, start_month, start_day,
                     end_year, end_month, end_day,
                     is_bc_start, is_bc_end, weight, precision, category, wikipedia_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                insert_params,
            )

        row = cursor.fetchone()
        event_id = row[0] if row else None
        if event_id is None:
            return False

        debug = event.get("_debug_extraction")
        if debug:
            # Record weight for UI debugging.
            debug_weight = debug.get("weight_days")
            if debug_weight is None:
                debug_weight = event.get("weight")

            cursor.execute(
                """
                INSERT INTO event_date_extraction_debug
                    (historical_event_id, pageid, title, category, wikipedia_url,
                     extraction_method, extracted_year_matches,
                     chosen_start_year, chosen_start_month, chosen_start_day,
                     chosen_is_bc_start, 
                     chosen_end_year, chosen_end_month, chosen_end_day,
                     chosen_is_bc_end,
                     chosen_weight_days,
                     chosen_precision,
                     extract_snippet, span_match_notes)
                VALUES (%s, %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s,
                        %s, %s, %s,
                        %s,
                        %s,
                        %s,
                        %s, %s)
                """,
                (
                    event_id,
                    event.get("pageid"),
                    event.get("title"),
                    category,
                    event.get("url"),
                    debug.get("method", "unknown"),
                    json.dumps(debug.get("matches", []), cls=SpanEncoder),
                    event.get("start_year"),
                    event.get("start_month"),
                    event.get("start_day"),
                    event.get("is_bc_start", False),
                    event.get("end_year"),
                    event.get("end_month"),
                    event.get("end_day"),
                    event.get("is_bc_end", False),
                    debug_weight,
                    debug.get("precision"),
                    debug.get("snippet"),
                    event.get("span_match_notes"),
                ),
            )

        return True

    except Exception as e:
        details = ""
        if psycopg2 is not None and isinstance(e, psycopg2.Error):
            pgerror = getattr(e, "pgerror", None)
            diag = getattr(e, "diag", None)
            d_msg = getattr(diag, "message_primary", None) if diag else None
            d_detail = getattr(diag, "message_detail", None) if diag else None
            details = (
                f" pgerror={pgerror!r}" + (f" diag={d_msg!r}" if d_msg else "") + (f" detail={d_detail!r}" if d_detail else "")
            )

        msg = "Error inserting event: " + str(e) + details + f" title={event.get('title')!r}"

        if psycopg2 is not None and isinstance(e, psycopg2.Error) and "current transaction is aborted" in str(e).lower():
            insert_event._aborted_count += 1  # type: ignore[attr-defined]
            if insert_event._aborted_count % 50 == 1:  # type: ignore[attr-defined]
                logger.error(msg + f" (aborted_count={insert_event._aborted_count})")
        else:
            if not insert_event._seen_first_db_error:  # type: ignore[attr-defined]
                insert_event._seen_first_db_error = True  # type: ignore[attr-defined]
                logger.error("FIRST_DB_ERROR " + msg)
            else:
                logger.error(msg)

        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            if cursor is not None:
                cursor.close()
        except Exception:
            pass
