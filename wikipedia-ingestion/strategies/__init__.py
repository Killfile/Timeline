"""Wikipedia ingestion strategies package.

This package contains all the ingestion strategies for extracting timeline events
from various Wikipedia pages and sources.
"""

from .bespoke_events_strategy import BespokeEventsStrategy
from .list_of_time_periods import ListOfTimePeriodsStrategy
from .list_of_years import ListOfYearsStrategy

__all__ = [
    "BespokeEventsStrategy",
    "ListOfTimePeriodsStrategy",
    "ListOfYearsStrategy",
]