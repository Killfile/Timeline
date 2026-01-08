"""Wikipedia ingestion entrypoint.

This file is intentionally thin.

- It provides a CLI entrypoint used by the Docker container (runs as a script).
- It re-exports a handful of functions that unit tests import from `ingest_wikipedia`.

Implementation lives in:
- `ingestion_common.py`
- `ingestion_list_of_years.py`
- `bespoke_events_strategy.py`
"""

from __future__ import annotations

import os

# Support BOTH:
# - `python -u ingest_wikipedia.py` (script execution inside container)
# - `python -m wikipedia_ingestion.ingest_wikipedia` (package-style)
try:
    from .ingestion_common import log_error, log_info

    # Test helper re-exports (used by tests importing from ingest_wikipedia)
    from .ingestion_common import _canonicalize_wikipedia_url, _require_psycopg2, _resolve_page_identity  # noqa: F401
    from .ingestion_list_of_years import (  # noqa: F401
        _DASH_RE,
        _extract_events_and_trends_bullets,
        _extract_events_section_items,
        _infer_page_era_from_html,
        _parse_scope_from_title,
        #_parse_span_from_bullet,
    )
except ImportError:  # pragma: no cover
    from ingestion_common import log_error, log_info

    # Test helper re-exports
    from ingestion_common import _canonicalize_wikipedia_url, _require_psycopg2, _resolve_page_identity  # noqa: F401
    from ingestion_list_of_years import (  # noqa: F401
        _DASH_RE,
        _extract_events_and_trends_bullets,
        _extract_events_section_items,
        _infer_page_era_from_html,
        _parse_scope_from_title,
        #_parse_span_from_bullet,
    )


def ingest() -> None:
    """Run ingestion strategies to generate JSON artifacts.
    
    This function ONLY runs strategies to generate artifacts. It does NOT
    insert to the database. Use database_loader.py to load artifacts into the database.
    
    Supports:
    - WIKIPEDIA_INGEST_STRATEGY=list_of_years (default)
    - WIKIPEDIA_INGEST_STRATEGY=bespoke_events
    - WIKIPEDIA_INGEST_STRATEGY=time_periods
    - WIKIPEDIA_INGEST_STRATEGY=all (runs all registered strategies)
    - WIKIPEDIA_INGEST_STRATEGIES=list_of_years,bespoke_events,time_periods (explicit list)
    """

    strategy = os.getenv("WIKIPEDIA_INGEST_STRATEGY", "list_of_years").strip().lower()
    multi_strategies = os.getenv("WIKIPEDIA_INGEST_STRATEGIES", "").strip()

    # Lazy imports for new architecture
    try:
        from .strategies import ListOfYearsStrategy, BespokeEventsStrategy, ListOfTimePeriodsStrategy
        from .ingestion_common import LOGS_DIR, RUN_ID
    except ImportError:  # pragma: no cover
        from strategies import ListOfYearsStrategy, BespokeEventsStrategy, ListOfTimePeriodsStrategy
        from ingestion_common import LOGS_DIR, RUN_ID
    
    from pathlib import Path
    
    output_dir = Path(LOGS_DIR)
    
    # Determine which strategies to run
    if multi_strategies:
        # Explicit list from WIKIPEDIA_INGEST_STRATEGIES
        strategy_names = [s.strip().lower() for s in multi_strategies.split(",")]
    elif strategy == "all":
        # "all" means all available strategies
        strategy_names = ["list_of_years", "bespoke_events", "time_periods"]
    else:
        # Single strategy
        strategy_names = [strategy]
    
    log_info(f"Running {len(strategy_names)} strategy(ies): {', '.join(strategy_names)}")
    
    # Run each strategy
    artifact_count = 0
    for strategy_name in strategy_names:
        if strategy_name in {"list_of_years", "years"}:
            strategy_obj = ListOfYearsStrategy(RUN_ID, output_dir)
        elif strategy_name in {"bespoke_events", "bespoke"}:
            strategy_obj = BespokeEventsStrategy(RUN_ID, output_dir)
        elif strategy_name in {"time_periods", "periods"}:
            strategy_obj = ListOfTimePeriodsStrategy(RUN_ID, output_dir)
        else:
            log_error(f"Unknown strategy: {strategy_name}")
            continue
        
        try:
            log_info(f"=== Running strategy: {strategy_obj.name()} ===")
            
            # Run strategy phases
            fetch_result = strategy_obj.fetch()
            parse_result = strategy_obj.parse(fetch_result)
            artifact_result = strategy_obj.generate_artifacts(parse_result)
            strategy_obj.cleanup_logs()
            
            log_info(f"=== Strategy {strategy_obj.name()} complete: {artifact_result.artifact_path} ===")
            artifact_count += 1
            
        except Exception as e:
            log_error(f"Strategy {strategy_name} failed: {e}")
            import traceback
            log_error(traceback.format_exc())
            continue
    
    log_info(f"Ingestion complete: {artifact_count} artifact(s) generated")
    log_info("Run database_loader.py to load artifacts into the database")


def main() -> None:
    try:
        ingest()
    except Exception as e:  # pragma: no cover
        log_error(f"Ingestion failed: {e}")
        raise


if __name__ == "__main__":
    log_info("Starting Wikipedia ingestion...")
    main()
