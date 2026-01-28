"""
Event Key Computation Utility (Backward Compatibility Wrapper)

DEPRECATED: This module re-exports from timeline_common.event_key.

This wrapper maintains backward compatibility with existing code that imports
from api.event_key. New code should import directly from timeline_common:

    from timeline_common.event_key import compute_event_key

The actual implementation has been moved to timeline_common to resolve circular
dependencies between the api/ and wikipedia-ingestion/ services.

Provides deterministic event key generation for associating enrichment data
with historical events across reimports.

The event_key is a SHA-256 hash of stable event fields (title, dates, description),
allowing second-order enrichment data to persist even when the historical_events
table is dropped and reimported.
"""

# Re-export all public functions from timeline_common
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
