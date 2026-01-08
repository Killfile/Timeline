"""List of Time Periods strategy components package.

This package contains all components related to parsing Wikipedia's
"List of time periods" page, including the main strategy.
"""

from .list_of_time_periods_strategy import ListOfTimePeriodsStrategy
from span_parsing.orchestrators.time_period_parse_orchestrator import TimePeriodParseOrchestrator

__all__ = [
    "ListOfTimePeriodsStrategy",
    "TimePeriodParseOrchestrator",
]