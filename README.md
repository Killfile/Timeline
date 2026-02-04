# Timeline

A containerized application that ingests historical events from Wikipedia and displays them as an interactive, filterable, zoomable timeline using D3.js.

## Features

- **Wikipedia Data Ingestion**: Automatically fetches historical events from Wikipedia articles
- **Time-Series Database**: Stores events with BC/AD date support
- **RESTful API**: FastAPI backend for querying historical events
- **Interactive Canvas Timeline**: Zoomable and pannable timeline visualization with semantic category coloring
- **Filtering & Search**: Filter by category or search across the entire database by keywords
- **Event Details**: Click on any event to see detailed information and Wikipedia links

## Architecture

This application consists of four containerized services:

1. **PostgreSQL Database** - Stores historical events with temporal data (BC/AD support)
2. **Wikipedia Ingestion Service** - Python service that fetches events from Wikipedia API
3. **API Service** - FastAPI backend providing endpoints for timeline data
4. **Frontend** - Interactive Canvas-based visualization with zoom, pan, semantic coloring, and search highlighting

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/Killfile/Timeline.git
   cd Timeline
   ```

2. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

3. Start all services:
   ```bash
   docker compose up -d
   ```

4. Wait for data ingestion (takes a few minutes to fetch Wikipedia data)

5. Access the application:
   - **Frontend**: http://localhost:3000
   - **API**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs

## API Authentication

All API endpoints require JWT authentication (except `/token`). The frontend automatically handles authentication, but if you're accessing the API directly:

### Quick Start

1. Get an access token:
```bash
curl -X POST http://localhost:8000/token \
  -H "X-Client-Secret: test-client-secret-12345" \
  -H "Origin: http://localhost:3000"
```

2. Use the token in API requests:
```bash
curl http://localhost:8000/events \
  -H "Authorization: Bearer <your-token>" \
  -H "Origin: http://localhost:3000"
```

### Key Points

- **Token TTL**: 15 minutes (900 seconds)
- **Required Headers**: `Authorization: Bearer <token>` and `Origin: <your-domain>`
- **Protected Endpoints**: All endpoints except `/token` require authentication
- **Rate Limiting**: 60 token requests per minute per IP

### Configuration

Set these in `docker-compose.yml`:
```yaml
API_CLIENT_SECRET: "test-client-secret-12345"
API_JWT_SECRET: "test-jwt-secret-67890"
API_ALLOWED_ORIGINS: "http://localhost:3000,http://127.0.0.1:3000"
```

**⚠️ Production**: Change default secrets and restrict origins to your domain.

For detailed authentication documentation, see [api/README.md](api/README.md) and [docs/README.md](docs/README.md).

## Using the Timeline

### Navigation
- **Zoom In/Out**: Scroll up or down on the timeline
- **Pan**: Click and drag to move along the timeline
- **Reset View**: Click "Reset Zoom" button to return to full view

### Filtering
- **By Category**: Use the dropdown to filter events by historical category
- **By Search**: Enter keywords to search event titles and descriptions

### Event Details
- Click on any event marker (circle) to see:
  - Event title and time period
  - Category
  - Description
  - Link to Wikipedia article

## Services

### Database (PostgreSQL)
- **Port**: 5432
- **Database**: timeline_history
- Stores historical events with BC/AD date support
- Optimized indexes for temporal queries
- Full-text search capability

### Wikipedia Ingestion Service
- Fetches events from Wikipedia categories:
  - Ancient history
  - Medieval history
  - Modern history
  - World Wars
  - Renaissance
  - Industrial Revolution
  - Cold War
  - Space exploration
  - Scientific discoveries
- Extracts temporal information (years, BC/AD)
- Stores structured event data

### API Service
- **Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Authentication**: All endpoints require JWT authentication (see [API Authentication](#api-authentication))

**Endpoints**:
- `POST /token` - Get JWT access token (X-Client-Secret required)
- `GET /` - API information
- `GET /health` - Health check ⚠️ **Requires authentication**
- `GET /events` - List events (filterable by year range, category)
- `GET /events/{id}` - Get specific event
- `GET /stats` - Timeline statistics
- `GET /categories` - List all categories
- `GET /search?q={query}` - Search events by keywords

### Frontend Service
- D3.js-powered interactive timeline
- Zoomable and pannable visualization
- Event markers colored by category
- Click events for details
- Responsive design

### pgAdmin (database inspector)

This repo includes a pgAdmin container for inspecting Postgres.

- **URL**: http://localhost:5050 (or whatever `PGADMIN_PORT` is in `.env`)
- **Login**:
   - Email: `PGADMIN_DEFAULT_EMAIL` (default `admin@example.com`)
   - Password: `PGADMIN_DEFAULT_PASSWORD`

The Postgres server runs on the Docker Compose network, so from pgAdmin the host is the Compose service name:

- **Host name/address**: `database`
- **Port**: `5432`
- **Maintenance DB**: `POSTGRES_DB` (default `timeline_history`)
- **Username**: `POSTGRES_USER` (default `timeline_user`)
- **Password**: `POSTGRES_PASSWORD`

Note: pgAdmin is preconfigured with a server entry named **"Timeline Postgres"** via `pgadmin/servers.json`. If you don't see it, restart the pgAdmin service (`docker compose restart pgadmin`).

## Configuration

### Wikipedia Ingestion Tuning

You can control which Wikipedia year pages are ingested using environment variables in your `.env` file or `docker-compose.yml`:

#### `WIKI_MIN_YEAR`
Specifies the earliest year to start ingesting. Format: `"#### AD/BC"` or `"#### BCE/CE"` (AD/CE is default if era not specified).

**Examples:**
- `WIKI_MIN_YEAR="100 BC"` - Start at 100 BC, then 99 BC, 98 BC, ... (skips earlier years like 200 BC, 150 BC, 101 BC)
- `WIKI_MIN_YEAR="10 AD"` or `WIKI_MIN_YEAR="10"` - Start at 10 AD, skipping all BC years and 1-9 AD
- Not set - Start from the earliest available year (~1000 BC)

#### `WIKI_MAX_YEAR`
Specifies the latest year to stop ingesting. Format: `"#### AD/BC"` or `"#### BCE/CE"` (AD/CE is default if era not specified).

**Examples:**
- `WIKI_MAX_YEAR="150 BC"` - Ingest through 150 BC, then stop (excludes 149 BC, 100 BC, 1 BC, and all AD years which come after 150 BC)
- `WIKI_MAX_YEAR="1962 AD"` or `WIKI_MAX_YEAR="1962"` - Ingest through 1962 AD, stopping before 1963 AD
- Not set - Ingest through the latest available year

#### Combined Usage
You can use both parameters to define a specific range:
- `WIKI_MIN_YEAR="100 BC"` and `WIKI_MAX_YEAR="50 BC"` - Ingest only 100 BC through 50 BC
- `WIKI_MIN_YEAR="10 AD"` and `WIKI_MAX_YEAR="50 AD"` - Ingest only 10 AD through 50 AD
- `WIKI_MIN_YEAR="50 BC"` and `WIKI_MAX_YEAR="50 AD"` - Ingest from 50 BC through 50 AD (crossing the BC/AD boundary)

**Note:** BC years count backwards chronologically - 200 BC comes BEFORE 100 BC in time (higher BC numbers = earlier in history).

**Usage in `.env` file:**
```bash
WIKI_MIN_YEAR=100 BC
WIKI_MAX_YEAR=50 AD
```

**Usage in `docker-compose.yml`:**
```yaml
wikipedia-ingestion:
  environment:
    WIKI_MIN_YEAR: "100 BC"
    WIKI_MAX_YEAR: "50 AD"
