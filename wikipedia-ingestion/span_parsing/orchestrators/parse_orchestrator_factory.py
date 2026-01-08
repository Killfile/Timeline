from enum import Enum, auto
from span_parsing.orchestrators.parse_orchestrator import ParseOrchestrator
from span_parsing.orchestrators.years_parse_orchestrator import YearsParseOrchestrator
from span_parsing.orchestrators.time_period_parse_orchestrator import TimePeriodParseOrchestrator

class ParseOrchestratorTypes(Enum):
    YEARS = auto()
    TIME_PERIODS = auto()

class ParseOrchestratorFactory:
    """Factory for creating parse orchestrators based on strategy type."""

    @staticmethod
    def get_orchestrator(strategy_type: ParseOrchestratorTypes) -> ParseOrchestrator:
        """Get the appropriate parse orchestrator for the given strategy type.

        Args:
            strategy_type (str): The type of strategy (e.g., "list_of_years", "list_of_time_periods").

        Returns:
            ParseOrchestrator: An instance of the corresponding parse orchestrator.

        Raises:
            ValueError: If the strategy type is not recognized.
        """
        if strategy_type == ParseOrchestratorTypes.YEARS:
            return YearsParseOrchestrator()
        elif strategy_type == ParseOrchestratorTypes.TIME_PERIODS:
            return TimePeriodParseOrchestrator()
        else:
            raise ValueError(f"Unknown orchestrator type: {strategy_type}")