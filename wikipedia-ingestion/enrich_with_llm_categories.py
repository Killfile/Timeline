"""LLM-based event categorization enrichment script.

This script enriches historical events with AI-generated categories:
1. Finds events without LLM categorizations
2. Calls GPT-4o-mini to categorize them
3. Stores high-confidence categories (>70%) in event_categories table

The script is idempotent - it skips events that already have LLM categories.

Usage:
    python enrich_with_llm_categories.py [--batch-size N] [--min-confidence 0.7]

Environment Variables:
    OPENAI_API_KEY: OpenAI API key (required)
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD: Database connection
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

import psycopg2
from openai import AsyncOpenAI

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ingestion_common import connect_db, log_info, log_error
except ImportError:
    # Fallback for running outside container
    import logging
    logging.basicConfig(level=logging.INFO)
    
    def log_info(msg: str) -> None:
        logging.info(msg)
    
    def log_error(msg: str) -> None:
        logging.error(msg)
    
    def connect_db():
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "timeline_history"),
            user=os.getenv("DB_USER", "timeline_user"),
            password=os.getenv("DB_PASSWORD", "timeline_pass")
        )


# Standard category list (matching LLM experiment page)
STANDARD_CATEGORIES = [
    "Politics",
    "War & Conflict",
    "Science & Technology",
    "Arts & Culture",
    "Religion",
    "Economics & Trade",
    "Natural Disasters",
    "Exploration & Discovery",
    "Social Movements",
    "Sports",
    "Education",
    "Other"
]


def get_uncategorized_events(conn, limit: int = 100) -> List[Dict[str, Any]]:
    """Get events that don't have LLM-assigned categories.
    
    Returns events that either:
    - Have no categories at all
    - Have only Wikipedia categories (no LLM categories)
    
    Args:
        conn: Database connection
        limit: Maximum number of events to return
        
    Returns:
        List of event dictionaries with event_key, title, description, dates
    """
    cursor = conn.cursor()
    try:
        query = """
            SELECT 
                he.event_key,
                he.title,
                he.description,
                he.start_year,
                he.end_year,
                he.is_bc_start,
                he.is_bc_end
            FROM historical_events he
            WHERE NOT EXISTS (
                SELECT 1 
                FROM event_categories ec 
                WHERE ec.event_key = he.event_key 
                  AND ec.llm_source IS NOT NULL
            )
            ORDER BY RANDOM()
            LIMIT %s;
        """
        
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        
        events = []
        for row in rows:
            event_key, title, description, start_year, end_year, is_bc_start, is_bc_end = row
            
            # Format year display
            start_display = f"{start_year} {'BC' if is_bc_start else 'AD'}"
            if end_year and end_year != start_year:
                end_display = f"{end_year} {'BC' if is_bc_end else 'AD'}"
                date_range = f"{start_display} to {end_display}"
            else:
                date_range = start_display
            
            events.append({
                "event_key": event_key,
                "title": title,
                "description": description or "",
                "date_range": date_range,
                "start_year": start_year,
                "end_year": end_year
            })
        
        return events
    finally:
        cursor.close()


def categorize_events_with_llm(
    events: List[Dict[str, Any]], 
    model: str = "gpt-4o-mini"
) -> List[Dict[str, Any]]:
    """Categorize events using OpenAI API (synchronous wrapper).
    
    Args:
        events: List of event dictionaries
        model: OpenAI model to use
        
    Returns:
        List of categorization results with event_key, categories, confidence
    """
    return asyncio.run(categorize_events_with_llm_async(events, model))


async def categorize_events_with_llm_async(
    events: List[Dict[str, Any]], 
    model: str = "gpt-4o-mini"
) -> List[Dict[str, Any]]:
    """Categorize events using OpenAI API (async).
    
    Args:
        events: List of event dictionaries
        model: OpenAI model to use
        
    Returns:
        List of categorization results with event_key, categories, confidence
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY or OPEN_AI_API_KEY environment variable required")
    
    # Use async context manager to ensure proper cleanup
    async with AsyncOpenAI(api_key=api_key) as client:
        # Build prompt
        event_list = "\n\n".join([
            f"Event {i+1}:\n"
            f"Title: {event['title']}\n"
            f"Date: {event['date_range']}\n"
            f"Description: {event['description'][:200]}"  # Truncate long descriptions
            for i, event in enumerate(events)
        ])
        
        system_prompt = f"""You are a historian categorizing historical events.

For each event, assign ONE OR MORE categories from this list:
{', '.join(STANDARD_CATEGORIES)}

Provide a confidence score (0.0 to 1.0) for each category assignment.

Respond in JSON format:
{{
  "categorizations": [
    {{
      "event_number": 1,
      "categories": [
        {{"category": "Politics", "confidence": 0.95, "reasoning": "Event involves government"}},
        {{"category": "War & Conflict", "confidence": 0.80, "reasoning": "Military action"}}
      ]
    }}
  ]
}}"""

        user_prompt = f"Categorize these historical events:\n\n{event_list}"
        
        log_info(f"Calling {model} to categorize {len(events)} events...")
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # Map results back to events by event_key
        categorizations = result.get("categorizations", [])
        results = []
        
        for cat in categorizations:
            event_idx = cat.get("event_number", 1) - 1
            if 0 <= event_idx < len(events):
                event = events[event_idx]
                results.append({
                    "event_key": event["event_key"],
                    "categories": cat.get("categories", [])
                })
        
        return results


