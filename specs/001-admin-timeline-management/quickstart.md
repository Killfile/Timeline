# Quickstart Guide: Admin Timeline Management

**Date**: 2026-02-13  
**Branch**: 001-admin-timeline-management  
**Purpose**: Get the admin timeline management feature up and running quickly.

## Overview

This guide walks you through setting up the admin timeline management feature, including database migrations, creating the first admin user, and testing the authentication flow.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ environment
- Access to existing Timeline repository
- Postgres database running (via `docker compose up database`)

## 1. Database Setup

### Run Migration

Create and apply the new database migration for admin tables:

```bash
# Create migration file
cat > database/migrations/005_add_admin_tables.sql << 'EOF'
-- Migration 005: Add admin authentication and category management tables

-- Create update_updated_at_column function (if not exists)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = TRUE;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Roles table
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE UNIQUE INDEX idx_roles_name ON roles(name);

-- Seed roles
INSERT INTO roles (name, description) VALUES
    ('admin', 'Administrator with full access to user and category management'),
    ('user', 'Regular user with standard timeline access (reserved for future features)')
ON CONFLICT (name) DO NOTHING;

-- User-Role junction table
CREATE TABLE user_roles (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    assigned_by INTEGER REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role_id ON user_roles(role_id);

-- Timeline Categories table
CREATE TABLE timeline_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    strategy_name VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE UNIQUE INDEX idx_timeline_categories_name ON timeline_categories(name);
CREATE INDEX idx_timeline_categories_strategy ON timeline_categories(strategy_name);
CREATE INDEX idx_timeline_categories_metadata ON timeline_categories USING gin(metadata);

CREATE TRIGGER update_timeline_categories_updated_at
    BEFORE UPDATE ON timeline_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add category_id to historical_events (new foreign key)
ALTER TABLE historical_events
ADD COLUMN category_id INTEGER REFERENCES timeline_categories(id) ON DELETE CASCADE;

CREATE INDEX idx_historical_events_category_id ON historical_events(category_id);

-- Ingestion Uploads table
CREATE TABLE ingestion_uploads (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES timeline_categories(id) ON DELETE CASCADE,
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    filename VARCHAR(500) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    events_count INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    uploaded_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_ingestion_uploads_category_id ON ingestion_uploads(category_id);
CREATE INDEX idx_ingestion_uploads_uploaded_by ON ingestion_uploads(uploaded_by);
CREATE INDEX idx_ingestion_uploads_status ON ingestion_uploads(status);
CREATE INDEX idx_ingestion_uploads_uploaded_at ON ingestion_uploads(uploaded_at DESC);
EOF

# Apply migration (database container must be running)
docker compose exec database psql -U timeline_user -d timeline_history -f /docker-entrypoint-initdb.d/migrations/005_add_admin_tables.sql
```

**Verification:**

```bash
# Verify tables were created
docker compose exec database psql -U timeline_user -d timeline_history -c "\dt"

# Should see: users, roles, user_roles, timeline_categories, ingestion_uploads

# Verify roles were seeded
docker compose exec database psql -U timeline_user -d timeline_history -c "SELECT * FROM roles;"
```

## 2. Install Python Dependencies

Add new dependencies to API service:

```bash
cd api/

# Add to requirements.txt
cat >> requirements.txt << 'EOF'
argon2-cffi==23.1.0
jsonschema==4.21.1
EOF

# Rebuild API container to install dependencies
docker compose build api
```

## 3. Create First Admin User

Use Python script to create an admin user with hashed password:

```bash
# Create seed script
cat > api/seed_admin.py << 'EOF'
"""Seed initial admin user for timeline management."""

import os
import sys
from argon2 import PasswordHasher
import psycopg2

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'database'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'timeline_history'),
    'user': os.getenv('DB_USER', 'timeline_user'),
    'password': os.getenv('DB_PASSWORD', 'timeline_pass')
}

def create_admin_user(email: str, password: str):
    """Create admin user with hashed password."""
    ph = PasswordHasher(
        time_cost=3,
        memory_cost=65536,  # 64 MiB
        parallelism=4,
        hash_len=32,
        salt_len=16
    )
    
    password_hash = ph.hash(password)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Insert user
        cursor.execute(
            "INSERT INTO users (email, password_hash, is_active) VALUES (%s, %s, %s) RETURNING id",
            (email, password_hash, True)
        )
        user_id = cursor.fetchone()[0]
        
        # Assign admin role
        cursor.execute(
            "INSERT INTO user_roles (user_id, role_id) VALUES (%s, (SELECT id FROM roles WHERE name = 'admin'))",
            (user_id,)
        )
        
        conn.commit()
        print(f"✅ Admin user created: {email} (ID: {user_id})")
        
    except psycopg2.errors.UniqueViolation:
        print(f"❌ User with email {email} already exists")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python seed_admin.py <email> <password>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    if len(password) < 8:
        print("❌ Password must be at least 8 characters")
        sys.exit(1)
    
    create_admin_user(email, password)
EOF

# Run seed script (API container must be running)
docker compose exec api python seed_admin.py admin@example.com AdminPassword123

# Expected output: ✅ Admin user created: admin@example.com (ID: 1)
```

