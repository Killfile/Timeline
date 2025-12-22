# Timeline

A containerized application for event tracking and visualization, built with Docker Compose.

## Architecture

This application consists of five interconnected tiers:

1. **PostgreSQL with TimescaleDB** - Time-series optimized database for storing event data
2. **Data Ingestion Layer** - Python service that generates and ingests raw event data
3. **ETL Layer** - Python service that transforms raw events into processed production data
4. **API Layer** - FastAPI service that provides RESTful endpoints for data access
5. **Frontend** - React application for visualizing and interacting with event data

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
   docker-compose up -d
   ```

4. Access the application:
   - **Frontend**: http://localhost:3000
   - **API**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs
   - **Database**: localhost:5432

## Services

### Database (PostgreSQL with TimescaleDB)
- **Port**: 5432
- **Database**: timeline
- Automatically initialized with tables and hypertables
- Optimized for time-series event data

### Ingestion Service
- Continuously generates and ingests sample event data
- Supports multiple event types: user actions, page views, API calls, errors
- Simulates data from multiple sources (web_app, mobile_app, api_gateway)

### ETL Service
- Processes raw events into structured production data
- Extracts meaningful values and enriches metadata
- Runs continuously, processing new events as they arrive

### API Service
- **Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs

**Endpoints**:
- `GET /` - API information
- `GET /health` - Health check
- `GET /events` - List processed events (with filtering)
- `GET /summary` - Event summary by type
- `GET /stats` - Overall statistics
- `GET /event-types` - List all event types
- `GET /sources` - List all data sources

### Frontend Service
- React-based dashboard for data visualization
- Real-time updates (refreshes every 10 seconds)
- Interactive charts and tables
- Event filtering by type, source, and time range

## Development

### View logs for all services:
```bash
docker-compose logs -f
```

### View logs for a specific service:
```bash
docker-compose logs -f frontend
docker-compose logs -f api
docker-compose logs -f etl
docker-compose logs -f ingestion
docker-compose logs -f database
```

### Restart a specific service:
```bash
docker-compose restart <service-name>
```

### Stop all services:
```bash
docker-compose down
```

### Stop and remove all data:
```bash
docker-compose down -v
```

## Data Flow

1. **Ingestion** → Raw events are generated and stored in `raw_events` table
2. **ETL** → Raw events are processed and transformed into `processed_events` table
3. **API** → Processed events are exposed via REST endpoints
4. **Frontend** → Data is visualized in the React dashboard

## Database Schema

### raw_events
- `id` - Primary key
- `event_time` - Event timestamp (TimescaleDB hypertable partitioned on this)
- `event_type` - Type of event
- `event_data` - JSONB data payload
- `source` - Data source
- `ingested_at` - Ingestion timestamp

### processed_events
- `id` - Primary key
- `event_time` - Event timestamp (TimescaleDB hypertable partitioned on this)
- `event_type` - Type of event
- `event_value` - Extracted numeric value
- `event_metadata` - Enriched metadata
- `source` - Data source
- `processed_at` - Processing timestamp

## Troubleshooting

### Services won't start
- Make sure Docker and Docker Compose are installed and running
- Check if ports 3000, 5432, or 8000 are already in use
- Try `docker-compose down -v` and then `docker-compose up -d`

### No data appearing
- Wait a few moments for the ingestion service to generate data
- Check ingestion logs: `docker-compose logs ingestion`
- Check ETL logs: `docker-compose logs etl`

### Frontend can't connect to API
- Verify the API is running: `docker-compose ps`
- Check API health: http://localhost:8000/health
- Ensure REACT_APP_API_URL is set correctly in .env

## License

MIT