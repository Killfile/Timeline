import os
import time
import re
import psycopg2
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'database'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'timeline_history'),
    'user': os.getenv('DB_USER', 'timeline_user'),
    'password': os.getenv('DB_PASSWORD', 'timeline_pass')
}

# Wikipedia API endpoint
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"

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


def parse_year(year_str):
    """Parse a year string and determine if it's BC/AD."""
    year_str = str(year_str).strip()
    is_bc = 'BC' in year_str or 'BCE' in year_str
    
    # Extract numeric year
    year_match = re.search(r'\d+', year_str)
    if year_match:
        year = int(year_match.group())
        return year, is_bc
    return None, False


def fetch_historical_events_by_category(category):
    """Fetch historical events from Wikipedia by category."""
    events = []
    
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": 50,
        "format": "json"
    }
    
    try:
        response = requests.get(WIKIPEDIA_API, params=params, timeout=30)
        data = response.json()
        
        if 'query' in data and 'categorymembers' in data['query']:
            for member in data['query']['categorymembers']:
                event = {
                    'title': member['title'],
                    'pageid': member['pageid']
                }
                events.append(event)
        
        print(f"Fetched {len(events)} events from category: {category}")
        
    except Exception as e:
        print(f"Error fetching category {category}: {e}")
    
    return events


def extract_event_details(pageid):
    """Extract event details including dates from a Wikipedia page."""
    params = {
        "action": "query",
        "pageids": pageid,
        "prop": "extracts|info",
        "exintro": True,
        "explaintext": True,
        "inprop": "url",
        "format": "json"
    }
    
    try:
        response = requests.get(WIKIPEDIA_API, params=params, timeout=30)
        data = response.json()
        
        if 'query' in data and 'pages' in data['query']:
            page = data['query']['pages'][str(pageid)]
            
            extract = page.get('extract', '')
            url = page.get('fullurl', '')
            
            # Try to extract years from the text
            years = re.findall(r'(\d{1,4})\s*(BC|BCE|AD|CE)?', extract)
            
            start_year = None
            end_year = None
            is_bc_start = False
            is_bc_end = False
            
            if years:
                # Take the first year as start
                start_year, start_era = years[0]
                start_year = int(start_year)
                is_bc_start = start_era in ['BC', 'BCE']
                
                # If multiple years, take the last as end
                if len(years) > 1:
                    end_year, end_era = years[-1]
                    end_year = int(end_year)
                    is_bc_end = end_era in ['BC', 'BCE']
            
            return {
                'description': extract[:500] if extract else None,  # Limit description
                'url': url,
                'start_year': start_year,
                'end_year': end_year,
                'is_bc_start': is_bc_start,
                'is_bc_end': is_bc_end
            }
    
    except Exception as e:
        print(f"Error extracting details for page {pageid}: {e}")
    
    return None


def insert_event(conn, event, category):
    """Insert an event into the database."""
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO historical_events 
            (title, description, start_year, end_year, is_bc_start, is_bc_end, category, wikipedia_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            event['title'],
            event.get('description'),
            event.get('start_year'),
            event.get('end_year'),
            event.get('is_bc_start', False),
            event.get('is_bc_end', False),
            category,
            event.get('url')
        ))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error inserting event: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()


def ingest_wikipedia_data(conn):
    """Main ingestion function."""
    print("Starting Wikipedia data ingestion...")
    
    # Categories of historical events to fetch
    categories = [
        "Ancient history",
        "Medieval history",
        "Modern history",
        "World War I",
        "World War II",
        "Renaissance",
        "Industrial Revolution",
        "Cold War",
        "Space exploration",
        "Scientific discoveries"
    ]
    
    total_inserted = 0
    
    for category in categories:
        print(f"\nProcessing category: {category}")
        events = fetch_historical_events_by_category(category)
        
        for event in events:
            # Rate limiting
            time.sleep(0.5)
            
            print(f"Processing: {event['title']}")
            details = extract_event_details(event['pageid'])
            
            if details:
                event.update(details)
                if insert_event(conn, event, category):
                    total_inserted += 1
                    print(f"✓ Inserted: {event['title']}")
        
        # Pause between categories
        time.sleep(2)
    
    print(f"\n{'='*50}")
    print(f"Ingestion complete! Total events inserted: {total_inserted}")
    print(f"{'='*50}")


def main():
    """Main function."""
    print("Wikipedia Historical Timeline Ingestion Service")
    print("=" * 50)
    
    # Wait for database to be ready
    print("Waiting for database to be ready...")
    time.sleep(10)
    
    # Connect to database
    conn = connect_db()
    
    try:
        # Ingest data
        ingest_wikipedia_data(conn)
        
        # Keep container running
        print("\nIngestion complete. Container will stay running...")
        while True:
            time.sleep(3600)  # Sleep for an hour
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        conn.close()
        print("Database connection closed")


if __name__ == "__main__":
    main()
