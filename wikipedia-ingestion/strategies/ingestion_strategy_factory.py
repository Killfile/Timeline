from pathlib import Path
from strategies.strategy_base import IngestionStrategy
from enum import Enum, auto

class IngestionStrategies(Enum):
    """Enumeration of available ingestion strategies."""
    LIST_OF_YEARS = auto()
    BESPOKE_EVENTS = auto()
    TIME_PERIODS = auto()
    WARS = auto()
    LGBTQ_HISTORY = auto()
    LGBTQ_HISTORY_V2 = auto()

class IngestionStrategyFactory:
    ...
    @staticmethod
    def get_strategy(strategy: IngestionStrategies, run_id: str, output_dir: Path) -> IngestionStrategy:
        """Get an ingestion strategy instance for the specified strategy.
        
        Args:
            strategy: The type of ingestion strategy to create
            
        Returns:
            An instance of the requested ingestion strategy
            
        Raises:
            ValueError: If the strategy is unknown
        """
        # Import here to avoid circular dependencies
        from strategies.bespoke_events_strategy import BespokeEventsStrategy
        from strategies.list_of_time_periods import ListOfTimePeriodsStrategy
        from strategies.list_of_years import ListOfYearsStrategy
        from strategies.wars import WarsStrategy

        from strategies.lgbtq_history_v2 import LgbtqHistoryV2Strategy
        
        if strategy == IngestionStrategies.LIST_OF_YEARS:
            return ListOfYearsStrategy(run_id, output_dir)
        elif strategy == IngestionStrategies.BESPOKE_EVENTS:
            return BespokeEventsStrategy(run_id, output_dir)
        elif strategy == IngestionStrategies.TIME_PERIODS:
            return ListOfTimePeriodsStrategy(run_id, output_dir)
        elif strategy == IngestionStrategies.WARS:
            return WarsStrategy(run_id, output_dir)

        elif strategy == IngestionStrategies.LGBTQ_HISTORY_V2:
            return LgbtqHistoryV2Strategy(run_id, output_dir)
        else:
            raise ValueError(f"Unknown ingestion strategy: {strategy}")