"""Wikipedia ingestion entrypoint.

This file is intentionally thin.

- It provides a CLI entrypoint used by the Docker container (runs as a script).
- It re-exports a handful of functions that unit tests import from `ingest_wikipedia`.

Implementation lives in:
- `ingestion_common.py`
- `ingestion_list_of_years.py`
- `ingestion_by_category.py`
"""

from __future__ import annotations

import os

# Support BOTH:
# - `python -u ingest_wikipedia.py` (script execution inside container)
# - `python -m wikipedia_ingestion.ingest_wikipedia` (package-style)
try:
    from .ingestion_common import clear_previously_ingested, connect_db, insert_event, log_error, log_info
    from .ingestion_list_of_years import ingest_wikipedia_list_of_years

    # Test helper re-exports (used by tests importing from ingest_wikipedia)
    from .ingestion_common import _canonicalize_wikipedia_url, _require_psycopg2, _resolve_page_identity  # noqa: F401
    from .ingestion_list_of_years import (  # noqa: F401
        _DASH_RE,
        _extract_events_and_trends_bullets,
        _extract_events_section_items,
        _infer_page_era_from_html,
        _parse_scope_from_title,
        _parse_span_from_bullet,
    )
except ImportError:  # pragma: no cover
    from ingestion_common import clear_previously_ingested, connect_db, insert_event, log_error, log_info
    from ingestion_list_of_years import ingest_wikipedia_list_of_years

    # Test helper re-exports
    from ingestion_common import _canonicalize_wikipedia_url, _require_psycopg2, _resolve_page_identity  # noqa: F401
    from ingestion_list_of_years import (  # noqa: F401
        _DASH_RE,
        _extract_events_and_trends_bullets,
        _extract_events_section_items,
        _infer_page_era_from_html,
        _parse_scope_from_title,
        _parse_span_from_bullet,
    )


def ingest() -> None:
    """Run the ingestion using the configured strategy."""

    strategy = os.getenv("WIKIPEDIA_INGEST_STRATEGY", "list_of_years").strip().lower()

    conn = connect_db()
    try:
        clear_previously_ingested(conn)

        if strategy in {"list_of_years", "years"}:
            ingest_wikipedia_list_of_years(conn)
        elif strategy in {"by_category", "category", "categories"}:
            # Lazily import to keep unit tests (which don't need this strategy)
            # from paying the import cost or hitting relative-import issues.
            try:
                from .ingestion_by_category import ingest_wikipedia_by_category
            except ImportError:  # pragma: no cover
                from ingestion_by_category import ingest_wikipedia_by_category

            ingest_wikipedia_by_category(conn)
        else:
            raise ValueError(
                "Unknown WIKIPEDIA_INGEST_STRATEGY. "
                "Expected 'list_of_years' or 'by_category'. "
                f"Got: {strategy!r}"
            )
    finally:
        conn.close()


def main() -> None:
    try:
        ingest()
    except Exception as e:  # pragma: no cover
        log_error(f"Ingestion failed: {e}")
        raise


if __name__ == "__main__":
    log_info("Starting Wikipedia ingestion...")
    main()
