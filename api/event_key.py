"""
Event Key Computation Utility

Provides deterministic event key generation for associating enrichment data
with historical events across reimports.

The event_key is a SHA-256 hash of stable event fields (title, dates, description),
allowing second-order enrichment data to persist even when the historical_events
table is dropped and reimported.

Usage:
    from event_key import compute_event_key
    
    key = compute_event_key(
        title="Battle of Hastings",
        start_year=1066,
        end_year=1066,
        description="William the Conqueror defeats Harold II..."
    )
"""

import hashlib
from typing import Optional


def compute_event_key(
    title: str,
    start_year: int,
    end_year: int,
    description: Optional[str] = None
) -> str:
    """
    Compute a deterministic event key for enrichment association.
    
    The key is a SHA-256 hash of the event's stable identifying fields.
    This allows enrichment data to survive reimports as long as the
    event content remains unchanged.
    
    Args:
        title: Event title (required, must not be empty)
        start_year: Event start year (required)
        end_year: Event end year (required)
        description: Event description (optional, defaults to empty string)
    
    Returns:
        64-character hexadecimal SHA-256 hash string
    
    Raises:
        ValueError: If title is empty or None
    
    Examples:
        >>> compute_event_key("Battle of Hastings", 1066, 1066, "Norman conquest")
        'a1b2c3d4...'
        
        >>> compute_event_key("World War II", 1939, 1945, None)
        'e5f6g7h8...'
    """
    if not title or not title.strip():
        raise ValueError("Event title must not be empty")
    
    # Normalize inputs
    title = title.strip()
    description = (description or "").strip()
    
    # Create deterministic key source
    # Use | as delimiter (unlikely to appear in actual content)
    key_source = f"{title}|{start_year}|{end_year}|{description}"
    
    # Compute SHA-256 hash
    return hashlib.sha256(key_source.encode("utf-8")).hexdigest()


def compute_event_key_from_dict(event: dict) -> str:
    """
    Compute event key from an event dictionary.
    
    Convenience wrapper for compute_event_key that extracts fields
    from a dictionary (e.g., from database row or API response).
    
    Args:
        event: Dictionary containing at minimum:
            - title (str)
            - start_year (int)
            - end_year (int)
            - description (str, optional)
    
    Returns:
        64-character hexadecimal SHA-256 hash string
    
    Raises:
        KeyError: If required fields are missing
        ValueError: If title is empty
    
    Examples:
        >>> event = {
        ...     'title': 'Moon Landing',
        ...     'start_year': 1969,
        ...     'end_year': 1969,
        ...     'description': 'Apollo 11 lands on the moon'
        ... }
        >>> compute_event_key_from_dict(event)
        'x9y8z7...'
    """
    return compute_event_key(
        title=event['title'],
        start_year=event['start_year'],
        end_year=event['end_year'],
        description=event.get('description')
    )


def validate_event_key(event_key: str) -> bool:
    """
    Validate that a string is a valid event key format.
    
    Event keys must be 64-character hexadecimal strings (SHA-256 output).
    
    Args:
        event_key: String to validate
    
    Returns:
        True if valid, False otherwise
    
    Examples:
        >>> validate_event_key('a' * 64)
        True
        
        >>> validate_event_key('invalid')
        False
    """
    if not isinstance(event_key, str):
        return False
    
    if len(event_key) != 64:
        return False
    
    try:
        int(event_key, 16)
        return True
    except ValueError:
        return False
