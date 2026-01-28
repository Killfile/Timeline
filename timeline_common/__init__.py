"""
Timeline Common Utilities

Shared utilities module for Timeline project, providing:
- Event key computation (deterministic SHA-256 hashing for event deduplication)
- Common domain models and helpers across api/ and wikipedia-ingestion/

This module serves as a shared dependency layer, resolving circular import
issues between api/ and wikipedia-ingestion/.
"""

from timeline_common.event_key import (
    compute_event_key,
    compute_event_key_from_dict,
    validate_event_key,
)

__all__ = [
    "compute_event_key",
    "compute_event_key_from_dict",
    "validate_event_key",
]