```

After changing these settings, restart the ingestion service and re-run ingestion:
```bash
docker compose restart wikipedia-ingestion
docker compose run --rm wikipedia-ingestion python ingest_wikipedia.py
```

## Data Management

### Reimporting Wikipedia Data

There are two ways to reimport Wikipedia data:

#### Option 1: Atomic Reimport (Preserves Enrichments) ⭐ **Recommended**

Use this when you want to refresh Wikipedia data while keeping user-generated enrichments (categories, notes, interest counts):

```bash
./scripts/atomic-reimport
```

With date range:
```bash
./scripts/atomic-reimport "1000 BC" "2026 AD"
```

**How it works:**
1. Imports data into a temporary table
2. Atomically swaps tables (< 1 second downtime)
3. Preserves enrichments via deterministic `event_key` matching
4. Automatically cleans up orphaned enrichments

See [docs/atomic-reimport.md](docs/atomic-reimport.md) for details.

#### Option 2: Full Reset (Clean Slate)

Use this when you want to completely reset the database:

```bash
./scripts/reset-and-reimport
```

**Warning:** This deletes ALL data including enrichments!

### Event Key System

The timeline uses a deterministic `event_key` system (SHA-256 hash) to maintain relationships between:
- **First-order data**: Raw Wikipedia events in `historical_events`
- **Second-order data**: Enrichments like categories, interest counts in `event_enrichments` and `event_categories`

Because the key is based on event content (title + dates + description), enrichments survive reimports as long as the event content doesn't change significantly.

See [docs/enrichment-architecture.md](docs/enrichment-architecture.md) for technical details.

## Development

### View logs for all services:
```bash
docker compose logs -f
```

### View logs for a specific service:
```bash
docker compose logs -f frontend
docker compose logs -f api
docker compose logs -f wikipedia-ingestion
docker compose logs -f database
```

### Restart a specific service:
```bash
docker compose restart <service-name>
```

### Stop all services:
```bash
docker compose down
```

### Stop and remove all data:
```bash
docker compose down -v
```

## Data Flow

1. **Wikipedia Ingestion** → Fetches events from Wikipedia API
2. **Database** → Stores events with temporal and categorical data
3. **API** → Exposes events via REST endpoints
4. **Frontend** → Visualizes events on interactive D3.js timeline

## Database Schema

### historical_events
- `id` - Primary key
- `title` - Event title from Wikipedia
- `description` - Event description (first paragraph)
- `start_year` - Start year of event
- `end_year` - End year of event (if applicable)
- `is_bc_start` - Whether start year is BC
- `is_bc_end` - Whether end year is BC
- `category` - Wikipedia category
- `wikipedia_url` - Link to Wikipedia article
- `created_at` - Record creation timestamp
- `updated_at` - Record update timestamp

## Troubleshooting

### Services won't start
- Make sure Docker and Docker Compose are installed and running
- Check if ports 3000, 5432, or 8000 are already in use
- Try `docker compose down -v` and then `docker compose up -d`

### No events appearing
- Wait a few minutes for Wikipedia ingestion to complete
- Check ingestion logs: `docker compose logs wikipedia-ingestion`
- Verify data was inserted: Access API at http://localhost:8000/stats

### Timeline not rendering
- Check browser console for authentication or CORS errors
- Verify the API is accessible with authentication (see [API Authentication](#api-authentication))
- Ensure the `API_CLIENT_SECRET` in docker-compose.yml matches the frontend configuration
- Check browser console for JavaScript errors
- Ensure events have valid year data

## License

MIT
