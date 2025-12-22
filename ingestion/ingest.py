import os
import time
import random
import psycopg2
from datetime import datetime, timedelta
import json
from psycopg2.extras import Json

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'database'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'timeline'),
    'user': os.getenv('DB_USER', 'timeline_user'),
    'password': os.getenv('DB_PASSWORD', 'timeline_pass')
}

# Event types to simulate
EVENT_TYPES = [
    'user_login',
    'user_logout',
    'page_view',
    'button_click',
    'form_submit',
    'api_call',
    'error_occurred'
]

SOURCES = ['web_app', 'mobile_app', 'api_gateway']


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


def generate_event_data(event_type):
    """Generate sample event data based on event type."""
    base_data = {
        'timestamp': datetime.now().isoformat(),
        'user_id': f"user_{random.randint(1, 100)}",
        'session_id': f"session_{random.randint(1, 50)}"
    }
    
    if event_type == 'user_login':
        base_data['ip_address'] = f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
        base_data['device_type'] = random.choice(['desktop', 'mobile', 'tablet'])
    elif event_type == 'page_view':
        base_data['page_url'] = random.choice(['/home', '/dashboard', '/profile', '/settings', '/timeline'])
        base_data['duration_ms'] = random.randint(100, 5000)
    elif event_type == 'button_click':
        base_data['button_id'] = random.choice(['submit_btn', 'cancel_btn', 'refresh_btn', 'export_btn'])
        base_data['page'] = random.choice(['dashboard', 'timeline', 'settings'])
    elif event_type == 'form_submit':
        base_data['form_name'] = random.choice(['contact_form', 'settings_form', 'search_form'])
        base_data['fields_count'] = random.randint(3, 10)
    elif event_type == 'api_call':
        base_data['endpoint'] = random.choice(['/api/events', '/api/users', '/api/timeline', '/api/stats'])
        base_data['method'] = random.choice(['GET', 'POST', 'PUT', 'DELETE'])
        base_data['response_time_ms'] = random.randint(50, 1000)
    elif event_type == 'error_occurred':
        base_data['error_code'] = random.choice(['404', '500', '403', '400'])
        base_data['error_message'] = 'Simulated error for testing'
    
    return base_data


def ingest_events(conn):
    """Continuously ingest sample events into the database."""
    cursor = conn.cursor()
    event_count = 0
    
    print("Starting data ingestion...")
    
    try:
        while True:
            # Generate a random number of events per batch
            batch_size = random.randint(1, 5)
            
            for _ in range(batch_size):
                event_type = random.choice(EVENT_TYPES)
                source = random.choice(SOURCES)
                event_data = generate_event_data(event_type)
                
                # Random time within the last hour for more realistic data
                event_time = datetime.now() - timedelta(seconds=random.randint(0, 3600))
                
                cursor.execute(
                    """
                    INSERT INTO raw_events (event_time, event_type, event_data, source)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (event_time, event_type, Json(event_data), source)
                )
                
                event_count += 1
            
            conn.commit()
            
            if event_count % 10 == 0:
                print(f"Ingested {event_count} events so far...")
            
            # Wait a bit before next batch
            time.sleep(random.uniform(2, 5))
            
    except KeyboardInterrupt:
        print(f"\nIngestion stopped. Total events ingested: {event_count}")
    except Exception as e:
        print(f"Error during ingestion: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()


def main():
    """Main function to run the ingestion service."""
    print("Timeline Data Ingestion Service")
    print("=" * 50)
    
    # Wait a moment for database to be fully ready
    print("Waiting for database to be ready...")
    time.sleep(10)
    
    # Connect to database
    conn = connect_db()
    
    try:
        # Start ingesting events
        ingest_events(conn)
    finally:
        conn.close()
        print("Database connection closed")


if __name__ == "__main__":
    main()