**Verification:**

```bash
# Verify admin user was created
docker compose exec database psql -U timeline_user -d timeline_history -c "
    SELECT u.id, u.email, u.is_active, r.name AS role
    FROM users u
    JOIN user_roles ur ON u.id = ur.user_id
    JOIN roles r ON ur.role_id = r.id
    WHERE u.email = 'admin@example.com';
"

# Expected output:
# id | email               | is_active | role
# ---+---------------------+-----------+------
#  1 | admin@example.com   | t         | admin
```

## 4. Test Authentication Flow

### Method 1: Using curl

```bash
# Test login (should return JWT cookie)
curl -v -X POST http://localhost:8000/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "AdminPassword123"}' \
  -c cookies.txt

# Expected response: 200 OK with Set-Cookie header
# {"message": "Login successful", "user": {"id": 1, "email": "admin@example.com", "roles": ["admin"]}}

# Test accessing protected endpoint
curl -v http://localhost:8000/admin/me -b cookies.txt

# Expected response: 200 OK
# {"id": 1, "email": "admin@example.com", "roles": ["admin"], "is_active": true, "created_at": "..."}

# Test logout
curl -v -X POST http://localhost:8000/admin/logout -b cookies.txt

# Expected response: 200 OK with cleared cookie
```

### Method 2: Using Python script

```python
# test_auth.py
import requests

BASE_URL = "http://localhost:8000"

# Login
response = requests.post(
    f"{BASE_URL}/admin/login",
    json={"email": "admin@example.com", "password": "AdminPassword123"}
)
print(f"Login: {response.status_code}")
print(f"Response: {response.json()}")

# Access protected endpoint
response = requests.get(
    f"{BASE_URL}/admin/me",
    cookies=response.cookies
)
print(f"Get current user: {response.status_code}")
print(f"Response: {response.json()}")
```

## 5. Environment Variables

Ensure the following environment variables are set for the API service:

```bash
# API JWT configuration (add to docker-compose.yml or .env)
API_JWT_SECRET=your-production-secret-here-min-32-chars
COOKIE_NAME=timeline_auth
COOKIE_SECURE=true  # Set to false for local development
COOKIE_SAMESITE=strict
TOKEN_TTL_SECONDS=3600  # 1 hour

# Rate limiting
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_BURST=5
```

**Example docker-compose.yml update:**

```yaml
services:
  api:
    environment:
      - API_JWT_SECRET=${API_JWT_SECRET:-dev-jwt-secret-min-32-characters}
      - COOKIE_NAME=timeline_auth
      - COOKIE_SECURE=false  # true in production
      - COOKIE_SAMESITE=lax
      - TOKEN_TTL_SECONDS=3600
```

## 6. Frontend Setup

The frontend admin UI will be created in Phase 2 (tasks implementation). For now, you can interact with the API using:

- **curl**: Command-line testing (examples above)
- **Postman**: Import OpenAPI specs from `specs/001-admin-timeline-management/contracts/`
- **Python requests**: Automated testing and scripting

## 7. Troubleshooting

### Issue: Migration fails with "relation already exists"

**Solution:** Check if tables already exist from a previous run:

```bash
docker compose exec database psql -U timeline_user -d timeline_history -c "\dt"

# If tables exist, drop them first (WARNING: deletes data)
docker compose exec database psql -U timeline_user -d timeline_history -c "
    DROP TABLE IF EXISTS ingestion_uploads CASCADE;
    DROP TABLE IF EXISTS user_roles CASCADE;
    DROP TABLE IF EXISTS timeline_categories CASCADE;
    DROP TABLE IF EXISTS users CASCADE;
    DROP TABLE IF EXISTS roles CASCADE;
"

# Then re-run migration
```