def store_llm_categories(
    conn,
    event_key: str,
    categories: List[Dict[str, Any]],
    model: str,
    min_confidence: float = 0.7
) -> int:
    """Store LLM-generated categories in the database.
    
    Args:
        conn: Database connection
        event_key: Event key to categorize
        categories: List of category dicts with category, confidence, reasoning
        model: Model name that generated the categories
        min_confidence: Minimum confidence threshold (0.0-1.0)
        
    Returns:
        Number of categories stored
    """
    cursor = conn.cursor()
    stored_count = 0
    
    try:
        for cat_data in categories:
            category = cat_data.get("category")
            confidence = cat_data.get("confidence", 0.0)
            
            # Validate category
            if category not in STANDARD_CATEGORIES:
                log_error(f"Invalid category '{category}' for event {event_key}")
                continue
            
            # Check confidence threshold
            if confidence < min_confidence:
                log_info(f"Skipping '{category}' for event {event_key} (confidence {confidence:.2f} < {min_confidence:.2f})")
                continue
            
            # Insert category (upsert to handle duplicates)
            insert_sql = """
                INSERT INTO event_categories (event_key, category, llm_source, confidence, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (event_key, category, llm_source) DO UPDATE
                SET confidence = EXCLUDED.confidence, created_at = EXCLUDED.created_at;
            """
            
            cursor.execute(insert_sql, (event_key, category, model, confidence))
            if cursor.rowcount > 0:
                stored_count += 1
                log_info(f"  ✓ {category} ({confidence:.0%}) → {event_key[:16]}...")
        
        conn.commit()
        return stored_count
        
    except Exception as e:
        conn.rollback()
        log_error(f"Failed to store categories for event {event_key}: {e}")
        raise
    finally:
        cursor.close()


async def categorize_batch_parallel(
    events: List[Dict[str, Any]],
    page_size: int,
    model: str = "gpt-4o-mini"
) -> List[Dict[str, Any]]:
    """Categorize a batch of events in parallel by splitting into pages.
    
    Args:
        events: List of event dictionaries
        page_size: Number of events per API call
        model: OpenAI model to use
        
    Returns:
        Combined list of categorization results from all pages
    """
    # Split events into pages
    pages = [events[i:i + page_size] for i in range(0, len(events), page_size)]
    
    log_info(f"Dispatching {len(pages)} parallel requests ({page_size} events each)...")
    
    # Create async tasks for each page
    tasks = [
        categorize_events_with_llm_async(page, model)
        for page in pages
    ]
    
    # Wait for all tasks to complete
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Combine results and handle errors
    all_results = []
    for i, result in enumerate(results_list):
        if isinstance(result, Exception):
            log_error(f"Page {i+1} failed: {result}")
            # Continue with other pages
        else:
            all_results.extend(result)
    
    log_info(f"Completed {len(results_list)} parallel requests, got {len(all_results)} results")
    
    return all_results


