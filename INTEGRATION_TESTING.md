# Integration Testing Guide

## Local Development (No Docker Exposure)

### Quick Start

1. **Start the test database** (short-lived, isolated):
   ```bash
   ./scripts/test-db-start
   ```

2. **Run integration tests locally**:
   ```bash
   pytest api/tests/integration/
   # No environment variables needed!
   ```

3. **Stop the test database** when done:
   ```bash
   ./scripts/test-db-stop
   ```

### How It Works

- **Local testing** (default) uses a separate test database container on port 5433
- Database is isolated to your machine and only runs while you're testing
- `conftest.py` defaults to `localhost:5433` for developer convenience
- Docker containers set `POSTGRES_HOST=database` via docker-compose.yml to override the default
- After tests complete, cleanup removes all volumes and the container

### Advantages

✅ Database is **never exposed publicly**  
✅ **Isolated test environment** - doesn't interfere with production data  
✅ **Quick setup/teardown** - just run the scripts  
✅ **No Docker port conflicts** - uses port 5433 instead of 5432  
✅ **Compatible with CI/CD** - Docker execution still works normally

---

## Docker Container Execution

When tests run **inside Docker** (e.g., in CI/CD or with `docker-compose exec -T api pytest`):

- Docker-compose sets `POSTGRES_HOST=database` to override the default
- `conftest.py` detects `POSTGRES_HOST=database` and connects to the Docker database service
- Uses existing main database on port 5432
- Works exactly as before

### Running tests in Docker

```bash
# Inside the container
docker-compose exec -T api pytest tests/integration/

# Or directly
docker-compose run --rm api pytest tests/integration/
```

---

## Environment Variables Reference

| Variable | Local Test (Default) | Docker (Override) | Purpose |
|----------|---------------------|-------------------|---------||
| `POSTGRES_HOST` | `localhost` (default) | `database` (set by docker-compose) | Signals execution mode |
| `DB_HOST` | `localhost` | `database` | Actual connection host |
| `DB_PORT` | `5433` | `5432` | Database port |
| `DB_NAME` | `timeline_history` | `timeline_history` | Database name |
| `DB_USER` | `timeline_user` | `timeline_user` | Database user |
| `DB_PASSWORD` | `timeline_pass` | `timeline_pass` | Database password |

---

## Troubleshooting

### Tests still can't connect

```bash
# Verify test database is running
docker ps | grep timeline-test-db

# Check database is healthy
docker-compose -f docker-compose.test.yml ps

# View database logs
docker-compose -f docker-compose.test.yml logs test-database
```

### Tests pass once but fail on second run

The test databases need cleanup between runs:
```bash
./scripts/test-db-stop
./scripts/test-db-start
POSTGRES_HOST=localhost pytest tests/integration/
```

### Port 5433 already in use

Either:
1. Kill the process using port 5433
2. Edit `docker-compose.test.yml` to use a different port
3. Stop the test database: `./scripts/test-db-stop`

---

## Development Workflow

```bash
# Start test db (one terminal)
./scripts/test-db-start

# In another terminal, run tests repeatedly
POSTGRES_HOST=localhost pytest tests/integration/ -v

# When done, stop test db
./scripts/test-db-stop
```

Or with auto-reload:
```bash
POSTGRES_HOST=localhost pytest tests/integration/ -v --tb=short -x -s
```
