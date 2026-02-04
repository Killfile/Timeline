"""Client detection utilities for monitoring and logging.

Provides user-agent parsing and classification for observability purposes.
Does not block any requests - only used for metrics and monitoring.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ClientInfo:
    """Information about the client making the request."""
    user_agent: str
    is_likely_browser: bool
    browser_name: Optional[str]
    client_type: str  # 'browser', 'cli', 'bot', 'unknown'
    confidence: float  # 0.0-1.0
    details: str  # Human-readable description


# Common browser user-agent patterns
# Order matters: more specific patterns first (Edge, Opera before Chrome)
_BROWSER_PATTERNS = [
    (r"mozilla/5\.0.*edg/[\d.]+", "Edge"),
    (r"mozilla/5\.0.*(opr|opera)/[\d.]+", "Opera"),
    (r"mozilla/5\.0.*chrome/[\d.]+", "Chrome"),
    (r"mozilla/5\.0.*firefox/[\d.]+", "Firefox"),
    (r"mozilla/5\.0.*safari/[\d.]+", "Safari"),
]

# Non-browser client patterns
_CLI_PATTERNS = [
    "curl",
    "wget",
    "httpie",
    "python-requests",
    "python-urllib",
    "postman",
    "insomnia",
]

_BOT_PATTERNS = [
    "bot",
    "crawler",
    "spider",
    "scraper",
    "slurp",
]


def parse_user_agent(user_agent: str) -> ClientInfo:
    """Parse user-agent string and classify the client.
    
    Args:
        user_agent: The User-Agent header value
        
    Returns:
        ClientInfo with classification and confidence score
    """
    if not user_agent:
        return ClientInfo(
            user_agent="",
            is_likely_browser=False,
            browser_name=None,
            client_type="unknown",
            confidence=0.0,
            details="No user-agent provided"
        )
    
    ua_lower = user_agent.lower()
    
    # Check for obvious CLI tools
    for cli_pattern in _CLI_PATTERNS:
        if cli_pattern in ua_lower:
            # Find the actual string in the original user-agent (preserves case)
            start_idx = ua_lower.index(cli_pattern)
            actual_name = user_agent[start_idx:start_idx + len(cli_pattern)]
            return ClientInfo(
                user_agent=user_agent,
                is_likely_browser=False,
                browser_name=None,
                client_type="cli",
                confidence=0.95,
                details=f"CLI tool: {actual_name}"
            )
    
    # Check for bots
    for bot_pattern in _BOT_PATTERNS:
        if bot_pattern in ua_lower:
            # Find the actual string in the original user-agent (preserves case)
            start_idx = ua_lower.index(bot_pattern)
            actual_name = user_agent[start_idx:start_idx + len(bot_pattern)]
            return ClientInfo(
                user_agent=user_agent,
                is_likely_browser=False,
                browser_name=None,
                client_type="bot",
                confidence=0.95,
                details=f"Bot/crawler: {actual_name}"
            )
    
    # Check for browsers
    for pattern, browser_name in _BROWSER_PATTERNS:
        if re.search(pattern, ua_lower):
            return ClientInfo(
                user_agent=user_agent,
                is_likely_browser=True,
                browser_name=browser_name,
                client_type="browser",
                confidence=0.9,
                details=f"Browser: {browser_name}"
            )
    
    # Heuristic: If it contains "Mozilla" but doesn't match known browsers,
    # it might be a browser we don't recognize or a bot pretending
    if "mozilla" in ua_lower:
        return ClientInfo(
            user_agent=user_agent,
            is_likely_browser=True,
            browser_name="Unknown Browser",
            client_type="browser",
            confidence=0.5,
            details="Unknown Mozilla-based client"
        )
    
    # Unknown client type
    return ClientInfo(
        user_agent=user_agent,
        is_likely_browser=False,
        browser_name=None,
        client_type="unknown",
        confidence=0.3,
        details="Unknown user-agent"
    )


def get_client_summary(client_info: ClientInfo) -> dict:
    """Get a dictionary summary of client info for logging.
    
    Args:
        client_info: The ClientInfo object to summarize
        
    Returns:
        Dictionary with client classification info
    """
    return {
        "client_type": client_info.client_type,
        "is_browser": client_info.is_likely_browser,
        "browser": client_info.browser_name,
        "confidence": client_info.confidence,
        "details": client_info.details,
        "user_agent_preview": client_info.user_agent[:80] if client_info.user_agent else ""
    }
