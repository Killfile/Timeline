import os
import logging
from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Any, Dict
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel

from auth.auth_dependency import build_auth_dependency
from auth.client_detection import parse_user_agent, get_client_summary
from auth.config import AuthConfig, load_auth_config
from auth.jwt_service import generate_token
from auth.rate_limiter import RateLimiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'database'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'timeline_history'),
    'user': os.getenv('DB_USER', 'timeline_user'),
    'password': os.getenv('DB_PASSWORD', 'timeline_pass')
}

# CORS configuration
CORS_ORIGINS = [
    origin.strip() for origin in os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:3000,http://127.0.0.1:3000'
    ).split(',')
]

# Create FastAPI app
app = FastAPI(
    title="Historical Timeline API",
    description="API for accessing Wikipedia-based historical events",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

_token_rate_limiter: RateLimiter | None = None
_auth_dependency = build_auth_dependency()


def _reset_token_rate_limiter() -> None:
    """Reset the global rate limiter. For testing only."""
    global _token_rate_limiter
    _token_rate_limiter = None


def _get_token_rate_limiter(config: AuthConfig) -> RateLimiter:
    global _token_rate_limiter
    if _token_rate_limiter is None:
        _token_rate_limiter = RateLimiter(
            limit_per_minute=config.rate_limit_per_minute,
            burst=config.rate_limit_burst,
        )
    return _token_rate_limiter


# Pydantic models
class CategoryEnrichment(BaseModel):
    category: str
    llm_source: Optional[str] = None  # NULL for Wikipedia, model name for LLM
    confidence: Optional[float] = None  # NULL for Wikipedia, 0.0-1.0 for LLM


class HistoricalEvent(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    start_year: Optional[int] = None
    start_month: Optional[int] = None
    start_day: Optional[int] = None
    end_year: Optional[int] = None
    end_month: Optional[int] = None
    end_day: Optional[int] = None
    is_bc_start: bool = False
    is_bc_end: bool = False
    weight: Optional[int] = None
    precision: Optional[float] = None
    category: Optional[str] = None  # Legacy Wikipedia category (kept for compatibility)
    categories: List[CategoryEnrichment] = []  # New: All categories (Wikipedia + LLM)
    wikipedia_url: Optional[str] = None
    display_year: Optional[str] = None
    bin_num: Optional[int] = None  # For 15-bin system (0-14)
    extraction_method: Optional[str] = None  # How the date was extracted
    extract_snippet: Optional[str] = None  # Text snippet used for extraction
    span_match_notes: Optional[str] = None  # Notes about span matching
    match_type: Optional[str] = None  # Normalized match type (mirrors span_match_notes when available)
    strategy: Optional[str] = None  # Ingestion strategy that generated this event


class TimelineStats(BaseModel):
    total_events: int
    earliest_year: Optional[int] = None
    latest_year: Optional[int] = None
    categories: List[str] = []


@app.middleware("http")
async def enforce_authentication(request: Request, call_next):
    # Allow CORS preflight requests
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # Skip authentication for /token and /logout endpoints
    if request.url.path in ("/token", "/logout"):
        return await call_next(request)
    
    # Enforce authentication on all other endpoints
    try:
        _auth_dependency(request)
    except HTTPException as exc:
        from fastapi.responses import JSONResponse
        response = JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
        # Manually add CORS headers since we're bypassing call_next
        origin = request.headers.get("origin")
        if origin in CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    
    return await call_next(request)


class ExtractionDebug(BaseModel):
    """Observability payload for how an event's date was extracted."""

    historical_event_id: int
    extraction_method: str
    extracted_year_matches: Optional[Any] = None
    chosen_start_year: Optional[int] = None
    chosen_start_month: Optional[int] = None
    chosen_start_day: Optional[int] = None
    chosen_is_bc_start: bool = False
    chosen_end_year: Optional[int] = None
    chosen_end_month: Optional[int] = None
    chosen_end_day: Optional[int] = None
    chosen_is_bc_end: bool = False
    chosen_weight_days: Optional[int] = None
    chosen_precision: Optional[float] = None
    extract_snippet: Optional[str] = None
    pageid: Optional[int] = None
    title: Optional[str] = None
    category: Optional[str] = None
    wikipedia_url: Optional[str] = None
    created_at: Optional[datetime] = None
    span_match_notes: Optional[str] = None

    # Convenience echo from historical_events (so UI has a stable place to read it)
    event_weight: Optional[int] = None


# Database connection helper
def get_db_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except psycopg2.OperationalError as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


def format_year_display(year: Optional[int], is_bc: bool) -> Optional[str]:
    """Format year for display."""
    if year is None:
        return None
    if is_bc:
        return f"{year} BC"
    else:
        return f"{year} AD"


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "Historical Timeline API",
        "version": "1.0.0",
        "description": "Wikipedia-based historical events timeline",
        "endpoints": {
            "events": "/events",
            "event_by_id": "/events/{id}",
            "stats": "/stats",
            "categories": "/categories",
            "search": "/search",
            "health": "/health"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.post("/token")
def issue_token(request: Request, response: Response) -> Dict[str, Any]:
    """Issue a JWT token via HttpOnly cookie for all clients.
    
    Sets a secure, HttpOnly cookie containing the JWT.
    No client secret required - rate limiting provides abuse protection.
    """
    try:
        config = load_auth_config()
    except ValueError as exc:
        logger.error("Failed to load auth config", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "")
    
    # Parse user-agent for monitoring/logging
    client_info = parse_user_agent(user_agent)
    client_summary = get_client_summary(client_info)
    
    # Rate limiting
    limiter = _get_token_rate_limiter(config)
    if not limiter.allow(client_ip):
        logger.warning(
            "Token issuance rate limit exceeded",
            extra={
                "client_ip": client_ip,
                "client_type": client_summary["client_type"],
                "status_code": 429,
            }
        )
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    # Generate token
    token_payload = generate_token(config)
    
    # Set cookie with JWT
    response.set_cookie(
        key=config.cookie_name,
        value=token_payload.token,
        max_age=token_payload.expires_in,
        httponly=True,
        secure=config.cookie_secure,
        samesite=config.cookie_samesite,
        domain=config.cookie_domain,
    )
    
    logger.info(
        "Token issued successfully via cookie",
        extra={
            "client_ip": client_ip,
            "client_type": client_summary["client_type"],
            "browser": client_summary["browser"],
            "confidence": client_summary["confidence"],
            "token_id": token_payload.token_id[:8] + "...",  # Only log prefix
            "expires_in": token_payload.expires_in,
            "status_code": 200,
        }
    )
    
    return {
        "status": "success",
        "message": "Authentication token set in cookie",
        "expires_in": token_payload.expires_in,
    }


@app.post("/logout")
def logout(request: Request, response: Response) -> Dict[str, str]:
    """Clear the authentication cookie to log out.
    
    Returns a success message after clearing the cookie.
    """
    try:
        config = load_auth_config()
    except ValueError as exc:
        logger.error("Failed to load auth config", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    
    client_ip = request.client.host if request.client else "unknown"
    
    # Clear the cookie by setting max_age=0
    response.set_cookie(
        key=config.cookie_name,
        value="",
        max_age=0,
        httponly=True,
        secure=config.cookie_secure,
        samesite=config.cookie_samesite,
        domain=config.cookie_domain,
    )
    
    logger.info(
        "User logged out successfully",
        extra={
            "client_ip": client_ip,
            "status_code": 200,
        }
    )
    
    return {
        "status": "success",
        "message": "Logged out successfully",
    }


def fetch_event_enrichments(conn, event_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    """Fetch enrichment categories for a list of event IDs.
    
    Args:
        conn: Database connection
        event_ids: List of event IDs
        
    Returns:
        Dictionary mapping event_id to list of category enrichments
    """
    if not event_ids:
        return {}
    
    cursor = conn.cursor()
    try:
        # Get event_key to id mapping, plus legacy Wikipedia category
        placeholders = ','.join(['%s'] * len(event_ids))
        cursor.execute(
            f"SELECT id, event_key, category FROM historical_events WHERE id IN ({placeholders})",
            event_ids
        )
        event_info = {row['id']: {'event_key': row['event_key'], 'category': row['category']} for row in cursor.fetchall()}
        
        # Get all enrichment categories for these event_keys
        event_keys = [info['event_key'] for info in event_info.values()]
        if not event_keys:
            return {}
        
        placeholders = ','.join(['%s'] * len(event_keys))
        cursor.execute(
            f"""
            SELECT event_key, category, llm_source, confidence
            FROM event_categories
            WHERE event_key IN ({placeholders})
            ORDER BY event_key, 
                     CASE WHEN llm_source IS NULL THEN 1 ELSE 0 END,  -- LLM first (prioritize AI)
                     confidence DESC NULLS LAST
            """,
            event_keys
        )
        
        # Group by event_id
        enrichments_by_id = {}
        for row in cursor.fetchall():
            event_key = row['event_key']
            # Find the event_id for this event_key
            event_id = next((eid for eid, info in event_info.items() if info['event_key'] == event_key), None)
            if event_id:
                if event_id not in enrichments_by_id:
                    enrichments_by_id[event_id] = []
                enrichments_by_id[event_id].append({
                    'category': row['category'],
                    'llm_source': row['llm_source'],
                    'confidence': row['confidence']
                })
        
        # Add legacy Wikipedia categories if not already present in enrichments
        for event_id, info in event_info.items():
            wiki_category = info['category']
            if wiki_category:
                # Check if this category is already in enrichments (from event_categories table)
                existing_categories = enrichments_by_id.get(event_id, [])
                has_wiki_category = any(
                    c['category'] == wiki_category and c['llm_source'] is None 
                    for c in existing_categories
                )
                
                if not has_wiki_category:
                    # Add the legacy Wikipedia category at the end (LLM categories come first)
                    if event_id not in enrichments_by_id:
                        enrichments_by_id[event_id] = []
                    enrichments_by_id[event_id].append({
                        'category': wiki_category,
                        'llm_source': None,
                        'confidence': None
                    })
        
        return enrichments_by_id
    finally:
        cursor.close()


def fetch_extraction_debug(conn, event_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """Fetch extraction debug information for a list of event IDs.
    
    Args:
        conn: Database connection
        event_ids: List of event IDs
        
    Returns:
        Dictionary mapping event_id to extraction debug info
    """
    if not event_ids:
        return {}
    
    cursor = conn.cursor()
    try:
        placeholders = ','.join(['%s'] * len(event_ids))
        cursor.execute(
            f"""
            SELECT historical_event_id, extraction_method, extract_snippet, span_match_notes
            FROM event_date_extraction_debug 
            WHERE historical_event_id IN ({placeholders})
            """,
            event_ids
        )
        
        debug_by_id = {}
        for row in cursor.fetchall():
            debug_by_id[row['historical_event_id']] = {
                'extraction_method': row['extraction_method'],
                'extract_snippet': row['extract_snippet'],
                'span_match_notes': row['span_match_notes']
            }
        
        return debug_by_id
    finally:
        cursor.close()


@app.get("/events", response_model=List[HistoricalEvent])
def get_events(
    start_year: Optional[int] = Query(None, description="Filter events starting from this year"),
    end_year: Optional[int] = Query(None, description="Filter events up to this year"),
    category: Optional[List[str]] = Query(None, description="Filter by categories (can specify multiple)"),
    strategy: Optional[List[str]] = Query(None, description="Filter by strategies (can specify multiple)"),
    viewport_start: Optional[int] = Query(None, description="Viewport start year (for weight-based filtering)"),
    viewport_end: Optional[int] = Query(None, description="Viewport end year (for weight-based filtering)"),
    viewport_is_bc_start: Optional[bool] = Query(None, description="Whether viewport_start is BC"),
    viewport_is_bc_end: Optional[bool] = Query(None, description="Whether viewport_end is BC"),
    limit: int = Query(100, ge=1, le=1000, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get historical events with optional filters.
    
    When viewport params are provided, this endpoint:
    1. Pads viewport by 25% on each side
    2. Filters to events that overlap the padded range
    3. Orders by weight DESC
    4. Returns top `limit` highest-weight events in viewport
    
    The category parameter can be specified multiple times to filter by multiple categories.
    The strategy parameter can be specified multiple times to filter by multiple strategies.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # If viewport is specified, compute padded range and filter by weight.
        use_viewport_mode = (
            viewport_start is not None
            and viewport_end is not None
            and viewport_is_bc_start is not None
            and viewport_is_bc_end is not None
        )

        if use_viewport_mode:
            # Convert BC years to negative for arithmetic.
            vs = -viewport_start if viewport_is_bc_start else viewport_start
            ve = -viewport_end if viewport_is_bc_end else viewport_end
            vmin, vmax = min(vs, ve), max(vs, ve)
            span = max(1, vmax - vmin)
            padding = span * 0.25
            padded_min = vmin - padding
            padded_max = vmax + padding

            # Strategy: Spatially-balanced binned selection WITH priority for viewport-center events
            # Divide viewport into bins, get top events from each bin by weight,
            # but prioritize events that are actually IN the viewport over padded areas.
            # This ensures we show WWI/WWII events in 1915-1945, not just high-weight pre-1915 events.
            
            num_bins = 10
            events_per_bin = max(10, limit // num_bins + 20)  # Get extra per bin to fill gaps
            
            # Create bins ONLY in the actual viewport, not the padded area
            # This ensures we prioritize events actually in view
            bin_span = vmax - vmin
            
            # Filter out events with unreasonably large spans (likely data errors or overly broad events)
            # Events with spans > 3x the viewport are likely not useful to show
            # For example, in a 30-year viewport (1915-1945), we don't want to show events spanning 190 years
            max_reasonable_span = span * 3
            
            query_parts = []
            params = []
            
            for i in range(num_bins):
                bin_start = vmin + bin_span * i / num_bins
                bin_end = vmin + bin_span * (i + 1) / num_bins
                
                # Event overlaps bin if: event_start <= bin_end AND event_end >= bin_start
                subquery = """
                    (SELECT id, title, description, start_year, start_month, start_day,
                            end_year, end_month, end_day,
                            is_bc_start, is_bc_end, weight, precision, category, wikipedia_url,
                            s.name as strategy,
                            %s as bin_num,
                            ROW_NUMBER() OVER (ORDER BY weight DESC, id) as rank_in_bin
                     FROM historical_events he
                     LEFT JOIN strategies s ON he.strategy_id = s.id
                     WHERE weight IS NOT NULL
                       AND start_year IS NOT NULL
                       AND end_year IS NOT NULL
                       AND to_fractional_year(start_year, is_bc_start, start_month, start_day) <= %s
                       AND to_fractional_year(end_year, is_bc_end, end_month, end_day) >= %s
                       AND ABS(to_fractional_year(end_year, is_bc_end, end_month, end_day) - 
                               to_fractional_year(start_year, is_bc_start, start_month, start_day)) <= %s
                """
                params.extend([i, bin_end, bin_start, max_reasonable_span])
                
                # Handle multiple categories - check both legacy field and enrichments
                if category and len(category) > 0:
                    placeholders = ','.join(['%s'] * len(category))
                    # Check if event has the category in either legacy field OR enrichment table
                    subquery += f"""
                       AND (category IN ({placeholders})
                            OR event_key IN (
                                SELECT event_key FROM event_categories 
                                WHERE category IN ({placeholders})
                            ))
                    """
                    # Double the params since we use the category list twice
                    params.extend(category)
                    params.extend(category)
                
                # Handle multiple strategies
                if strategy and len(strategy) > 0:
                    placeholders = ','.join(['%s'] * len(strategy))
                    subquery += f" AND s.name IN ({placeholders})"
                    params.extend(strategy)
                
                subquery += " ORDER BY weight DESC, id LIMIT %s)"
                params.append(events_per_bin)
                
                query_parts.append(subquery)
            
            # Union all bins, then use ROW_NUMBER to interleave events from different bins
            # This ensures we get a balanced sample across the timeline
            # Use DISTINCT ON to deduplicate events that span multiple bins
            query = " UNION ALL ".join(query_parts)
            query = f"""
                SELECT DISTINCT ON (id) id, title, description, start_year, start_month, start_day,
                       end_year, end_month, end_day,
                       is_bc_start, is_bc_end, weight, precision, category, wikipedia_url, strategy
                FROM ({query}) AS all_bins
                ORDER BY id, rank_in_bin, bin_num
                LIMIT %s
            """
            params.append(limit)

        else:
            # Legacy mode: no viewport, just filter by start/end year and category.
            query = """
                SELECT he.id, he.title, he.description, he.start_year, he.start_month, he.start_day,
                       he.end_year, he.end_month, he.end_day,
                       he.is_bc_start, he.is_bc_end, he.weight, he.precision, he.category, he.wikipedia_url, s.name as strategy
                FROM historical_events he
                LEFT JOIN strategies s ON he.strategy_id = s.id
                WHERE 1=1
            """
            params = []
            
            if start_year is not None:
                query += " AND start_year >= %s"
                params.append(start_year)
            
            if end_year is not None:
                query += " AND (end_year <= %s OR end_year IS NULL)"
                params.append(end_year)
            
            # Handle multiple categories - check both legacy field and enrichments
            if category and len(category) > 0:
                placeholders = ','.join(['%s'] * len(category))
                # Check if event has the category in either legacy field OR enrichment table
                query += f"""
                   AND (category IN ({placeholders})
                        OR event_key IN (
                            SELECT event_key FROM event_categories 
                            WHERE category IN ({placeholders})
                        ))
                """
                # Double the params since we use the category list twice
                params.extend(category)
                params.extend(category)
            
            # Handle multiple strategies
            if strategy and len(strategy) > 0:
                placeholders = ','.join(['%s'] * len(strategy))
                query += f" AND s.name IN ({placeholders})"
                params.extend(strategy)
            
            query += " ORDER BY start_year ASC NULLS LAST, end_year ASC NULLS LAST"
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])
        
        cursor.execute(query, params)
        events = cursor.fetchall()
        
        # Fetch enrichment categories for all events
        event_ids = [event['id'] for event in events]
        enrichments = fetch_event_enrichments(conn, event_ids)
        extraction_debug = fetch_extraction_debug(conn, event_ids)
        
        # Add display year, enrichment categories, and extraction debug to each event
        for event in events:
            if event['start_year']:
                event['display_year'] = format_year_display(event['start_year'], event['is_bc_start'])
            
            # Add enrichment categories
            event['categories'] = enrichments.get(event['id'], [])
            
            # Add extraction debug info
            debug_info = extraction_debug.get(event['id'], {})
            event['extraction_method'] = debug_info.get('extraction_method')
            event['extract_snippet'] = debug_info.get('extract_snippet')
            event['span_match_notes'] = debug_info.get('span_match_notes')
            # Expose match_type for frontend debug/modal convenience.
            # Many ingestion parsers populate match_type into span_match_notes,
            # so mirror it to a dedicated field for UI access.
            event['match_type'] = debug_info.get('span_match_notes')
        
        return events
    
    finally:
        cursor.close()
        conn.close()


@app.get("/events/bins", response_model=List[HistoricalEvent])
def get_events_by_bins(
    viewport_center: float = Query(..., description="Center of viewport (fractional year, negative for BC)"),
    viewport_span: float = Query(..., description="Span of viewport in years"),
    zone: str = Query(..., description="Which zone to load: 'left', 'center', or 'right'"),
    category: Optional[List[str]] = Query(None, description="Filter by categories (can specify multiple)"),
    strategy: Optional[List[str]] = Query(None, description="Filter by strategies (can specify multiple)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of events to return per bin")
):
    """
    Load events for a 5-bin zone in the 15-bin timeline system.
    
    The 15-bin system divides the timeline into:
    - Left buffer: bins 0-4 (earlier than viewport)
    - Center viewport: bins 5-9 (visible)
    - Right buffer: bins 10-14 (later than viewport)
    
    Each bin covers viewport_span / 5 years.
    
    Args:
        viewport_center: Center point of the visible viewport (negative for BC years)
        viewport_span: Width of the visible viewport in years
        zone: Which 5-bin zone to load ('left', 'center', or 'right')
        category: Optional list of categories to filter by
        strategy: Optional list of strategies to filter by
        limit: Max events per bin
    
    Returns:
        List of events with bin metadata, ordered by weight within each bin
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Calculate bin boundaries
        bin_width = viewport_span / 5
        
        # Define zone boundaries relative to viewport center
        if zone == 'left':
            # Bins 0-4: left buffer (earlier than viewport)
            zone_start = viewport_center - viewport_span * 1.5  # 1.5 viewports before center
            zone_end = viewport_center - viewport_span * 0.5    # 0.5 viewports before center
            bin_offset = 0
        elif zone == 'center':
            # Bins 5-9: center viewport (visible)
            zone_start = viewport_center - viewport_span * 0.5  # 0.5 viewports before center
            zone_end = viewport_center + viewport_span * 0.5    # 0.5 viewports after center
            bin_offset = 5
        elif zone == 'right':
            # Bins 10-14: right buffer (later than viewport)
            zone_start = viewport_center + viewport_span * 0.5  # 0.5 viewports after center
            zone_end = viewport_center + viewport_span * 1.5    # 1.5 viewports after center
            bin_offset = 10
        else:
            raise HTTPException(status_code=400, detail=f"Invalid zone: {zone}. Must be 'left', 'center', or 'right'")
        
        # Create 5 bins for this zone
        query_parts = []
        params = []
        
        for i in range(5):
            bin_num = bin_offset + i
            bin_start = zone_start + (i * bin_width)
            bin_end = zone_start + ((i + 1) * bin_width)
            
            # Event overlaps bin if: event_start <= bin_end AND event_end >= bin_start
            # Filter out events with weight > 2x viewport_span (too long for current zoom level)
            max_weight = viewport_span * 2 * 365
            subquery = """
                (SELECT he.id, he.title, he.description, he.start_year, he.start_month, he.start_day,
                        he.end_year, he.end_month, he.end_day,
                        he.is_bc_start, he.is_bc_end, he.weight, he.precision, he.category, he.wikipedia_url,
                        s.name as strategy,
                        %s as bin_num,
                        ROW_NUMBER() OVER (ORDER BY he.weight DESC, he.id) as rank_in_bin
                 FROM historical_events he
                 LEFT JOIN strategies s ON he.strategy_id = s.id
                 WHERE he.weight IS NOT NULL
                   AND he.start_year IS NOT NULL
                   AND he.end_year IS NOT NULL
                   AND he.weight <= %s
                   AND to_fractional_year(he.start_year, he.is_bc_start, he.start_month, he.start_day) <= %s
                   AND to_fractional_year(he.end_year, he.is_bc_end, he.end_month, he.end_day) >= %s
            """
            params.extend([bin_num, max_weight, bin_end, bin_start])
            
            print(f"Max weight for bin {bin_num}: {max_weight}")
            # Handle multiple categories
            if category and len(category) > 0:
                placeholders = ','.join(['%s'] * len(category))
                subquery += f"""
                   AND (he.category IN ({placeholders})
                        OR he.event_key IN (
                            SELECT event_key FROM event_categories 
                            WHERE category IN ({placeholders})
                        ))
                """
                params.extend(category)
                params.extend(category)
            
            # Handle multiple strategies
            if strategy and len(strategy) > 0:
                placeholders = ','.join(['%s'] * len(strategy))
                subquery += f" AND s.name IN ({placeholders})"
                params.extend(strategy)
            
            subquery += " ORDER BY he.weight DESC, he.id LIMIT %s)"
            params.append(limit)
            
            query_parts.append(subquery)
        
        # Union all bins
        query = " UNION ALL ".join(query_parts)
        query = f"""
            SELECT id, title, description, start_year, start_month, start_day,
                   end_year, end_month, end_day,
                   is_bc_start, is_bc_end, weight, precision, category, wikipedia_url, strategy, bin_num
            FROM ({query}) AS zone_bins
            ORDER BY bin_num, rank_in_bin
        """
        
        cursor.execute(query, params)
        events = cursor.fetchall()
        
        # Fetch enrichment categories
        event_ids = [event['id'] for event in events]
        enrichments = fetch_event_enrichments(conn, event_ids)
        extraction_debug = fetch_extraction_debug(conn, event_ids)
        
        # Add display year, enrichments, and extraction debug
        for event in events:
            if event['start_year']:
                event['display_year'] = format_year_display(event['start_year'], event['is_bc_start'])
            event['categories'] = enrichments.get(event['id'], [])
            
            # Add extraction debug info
            debug_info = extraction_debug.get(event['id'], {})
            event['extraction_method'] = debug_info.get('extraction_method')
            event['extract_snippet'] = debug_info.get('extract_snippet')
            event['span_match_notes'] = debug_info.get('span_match_notes')
            event['match_type'] = debug_info.get('span_match_notes')
        
        return events
    
    finally:
        cursor.close()
        conn.close()


@app.get("/events/count")
def get_events_count(
    start_year: Optional[int] = Query(None, description="Filter events starting from this year"),
    end_year: Optional[int] = Query(None, description="Filter events up to this year"),
    category: Optional[List[str]] = Query(None, description="Filter by categories (can specify multiple)"),
    viewport_start: Optional[int] = Query(None, description="Viewport start year"),
    viewport_end: Optional[int] = Query(None, description="Viewport end year"),
    viewport_is_bc_start: Optional[bool] = Query(None, description="Whether viewport_start is BC"),
    viewport_is_bc_end: Optional[bool] = Query(None, description="Whether viewport_end is BC"),
):
    """Get count of events matching filters. Used to populate 'Events in Scope' stat.
    
    When viewport params are provided, this returns the total count of events
    that fall within the viewport range (without limit).
    
    The category parameter can be specified multiple times to filter by multiple categories.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Build count query
        query = "SELECT COUNT(*) as count FROM historical_events WHERE 1=1"
        params = []
        
        # If viewport is specified, filter to events overlapping viewport
        use_viewport_mode = (
            viewport_start is not None
            and viewport_end is not None
            and viewport_is_bc_start is not None
            and viewport_is_bc_end is not None
        )
        
        if use_viewport_mode:
            # Convert viewport bounds to numeric years (negative for BC)
            vs = -viewport_start if viewport_is_bc_start else viewport_start
            ve = -viewport_end if viewport_is_bc_end else viewport_end
            
            # Ensure vs < ve
            if vs > ve:
                vs, ve = ve, vs
            
            # Filter: event overlaps viewport if event_end >= viewport_start AND event_start <= viewport_end
            # Using numeric representation: negative for BC, positive for AD
            query += """ AND (
                CASE WHEN is_bc_end THEN -end_year ELSE end_year END >= %s
                OR (end_year IS NULL AND CASE WHEN is_bc_start THEN -start_year ELSE start_year END >= %s)
            ) AND (
                CASE WHEN is_bc_start THEN -start_year ELSE start_year END <= %s
            )"""
            params.extend([vs, vs, ve])
        else:
            # Use simple year filters if provided
            if start_year is not None:
                query += " AND start_year >= %s"
                params.append(start_year)
            
            if end_year is not None:
                query += " AND (end_year <= %s OR end_year IS NULL)"
                params.append(end_year)
        
        # Handle multiple categories - check both legacy field and enrichments
        if category and len(category) > 0:
            placeholders = ','.join(['%s'] * len(category))
            # Check if event has the category in either legacy field OR enrichment table
            query += f"""
               AND (category IN ({placeholders})
                    OR event_key IN (
                        SELECT event_key FROM event_categories 
                        WHERE category IN ({placeholders})
                    ))
            """
            # Double the params since we use the category list twice
            params.extend(category)
            params.extend(category)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        return {"count": result['count']}
    
    finally:
        cursor.close()
        conn.close()


@app.get("/events/{event_id}", response_model=HistoricalEvent)
def get_event(event_id: int):
    """Get a specific historical event by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, title, description, start_year, start_month, start_day,
                   end_year, end_month, end_day,
                   is_bc_start, is_bc_end, weight, precision, category, wikipedia_url
            FROM historical_events 
            WHERE id = %s
        """, (event_id,))
        
        event = cursor.fetchone()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Add display year
        if event['start_year']:
            event['display_year'] = format_year_display(event['start_year'], event['is_bc_start'])
        
        # Fetch enrichment categories
        enrichments = fetch_event_enrichments(conn, [event_id])
        event['categories'] = enrichments.get(event_id, [])
        
        return event
    
    finally:
        cursor.close()
        conn.close()


@app.get("/events/{event_id}/extraction-debug", response_model=ExtractionDebug)
def get_event_extraction_debug(event_id: int):
    """Get the extraction observability record for a given event."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
         SELECT d.historical_event_id,
             d.extraction_method,
             d.extracted_year_matches,
             d.chosen_start_year,
             d.chosen_start_month,
             d.chosen_start_day,
             d.chosen_is_bc_start,
             d.chosen_end_year,
             d.chosen_end_month,
             d.chosen_end_day,
             d.chosen_is_bc_end,
             d.chosen_weight_days,
             d.chosen_precision,
             d.extract_snippet,
             d.pageid,
             d.title,
             d.category,
             d.wikipedia_url,
             d.created_at,
             d.span_match_notes,
             e.weight AS event_weight
         FROM event_date_extraction_debug d
         JOIN historical_events e ON e.id = d.historical_event_id
         WHERE d.historical_event_id = %s
         ORDER BY d.created_at DESC
         LIMIT 1
            """,
            (event_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No extraction debug record found for event")
        return row
    finally:
        cursor.close()
        conn.close()


@app.get("/stats", response_model=TimelineStats)
def get_stats():
    """Get timeline statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get total events
        cursor.execute("SELECT COUNT(*) as count FROM historical_events")
        total_events = cursor.fetchone()['count']
        
        # Get year range
        cursor.execute("""
            SELECT 
                MIN(CASE WHEN is_bc_start THEN -start_year ELSE start_year END) as earliest,
                MAX(CASE WHEN is_bc_end THEN -end_year ELSE end_year END) as latest
            FROM historical_events
            WHERE start_year IS NOT NULL
        """)
        years = cursor.fetchone()
        
        # Get categories
        cursor.execute("SELECT DISTINCT category FROM historical_events WHERE category IS NOT NULL ORDER BY category")
        categories = [row['category'] for row in cursor.fetchall()]
        
        return {
            "total_events": total_events,
            "earliest_year": years['earliest'] if years else None,
            "latest_year": years['latest'] if years else None,
            "categories": categories
        }
    
    finally:
        cursor.close()
        conn.close()


@app.get("/categories")
def get_categories():
    """Get list of all categories (both Wikipedia and LLM-enriched).
    
    Returns a combined list of categories from:
    1. Legacy Wikipedia categories (historical_events.category)
    2. Enrichment categories (event_categories table, both Wikipedia and LLM)
    
    Each category includes has_llm_enrichment flag to indicate if it has AI categorization.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all unique categories and whether they have LLM enrichment
        cursor.execute("""
            SELECT 
                category, 
                COUNT(DISTINCT event_key) as count,
                BOOL_OR(has_llm) as has_llm_enrichment
            FROM (
                -- Legacy Wikipedia categories (no LLM enrichment)
                SELECT category, event_key, false as has_llm
                FROM historical_events
                WHERE category IS NOT NULL
                
                UNION
                
                -- Enrichment categories - mark LLM ones
                SELECT ec.category, ec.event_key, (ec.llm_source IS NOT NULL) as has_llm
                FROM event_categories ec
            ) AS all_categories
            GROUP BY category
            ORDER BY count DESC, category
        """)
        categories = cursor.fetchall()
        return {"categories": categories}
    
    finally:
        cursor.close()
        conn.close()


@app.get("/strategies")
def get_strategies():
    """Get list of all strategies used for data ingestion.
    
    Returns a list of strategies with their IDs, names, and event counts.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                s.id,
                s.name,
                COUNT(he.id) as event_count
            FROM strategies s
            LEFT JOIN historical_events he ON he.strategy_id = s.id
            GROUP BY s.id, s.name
            ORDER BY event_count DESC, s.name
        """)
        strategies = cursor.fetchall()
        return {"strategies": strategies}
    
    finally:
        cursor.close()
        conn.close()


@app.get("/events/count")
def get_events_count(
    viewport_start: Optional[int] = Query(None, description="Viewport start year (absolute value)"),
    viewport_end: Optional[int] = Query(None, description="Viewport end year (absolute value)"),
    viewport_is_bc_start: Optional[bool] = Query(None, description="Whether viewport_start is BC"),
    viewport_is_bc_end: Optional[bool] = Query(None, description="Whether viewport_end is BC"),
    category: Optional[List[str]] = Query(None, description="Filter by categories (can specify multiple)"),
    strategy: Optional[List[str]] = Query(None, description="Filter by strategies (can specify multiple)")
):
    """Get count of events in a viewport with optional filters."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Convert viewport params to fractional years for range calculation
        if viewport_start is not None and viewport_end is not None and viewport_is_bc_start is not None and viewport_is_bc_end is not None:
            vs = -viewport_start if viewport_is_bc_start else viewport_start
            ve = -viewport_end if viewport_is_bc_end else viewport_end
            vmin, vmax = min(vs, ve), max(vs, ve)
            
            # Count events that overlap with the viewport
            query = """
                SELECT COUNT(DISTINCT he.id) as count
                FROM historical_events he
                LEFT JOIN strategies s ON he.strategy_id = s.id
                WHERE to_fractional_year(he.start_year, he.is_bc_start, he.start_month, he.start_day) <= %s
                  AND to_fractional_year(he.end_year, he.is_bc_end, he.end_month, he.end_day) >= %s
            """
            params = [vmax, vmin]
            
            # Handle multiple categories
            if category and len(category) > 0:
                placeholders = ','.join(['%s'] * len(category))
                query += f"""
                   AND (he.category IN ({placeholders})
                        OR he.event_key IN (
                            SELECT event_key FROM event_categories 
                            WHERE category IN ({placeholders})
                        ))
                """
                params.extend(category)
                params.extend(category)
            
            # Handle multiple strategies
            if strategy and len(strategy) > 0:
                placeholders = ','.join(['%s'] * len(strategy))
                query += f" AND s.name IN ({placeholders})"
                params.extend(strategy)
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            return {"count": result['count']}
        else:
            # No viewport specified, return total count
            query = "SELECT COUNT(*) as count FROM historical_events he LEFT JOIN strategies s ON he.strategy_id = s.id WHERE 1=1"
            params = []
            
            # Handle multiple categories
            if category and len(category) > 0:
                placeholders = ','.join(['%s'] * len(category))
                query += f"""
                   AND (he.category IN ({placeholders})
                        OR he.event_key IN (
                            SELECT event_key FROM event_categories 
                            WHERE category IN ({placeholders})
                        ))
                """
                params.extend(category)
                params.extend(category)
            
            # Handle multiple strategies
            if strategy and len(strategy) > 0:
                placeholders = ','.join(['%s'] * len(strategy))
                query += f" AND s.name IN ({placeholders})"
                params.extend(strategy)
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            return {"count": result['count']}
    
    finally:
        cursor.close()
        conn.close()


@app.get("/search", response_model=List[HistoricalEvent])
def search_events(
    q: str = Query(..., min_length=3, description="Search query"),
    limit: int = Query(50, ge=1, le=100)
):
    """Search historical events by title and description."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT he.id, he.title, he.description, he.start_year, he.end_year,
                   he.is_bc_start, he.is_bc_end, he.category, he.wikipedia_url,
                   s.name as strategy
            FROM historical_events he
            LEFT JOIN strategies s ON he.strategy_id = s.id
            WHERE to_tsvector('english', he.title || ' ' || COALESCE(he.description, '')) @@ plainto_tsquery('english', %s)
            ORDER BY he.start_year ASC NULLS LAST
            LIMIT %s
        """, (q, limit))
        
        events = cursor.fetchall()
        
        # Add display year
        for event in events:
            if event['start_year']:
                event['display_year'] = format_year_display(event['start_year'], event['is_bc_start'])
        
        return events
    
    finally:
        cursor.close()
        conn.close()


# LLM Categorization endpoints for experimentation
class EventCategorization(BaseModel):
    """Request model for event categorization."""
    events: List[Dict[str, Any]]
    model: str = "gpt-4o-mini"


class CategorizationResult(BaseModel):
    """Result of categorizing a single event."""
    event_id: int
    category: str
    confidence: float
    reasoning: str


@app.get("/uncategorized-events")
def get_uncategorized_events(
    limit: int = Query(default=10, ge=1, le=100, description="Number of events to return")
):
    """
    Get events that don't have a category assigned.
    Used for LLM categorization experimentation.
    
    Args:
        limit: Maximum number of events to return (1-100)
    
    Returns:
        List of uncategorized events with full details
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                id,
                title,
                description,
                start_year,
                start_month,
                start_day,
                end_year,
                end_month,
                end_day,
                is_bc_start,
                is_bc_end,
                weight,
                precision,
                wikipedia_url
            FROM historical_events
            WHERE category IS NULL
            ORDER BY RANDOM()
            LIMIT %s
        """, (limit,))
        
        events = cursor.fetchall()
        return {"events": events, "count": len(events)}
    
    finally:
        cursor.close()
        conn.close()


@app.post("/categorize-events")
def categorize_events(request: EventCategorization):
    """
    Categorize events using an LLM.
    Used for experimentation before integrating into ingestion pipeline.
    
    Args:
        request: EventCategorization with events list and model choice
    
    Returns:
        List of categorization results with categories, confidence, and reasoning
    """
    from llm_categorizer import categorize_events_batch
    
    try:
        # Call the modular categorizer
        results = categorize_events_batch(
            events=request.events,
            model=request.model
        )
        
        return {
            "success": True,
            "model": request.model,
            "results": results,
            "count": len(results)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Categorization failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
