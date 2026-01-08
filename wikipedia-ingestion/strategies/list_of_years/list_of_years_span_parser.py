"""Compatibility shim that re-exports the central years parse orchestrator.

Historically code imported this module from `strategies.list_of_years`.
We keep a thin shim to avoid breaking existing imports while the real
implementation lives under `span_parsing.orchestrators`.
"""

from span_parsing.orchestrators.years_parse_orchestrator import YearsParseOrchestrator
from span_parsing.span import Span

__all__ = ["YearsParseOrchestrator", "Span"]
