import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
import json

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'database'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'timeline'),
    'user': os.getenv('DB_USER', 'timeline_user'),
    'password': os.getenv('DB_PASSWORD', 'timeline_pass')
}

# Create FastAPI app
app = FastAPI(
    title="Timeline API",
    description="API for accessing timeline event data",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class Event(BaseModel):
    id: int
    event_time: datetime
    event_type: str
    event_value: Optional[float] = None
    event_metadata: Optional[dict] = None
    source: str
    processed_at: datetime


class EventSummary(BaseModel):
    event_type: str
    event_count: int
    first_event: Optional[datetime] = None
    last_event: Optional[datetime] = None
    avg_value: Optional[float] = None


class Stats(BaseModel):
    total_events: int
    total_raw_events: int
    event_types_count: int
    latest_event_time: Optional[datetime] = None


# Database connection helper
def get_db_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except psycopg2.OperationalError as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "Timeline API",
        "version": "1.0.0",
        "endpoints": {
            "events": "/events",
            "summary": "/summary",
            "stats": "/stats",
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


@app.get("/events", response_model=List[Event])
def get_events(
    limit: int = Query(100, ge=1, le=1000, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    source: Optional[str] = Query(None, description="Filter by source"),
    hours: Optional[int] = Query(None, ge=1, le=168, description="Filter events from last N hours")
):
    """Get processed events with optional filters."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT * FROM processed_events WHERE 1=1"
        params = []
        
        if event_type:
            query += " AND event_type = %s"
            params.append(event_type)
        
        if source:
            query += " AND source = %s"
            params.append(source)
        
        if hours:
            query += " AND event_time > %s"
            params.append(datetime.now() - timedelta(hours=hours))
        
        query += " ORDER BY event_time DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        events = cursor.fetchall()
        
        # Parse JSON metadata
        for event in events:
            if event['event_metadata']:
                try:
                    event['event_metadata'] = json.loads(event['event_metadata']) if isinstance(event['event_metadata'], str) else event['event_metadata']
                except json.JSONDecodeError:
                    event['event_metadata'] = {}
        
        return events
    
    finally:
        cursor.close()
        conn.close()


@app.get("/summary", response_model=List[EventSummary])
def get_summary():
    """Get summary of events by type."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM timeline_summary ORDER BY event_count DESC")
        summary = cursor.fetchall()
        return summary
    
    finally:
        cursor.close()
        conn.close()


@app.get("/stats", response_model=Stats)
def get_stats():
    """Get overall statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get total processed events
        cursor.execute("SELECT COUNT(*) as count FROM processed_events")
        total_events = cursor.fetchone()['count']
        
        # Get total raw events
        cursor.execute("SELECT COUNT(*) as count FROM raw_events")
        total_raw_events = cursor.fetchone()['count']
        
        # Get distinct event types
        cursor.execute("SELECT COUNT(DISTINCT event_type) as count FROM processed_events")
        event_types_count = cursor.fetchone()['count']
        
        # Get latest event time
        cursor.execute("SELECT MAX(event_time) as latest FROM processed_events")
        result = cursor.fetchone()
        latest_event_time = result['latest'] if result else None
        
        return {
            "total_events": total_events,
            "total_raw_events": total_raw_events,
            "event_types_count": event_types_count,
            "latest_event_time": latest_event_time
        }
    
    finally:
        cursor.close()
        conn.close()


@app.get("/event-types")
def get_event_types():
    """Get list of all event types."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT DISTINCT event_type FROM processed_events ORDER BY event_type")
        types = [row['event_type'] for row in cursor.fetchall()]
        return {"event_types": types}
    
    finally:
        cursor.close()
        conn.close()


@app.get("/sources")
def get_sources():
    """Get list of all sources."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT DISTINCT source FROM processed_events ORDER BY source")
        sources = [row['source'] for row in cursor.fetchall()]
        return {"sources": sources}
    
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
