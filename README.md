# Timeline

A containerized application that ingests historical events from Wikipedia and displays them as an interactive, filterable, zoomable timeline using D3.js.

## Features

- **Wikipedia Data Ingestion**: Automatically fetches historical events from Wikipedia articles
- **Time-Series Database**: Stores events with BC/AD date support
- **RESTful API**: FastAPI backend for querying historical events
- **Interactive D3.js Timeline**: Zoomable and pannable timeline visualization
- **Filtering & Search**: Filter by category or search by keywords
- **Event Details**: Click on any event to see detailed information and Wikipedia links

## Architecture

This application consists of four containerized services:

1. **PostgreSQL Database** - Stores historical events with temporal data (BC/AD support)
2. **Wikipedia Ingestion Service** - Python service that fetches events from Wikipedia API
3. **API Service** - FastAPI backend providing endpoints for timeline data
4. **Frontend** - Interactive D3.js visualization with zoom, pan, and filtering capabilities

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

**Endpoints**:
- `GET /` - API information
- `GET /health` - Health check
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
- Verify the API is accessible: http://localhost:8000/health
- Check browser console for JavaScript errors
- Ensure events have valid year data

## License

MIT