### Issue: Admin user creation fails with "connection refused"

**Solution:** Ensure database container is running:

```bash
docker compose ps database

# If not running, start it
docker compose up -d database

# Wait 5 seconds for PostgreSQL to initialize
sleep 5

# Retry seed script
```

### Issue: Login returns 401 "Invalid credentials"

**Checklist:**
1. Verify admin user exists: `docker compose exec database psql -U timeline_user -d timeline_history -c "SELECT * FROM users;"`
2. Check password hash format: Should start with `$argon2id$`
3. Ensure correct password in login request
4. Check API logs: `docker compose logs api`

### Issue: Protected endpoint returns 403 "Insufficient permissions"

**Checklist:**
1. Verify user has admin role: `SELECT * FROM user_roles WHERE user_id = 1;`
2. Check JWT token contains roles claim (decode token at jwt.io)
3. Ensure cookie is being sent in request (use `-b cookies.txt` with curl)
4. Check API logs for detailed error: `docker compose logs api`

## 8. Testing Strategy

### Unit Tests

Run unit tests for password hashing and RBAC:

```bash
# From api/ directory
pytest tests/unit/test_password_service.py -v
pytest tests/unit/test_rbac.py -v
```

### Integration Tests

Run integration tests for authentication flow:

```bash
# From api/ directory
pytest tests/integration/test_admin_auth.py -v
pytest tests/integration/test_user_endpoints.py -v
```

### Manual Testing Checklist

- [ ] Can create admin user via seed script
- [ ] Can login with valid credentials (returns JWT cookie)
- [ ] Cannot login with invalid credentials (returns 401)
- [ ] Can access `/admin/me` with valid cookie
- [ ] Cannot access `/admin/me` without cookie (returns 401)
- [ ] Can logout (clears cookie)
- [ ] Password is hashed (not plaintext in database)
- [ ] Admin role is correctly assigned

## 9. Next Steps

After completing this quickstart:

1. **Phase 2: Implementation**
   - Implement user management endpoints (`/admin/users`)
   - Implement category management endpoints (`/admin/categories`)
   - Implement JSON upload endpoint (`/admin/uploads`)
   - Create frontend admin UI (`frontend/candidate/admin.html`)

2. **Phase 3: Testing**
   - Write comprehensive unit tests
   - Write integration tests for all endpoints
   - Test cascade deletes (category → events)
   - Test JSON schema validation

3. **Phase 4: Deployment**
   - Update production environment variables
   - Run database migration in production
   - Create production admin user
   - Deploy updated API container

## 10. Reference Links

- **Specification**: [spec.md](spec.md)
- **Implementation Plan**: [plan.md](plan.md)
- **Research**: [research.md](research.md)
- **Data Model**: [data-model.md](data-model.md)
- **API Contracts**:
  - [auth.openapi.yaml](contracts/auth.openapi.yaml)
  - [users.openapi.yaml](contracts/users.openapi.yaml)
  - [categories.openapi.yaml](contracts/categories.openapi.yaml)

## 11. Common Commands Reference

```bash
# Database
docker compose exec database psql -U timeline_user -d timeline_history

# API logs
docker compose logs -f api

# Rebuild API after code changes
docker compose build api && docker compose up -d api

# Run specific test file
docker compose exec api pytest tests/integration/test_admin_auth.py -v

# Create new admin user
docker compose exec api python seed_admin.py newadmin@example.com SecurePass456

# Check database table
docker compose exec database psql -U timeline_user -d timeline_history -c "SELECT * FROM users;"
```

## 12. Security Best Practices

✅ **Do:**
- Use strong passwords (min 8 chars, mix of letters/numbers/symbols)
- Set `COOKIE_SECURE=true` in production (requires HTTPS)
- Use `COOKIE_SAMESITE=strict` for CSRF protection
- Generate unique `API_JWT_SECRET` for production (min 32 characters)
- Regularly update Argon2 parameters if hashing becomes too fast (< 0.2s)
- Monitor failed login attempts via API logs

❌ **Don't:**
- Use default secrets in production
- Store passwords in plaintext anywhere
- Log JWT tokens or password hashes
- Disable `is_active` check for authentication
- Allow admin users to delete their own accounts
- Skip database backups before running migrations

---

**Setup Complete!** You should now have a working admin authentication system. Proceed to Phase 2 implementation to build out the full feature.
