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
import sys

# Ensure /app is in sys.path for imports
sys.path.insert(0, '/app')

# Support BOTH:
# - `python -u ingest_wikipedia.py` (script execution inside container)
# - `python -m wikipedia_ingestion.ingest_wikipedia` (package-style)
try:
    from .ingestion_common import log_error, log_info
    from .strategies.ingestion_strategy_factory import IngestionStrategyFactory, IngestionStrategies
    from .strategies.strategy_base import IngestionStrategy
    # Test helper re-exports (used by tests importing from ingest_wikipedia)
    # ingestion_list_of_years.py has been consolidated into strategies/list_of_years/list_of_years_strategy.py
    # Legacy helper for backward compatibility
    

except ImportError:  # pragma: no cover
    from ingestion_common import log_error, log_info
    from strategies.ingestion_strategy_factory import IngestionStrategyFactory, IngestionStrategies
    from strategies.strategy_base import IngestionStrategy
    # Test helper re-exports
    # ingestion_list_of_years.py has been consolidated into strategies/list_of_years/list_of_years_strategy.py
    # Legacy helper for backward compatibility

   


def ingest(strategy_names: list[str] | None = None) -> None:
    """Run ingestion strategies to generate JSON artifacts.
    
    This function ONLY runs strategies to generate artifacts. It does NOT
    insert to the database. Use database_loader.py to load artifacts into the database.
    
    Args:
        strategy_names: List of strategy names to run. If None, uses environment variables.
    
    Command-line usage:
    - python ingest_wikipedia.py wars
    - python ingest_wikipedia.py list_of_years bespoke_events
    - python ingest_wikipedia.py all
    
    Environment variable usage (backward compatible):
    - WIKIPEDIA_INGEST_STRATEGY=list_of_years (default)
    - WIKIPEDIA_INGEST_STRATEGY=bespoke_events
    - WIKIPEDIA_INGEST_STRATEGY=time_periods
    - WIKIPEDIA_INGEST_STRATEGY=all (runs all registered strategies)
    - WIKIPEDIA_INGEST_STRATEGIES=list_of_years,bespoke_events,time_periods (explicit list)
    """

    # Determine which strategies to run
    if strategy_names is None:
        # Use environment variables (backward compatibility)
        strategy = os.getenv("WIKIPEDIA_INGEST_STRATEGY", "list_of_years").strip().lower()
        multi_strategies = os.getenv("WIKIPEDIA_INGEST_STRATEGIES", "").strip()
        
        if multi_strategies:
            # Explicit list from WIKIPEDIA_INGEST_STRATEGIES
            strategy_names = [s.strip().lower() for s in multi_strategies.split(",")]
        elif strategy == "all":
            # "all" means all available strategies
            strategy_names = [
                "list_of_years",
                "bespoke_events",
                "time_periods",
                "wars",
                "lgbtq_history",
                "lgbtq_history_v2",
                "timeline_of_food",
                "timeline_of_roman_history",
            ]
        else:
            # Single strategy
            strategy_names = [strategy]
    else:
        # Use provided strategy names
        strategy_names = [s.strip().lower() for s in strategy_names]
    
    # Lazy imports for new architecture
    try:
        from .strategies import ListOfYearsStrategy, BespokeEventsStrategy, ListOfTimePeriodsStrategy
        from .ingestion_common import LOGS_DIR, RUN_ID
        from .span_parsing.span import SpanEncoder
    except ImportError:  # pragma: no cover
        from strategies import ListOfYearsStrategy, BespokeEventsStrategy, ListOfTimePeriodsStrategy
        from ingestion_common import LOGS_DIR, RUN_ID
        from span_parsing.span import SpanEncoder
    
    import json
    from pathlib import Path
    
    output_dir = Path(LOGS_DIR)
    
    log_info(f"Running {len(strategy_names)} strategy(ies): {', '.join(strategy_names)}")
    
    # Run each strategy
    artifact_count = 0
    for strategy_name in strategy_names:
        strategy_obj = IngestionStrategyFactory.get_strategy(
            IngestionStrategies[strategy_name.upper()], RUN_ID, output_dir
        )
        
        try:
            log_info(f"=== Running strategy: {strategy_obj.name()} ===")
            
            # Run strategy phases
            artifact_data = strategy_obj.ingest()
            
            # Write artifact to disk (centralized file writing)
            filename = artifact_data.suggested_filename or f"events_{artifact_data.strategy_name}_{artifact_data.run_id}.json"
            artifact_path = output_dir / filename
            
            with open(artifact_path, "w", encoding="utf-8") as f:
                json.dump(artifact_data.to_dict(), f, indent=2, ensure_ascii=False, cls=SpanEncoder)
                f.write("\n")
            
            log_info(f"Wrote artifact: {artifact_path}")
            
            # Run cleanup (for strategy-specific logs)
            strategy_obj.cleanup_logs()
            
            log_info(f"=== Strategy {strategy_obj.name()} complete: {artifact_path} ===")
            artifact_count += 1
            
        except Exception as e:
            log_error(f"Strategy {strategy_name} failed: {e}")
            import traceback
            log_error(traceback.format_exc())
            continue
    
    log_info(f"Ingestion complete: {artifact_count} artifact(s) generated")
    log_info("Run database_loader.py to load artifacts into the database")


def main() -> None:
    """Parse command-line arguments and run ingestion."""
    import sys
    
    if len(sys.argv) > 1:
        # Use command-line arguments
        strategy_names = sys.argv[1:]
        ingest(strategy_names)
    else:
        # Use environment variables (backward compatibility)
        ingest()


if __name__ == "__main__":
    log_info("Starting Wikipedia ingestion...")
    main()
