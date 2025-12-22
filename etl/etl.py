import os
import time
import psycopg2
from datetime import datetime
import json

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'database'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'timeline'),
    'user': os.getenv('DB_USER', 'timeline_user'),
    'password': os.getenv('DB_PASSWORD', 'timeline_pass')
}


def connect_db():
    """Connect to the database with retry logic."""
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            print(f"Successfully connected to database at {DB_CONFIG['host']}")
            return conn
        except psycopg2.OperationalError as e:
            if attempt < max_retries - 1:
                print(f"Connection attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Failed to connect to database after {max_retries} attempts")
                raise


def extract_event_value(event_type, event_data):
    """Extract numeric value from event data based on event type."""
    try:
        data = json.loads(event_data) if isinstance(event_data, str) else event_data
        
        if event_type == 'page_view':
            return data.get('duration_ms', 0)
        elif event_type == 'api_call':
            return data.get('response_time_ms', 0)
        elif event_type == 'form_submit':
            return data.get('fields_count', 0)
        elif event_type == 'error_occurred':
            return int(data.get('error_code', 0))
        elif event_type in ['user_login', 'user_logout', 'button_click']:
            return 1  # Count occurrences
        else:
            return 0
    except (json.JSONDecodeError, ValueError, KeyError):
        return 0


def enrich_metadata(event_type, event_data):
    """Enrich and structure metadata for processed events."""
    try:
        data = json.loads(event_data) if isinstance(event_data, str) else event_data
        
        metadata = {
            'user_id': data.get('user_id'),
            'session_id': data.get('session_id'),
            'original_timestamp': data.get('timestamp')
        }
        
        # Add type-specific enrichment
        if event_type == 'user_login':
            metadata['device_type'] = data.get('device_type')
            metadata['ip_address'] = data.get('ip_address')
        elif event_type == 'page_view':
            metadata['page_url'] = data.get('page_url')
        elif event_type == 'button_click':
            metadata['button_id'] = data.get('button_id')
            metadata['page'] = data.get('page')
        elif event_type == 'api_call':
            metadata['endpoint'] = data.get('endpoint')
            metadata['method'] = data.get('method')
        elif event_type == 'error_occurred':
            metadata['error_message'] = data.get('error_message')
            
        return metadata
    except (json.JSONDecodeError, ValueError):
        return {}


def process_batch(conn, batch_size=100):
    """Process a batch of raw events and transform them into processed events."""
    cursor = conn.cursor()
    
    try:
        # Find unprocessed raw events
        cursor.execute("""
            SELECT id, event_time, event_type, event_data, source
            FROM raw_events
            WHERE id > (
                SELECT COALESCE(MAX(id), 0) 
                FROM raw_events r
                WHERE EXISTS (
                    SELECT 1 FROM processed_events p 
                    WHERE p.source = r.source 
                    AND p.event_time = r.event_time
                )
            )
            ORDER BY id
            LIMIT %s
        """, (batch_size,))
        
        raw_events = cursor.fetchall()
        
        if not raw_events:
            return 0
        
        # Transform and load into processed_events
        processed_count = 0
        for event_id, event_time, event_type, event_data, source in raw_events:
            event_value = extract_event_value(event_type, event_data)
            event_metadata = enrich_metadata(event_type, event_data)
            
            cursor.execute("""
                INSERT INTO processed_events 
                (event_time, event_type, event_value, event_metadata, source)
                VALUES (%s, %s, %s, %s, %s)
            """, (event_time, event_type, event_value, json.dumps(event_metadata), source))
            
            processed_count += 1
        
        conn.commit()
        return processed_count
        
    except Exception as e:
        print(f"Error processing batch: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()


def run_etl(conn):
    """Continuously run ETL process."""
    print("Starting ETL process...")
    total_processed = 0
    
    try:
        while True:
            processed = process_batch(conn, batch_size=50)
            
            if processed > 0:
                total_processed += processed
                print(f"Processed {processed} events (Total: {total_processed})")
            else:
                # No new events to process, wait a bit
                time.sleep(5)
            
            # Small delay between batches
            time.sleep(2)
            
    except KeyboardInterrupt:
        print(f"\nETL stopped. Total events processed: {total_processed}")
    except Exception as e:
        print(f"Error in ETL process: {e}")
        raise


def main():
    """Main function to run the ETL service."""
    print("Timeline ETL Service")
    print("=" * 50)
    
    # Wait for database and ingestion to be ready
    print("Waiting for database and ingestion service...")
    time.sleep(15)
    
    # Connect to database
    conn = connect_db()
    
    try:
        # Start ETL process
        run_etl(conn)
    finally:
        conn.close()
        print("Database connection closed")


if __name__ == "__main__":
    main()
