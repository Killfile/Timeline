import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'database'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'timeline_history'),
    'user': os.getenv('DB_USER', 'timeline_user'),
    'password': os.getenv('DB_PASSWORD', 'timeline_pass')
}

# Create FastAPI app
app = FastAPI(
    title="Historical Timeline API",
    description="API for accessing Wikipedia-based historical events",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class HistoricalEvent(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    is_bc_start: bool = False
    is_bc_end: bool = False
    category: Optional[str] = None
    wikipedia_url: Optional[str] = None
    display_year: Optional[str] = None


class TimelineStats(BaseModel):
    total_events: int
    earliest_year: Optional[int] = None
    latest_year: Optional[int] = None
    categories: List[str] = []


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
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/events", response_model=List[HistoricalEvent])
def get_events(
    start_year: Optional[int] = Query(None, description="Filter events starting from this year"),
    end_year: Optional[int] = Query(None, description="Filter events up to this year"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get historical events with optional filters."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT id, title, description, start_year, end_year, 
                   is_bc_start, is_bc_end, category, wikipedia_url
            FROM historical_events 
            WHERE 1=1
        """
        params = []
        
        if start_year is not None:
            query += " AND start_year >= %s"
            params.append(start_year)
        
        if end_year is not None:
            query += " AND (end_year <= %s OR end_year IS NULL)"
            params.append(end_year)
        
        if category:
            query += " AND category = %s"
            params.append(category)
        
        query += " ORDER BY start_year ASC NULLS LAST, end_year ASC NULLS LAST"
        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        events = cursor.fetchall()
        
        # Add display year
        for event in events:
            if event['start_year']:
                event['display_year'] = format_year_display(event['start_year'], event['is_bc_start'])
        
        return events
    
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
            SELECT id, title, description, start_year, end_year,
                   is_bc_start, is_bc_end, category, wikipedia_url
            FROM historical_events 
            WHERE id = %s
        """, (event_id,))
        
        event = cursor.fetchone()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Add display year
        if event['start_year']:
            event['display_year'] = format_year_display(event['start_year'], event['is_bc_start'])
        
        return event
    
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
    """Get list of all categories."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM historical_events 
            WHERE category IS NOT NULL 
            GROUP BY category 
            ORDER BY count DESC, category
        """)
        categories = cursor.fetchall()
        return {"categories": categories}
    
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
            SELECT id, title, description, start_year, end_year,
                   is_bc_start, is_bc_end, category, wikipedia_url
            FROM historical_events
            WHERE to_tsvector('english', title || ' ' || COALESCE(description, '')) @@ plainto_tsquery('english', %s)
            ORDER BY start_year ASC NULLS LAST
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
