"""List of Years strategy components package.

This package contains all components related to parsing Wikipedia's
"List of years" page, including the main strategy and span parser.
"""

from .list_of_years_strategy import ListOfYearsStrategy
from span_parsing.orchestrators.years_parse_orchestrator import YearsParseOrchestrator

__all__ = [
    "ListOfYearsStrategy",
    "YearsParseOrchestrator",
]