def enrich_with_llm_categories(
    batch_size: int = 15,
    page_size: int = 15,
    min_confidence: float = 0.7,
    max_events: int = None,
    model: str = "gpt-4o-mini"
) -> None:
    """Main enrichment function.
    
    Args:
        batch_size: Number of events to fetch from DB per batch
        page_size: Number of events per API call (for parallelization)
        min_confidence: Minimum confidence threshold (0.0-1.0)
        max_events: Maximum total events to process (None for unlimited)
        model: OpenAI model to use
    """
    conn = connect_db()
    total_processed = 0
    total_categories_added = 0
    
    try:
        while True:
            # Get uncategorized events
            limit = batch_size if max_events is None else min(batch_size, max_events - total_processed)
            if limit <= 0:
                break
            
            events = get_uncategorized_events(conn, limit=limit)
            
            if not events:
                log_info("No more events to categorize!")
                break
            
            log_info(f"\n{'='*60}")
            log_info(f"Processing batch of {len(events)} events...")
            log_info(f"{'='*60}\n")
            
            # Categorize with LLM (parallel if batch > page_size)
            try:
                if len(events) > page_size:
                    # Use parallel processing
                    results = asyncio.run(categorize_batch_parallel(events, page_size, model))
                else:
                    # Single request
                    results = categorize_events_with_llm(events, model=model)
            except Exception as e:
                log_error(f"Batch failed, skipping: {e}")
                break
            
            # Store results
            for result in results:
                event_key = result["event_key"]
                categories = result["categories"]
                
                if not categories:
                    log_info(f"No categories for event {event_key[:16]}...")
                    continue
                
                stored = store_llm_categories(
                    conn, 
                    event_key, 
                    categories, 
                    model, 
                    min_confidence
                )
                total_categories_added += stored
            
            total_processed += len(events)
            log_info(f"\n✓ Processed {total_processed} events total, added {total_categories_added} categories")
            
            if max_events and total_processed >= max_events:
                log_info(f"Reached max events limit ({max_events})")
                break
        
        log_info(f"\n{'='*60}")
        log_info(f"✅ Enrichment complete!")
        log_info(f"  Total events processed: {total_processed}")
        log_info(f"  Total categories added: {total_categories_added}")
        log_info(f"{'='*60}\n")
        
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Enrich events with LLM-generated categories"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=15,
        help="Number of events to fetch from DB per batch (default: 15)"
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=15,
        help="Number of events per API call for parallelization (default: 15)"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.7,
        help="Minimum confidence threshold 0.0-1.0 (default: 0.7)"
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=None,
        help="Maximum total events to process (default: unlimited)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        choices=["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
        help="OpenAI model to use (default: gpt-4o-mini)"
    )
    
    args = parser.parse_args()
    
    log_info(f"Starting LLM categorization enrichment...")
    log_info(f"  Model: {args.model}")
    log_info(f"  Batch size: {args.batch_size}")
    log_info(f"  Page size: {args.page_size}")
    log_info(f"  Min confidence: {args.min_confidence:.0%}")
    log_info(f"  Max events: {args.max_events or 'unlimited'}\n")
    
    try:
        enrich_with_llm_categories(
            batch_size=args.batch_size,
            page_size=args.page_size,
            min_confidence=args.min_confidence,
            max_events=args.max_events,
            model=args.model
        )
    except Exception as e:
        log_error(f"Enrichment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
