# Phase 1: Data Model Design - Admin Timeline Management

**Date**: 2026-02-13  
**Branch**: 001-admin-timeline-management  
**Purpose**: Define database schema for users, roles, timeline categories, and ingestion uploads with relationships and constraints.

## Overview

This data model extends the existing Timeline database with admin authentication, role-based access control, and category management. The design follows PostgreSQL best practices with foreign key constraints, cascade deletes, and proper indexing for performance.

## Entity Relationship Diagram

```
┌─────────────┐       ┌──────────────┐       ┌─────────────┐
│   users     │───────│  user_roles  │───────│    roles    │
└─────────────┘   1:N └──────────────┘  N:1  └─────────────┘
      │ 1:N                                          │
      │                                              │
      │                                              │
      │ created_by                                   │
      │                                              │
      ▼ N:1                                          │
┌─────────────────────┐                             │
│ timeline_categories │                             │
└─────────────────────┘                             │
      │ 1:N                                          │
      │                                              │
      ├──────────────┬──────────────┐               │
      ▼              ▼              ▼               │
┌────────────┐ ┌─────────────┐ ┌─────────────────┐ │
│historical_ │ │ingestion_   │ │event_categories │ │
│events      │ │uploads      │ │(existing)       │ │
└────────────┘ └─────────────┘ └─────────────────┘ │
      │              │                               │
      │ 1:N          │ uploaded_by                   │
      ▼              └───────────────────────────────┘
┌──────────────┐
│event_        │
│enrichments   │
│(existing)    │
└──────────────┘
```

## Database Schema

### 1. Users Table

Stores user accounts with hashed passwords for authentication.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,  -- Argon2id PHC format string
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes
CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = TRUE;

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**Fields:**
- `id`: Auto-incrementing primary key
- `email`: Unique identifier for user login (case-insensitive in application)
- `password_hash`: Argon2id hash in PHC string format (e.g., `$argon2id$v=19$m=65536,t=3,p=4$...`)
- `is_active`: Soft delete flag (deactivated users cannot log in)
- `created_at`: Timestamp when user account was created
- `updated_at`: Timestamp of last modification (auto-updated via trigger)

**Constraints:**
- `email` must be unique (enforced at DB and application level)
- `password_hash` must never be NULL
- `is_active` defaults to TRUE

**Security Notes:**
- Never log or expose `password_hash` values
- Email validation performed at application layer
- Password strength requirements enforced at application layer (min 8 chars, no complexity rules)

---

### 2. Roles Table

Stores available roles (admin, user) for role-based access control.

```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes
CREATE UNIQUE INDEX idx_roles_name ON roles(name);

-- Seed data
INSERT INTO roles (name, description) VALUES
    ('admin', 'Administrator with full access to user and category management'),
    ('user', 'Regular user with standard timeline access (reserved for future features)')
ON CONFLICT (name) DO NOTHING;
```

**Fields:**
- `id`: Auto-incrementing primary key
- `name`: Unique role identifier (e.g., 'admin', 'user')
- `description`: Human-readable description of role permissions
- `created_at`: Timestamp when role was created

**Constraints:**
- `name` must be unique
- `name` values: 'admin', 'user' (extensible to 'moderator', 'editor', etc.)

**Business Rules:**
- Roles are relatively static (defined in seed data)
- Cannot delete a role if assigned to any users (enforced via CASCADE constraint on user_roles)
- Future expansion: Add `permissions` JSONB column for fine-grained scopes

---

### 3. User-Role Junction Table

Many-to-many relationship between users and roles.

```sql
CREATE TABLE user_roles (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    assigned_by INTEGER REFERENCES users(id),  -- Admin who assigned the role
    PRIMARY KEY (user_id, role_id)
);

-- Indexes
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role_id ON user_roles(role_id);
```

**Fields:**
- `user_id`: Foreign key to users table
- `role_id`: Foreign key to roles table
- `assigned_at`: Timestamp when role was assigned
- `assigned_by`: Foreign key to users table (admin who assigned the role, nullable for seed data)

**Constraints:**
- Composite primary key on (user_id, role_id) prevents duplicate assignments
- CASCADE DELETE: Deleting a user removes their role assignments
- CASCADE DELETE: Deleting a role removes all assignments of that role

**Business Rules:**
- A user can have multiple roles (e.g., admin + user)
- A user with no roles has no special permissions (public timeline access only)
- First admin user seeded via migration or setup script

---

### 4. Timeline Categories Table

Stores logical groupings of timeline events (e.g., 'Roman History', 'Food Timeline').

```sql
CREATE TABLE timeline_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    strategy_name VARCHAR(255),  -- Ingestion strategy identifier (e.g., 'timeline_of_food')
    metadata JSONB DEFAULT '{}'::jsonb,  -- Extensible metadata (tags, visibility, etc.)
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes
CREATE UNIQUE INDEX idx_timeline_categories_name ON timeline_categories(name);
CREATE INDEX idx_timeline_categories_strategy ON timeline_categories(strategy_name);
CREATE INDEX idx_timeline_categories_metadata ON timeline_categories USING gin(metadata);

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_timeline_categories_updated_at
    BEFORE UPDATE ON timeline_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**Fields:**
- `id`: Auto-incrementing primary key
- `name`: Human-readable category name (unique, e.g., 'Roman History')
- `description`: Optional long-form description of the category
- `strategy_name`: Identifier for the ingestion strategy that populated this category (e.g., 'timeline_of_food', 'wars')
- `metadata`: JSONB column for extensible properties (tags, visibility, color, icon, etc.)
- `created_by`: Foreign key to users table (admin who created the category)
- `created_at`: Timestamp when category was created
- `updated_at`: Timestamp of last modification

**Constraints:**
- `name` must be unique (case-sensitive in DB, case-insensitive in application)
- `created_by` ON DELETE SET NULL (preserve category if admin deleted)

**Business Rules:**
- Deleting a category cascades to `historical_events` (removes all events in that category)
- Renaming a category updates `updated_at` timestamp
- `strategy_name` links to ingestion pipeline (informational only, not enforced FK)

**Migration Path:**
- Existing `historical_events.category` VARCHAR column is preserved for backwards compatibility
- New `category_id` INTEGER column references `timeline_categories(id)`
- Migration script populates `timeline_categories` from unique values in `historical_events.category`

---

### 5. Historical Events Table (Modified)

Extend existing table with foreign key to timeline_categories.

```sql
-- Existing table structure (preserved)
-- CREATE TABLE historical_events (
--     id SERIAL PRIMARY KEY,
--     event_key TEXT UNIQUE NOT NULL,
--     title VARCHAR(500) NOT NULL,
--     description TEXT,
--     start_year INTEGER,
--     start_month INTEGER,
--     start_day INTEGER,
--     end_year INTEGER,
--     end_month INTEGER,
--     end_day INTEGER,
--     is_bc_start BOOLEAN DEFAULT FALSE,
--     is_bc_end BOOLEAN DEFAULT FALSE,
--     weight INTEGER,
--     precision NUMERIC(10, 2),
--     category VARCHAR(100),  -- Legacy column
--     wikipedia_url TEXT,
--     created_at TIMESTAMPTZ DEFAULT NOW(),
--     updated_at TIMESTAMPTZ DEFAULT NOW()
-- );

-- Migration: Add category_id foreign key
ALTER TABLE historical_events
ADD COLUMN category_id INTEGER REFERENCES timeline_categories(id) ON DELETE CASCADE;

-- Index for category queries
CREATE INDEX idx_historical_events_category_id ON historical_events(category_id);
```

**Changes:**
- **NEW**: `category_id INTEGER` references `timeline_categories(id)`
- **PRESERVED**: `category VARCHAR(100)` for legacy data
- **CASCADE**: Deleting a timeline_category removes all associated events

**Business Rules:**
- New events (from admin uploads) must have `category_id` set
- Legacy events may have `category` VARCHAR but no `category_id`
- Future migration can consolidate all categories into `timeline_categories` and remove VARCHAR column

**Performance:**
- Index on `category_id` supports efficient queries by category
- Existing indexes on `start_year`, `end_year`, `event_key` remain unchanged

---

### 6. Ingestion Uploads Table

Tracks admin file uploads for auditing and troubleshooting.

```sql
CREATE TABLE ingestion_uploads (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES timeline_categories(id) ON DELETE CASCADE,
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    filename VARCHAR(500) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    events_count INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,  -- 'success', 'failed', 'processing'
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,  -- Additional upload context (strategy, run_id, etc.)
    uploaded_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes
CREATE INDEX idx_ingestion_uploads_category_id ON ingestion_uploads(category_id);
CREATE INDEX idx_ingestion_uploads_uploaded_by ON ingestion_uploads(uploaded_by);
CREATE INDEX idx_ingestion_uploads_status ON ingestion_uploads(status);
CREATE INDEX idx_ingestion_uploads_uploaded_at ON ingestion_uploads(uploaded_at DESC);
```

**Fields:**
- `id`: Auto-incrementing primary key
- `category_id`: Foreign key to timeline_categories (which category was populated)
- `uploaded_by`: Foreign key to users (admin who uploaded the file)
- `filename`: Original filename (e.g., 'timeline_of_food.json')
- `file_size_bytes`: Size of uploaded file in bytes
- `events_count`: Number of events extracted from upload
- `status`: Upload processing status ('success', 'failed', 'processing')
- `error_message`: Detailed error if status is 'failed'
- `metadata`: JSONB for additional context (strategy name, run_id, etc.)
- `uploaded_at`: Timestamp of upload

**Constraints:**
- `category_id` must reference valid timeline_category
- `uploaded_by` ON DELETE SET NULL (preserve audit trail if admin deleted)
- `status` must be one of: 'success', 'failed', 'processing'

**Business Rules:**
- Each upload creates one record (even if it fails)
- `events_count` is 0 for failed uploads
- `error_message` populated only when status is 'failed'
- Admins can view upload history for debugging

**Use Cases:**
- Audit trail: Who uploaded what, when
- Troubleshooting: View error messages for failed uploads
- Analytics: Track ingestion success rates, file sizes, event counts

---

## Data Migration Strategy

### Step 1: Create New Tables (Migration 005)

```sql
-- 005_add_admin_tables.sql

-- Create update_updated_at_column function (if not exists)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create tables in dependency order
CREATE TABLE users (...);
CREATE TABLE roles (...);
CREATE TABLE user_roles (...);
CREATE TABLE timeline_categories (...);
ALTER TABLE historical_events ADD COLUMN category_id INTEGER REFERENCES timeline_categories(id) ON DELETE CASCADE;
CREATE TABLE ingestion_uploads (...);

-- Create indexes
CREATE UNIQUE INDEX idx_users_email ON users(email);
-- ... (all indexes from above)

-- Seed roles
INSERT INTO roles (name, description) VALUES (...);
```

### Step 2: Seed Admin User

Admin user created via setup script or manual SQL:

```sql
-- Create admin user with hashed password (generated via argon2-cffi)
INSERT INTO users (email, password_hash, is_active) VALUES
    ('admin@example.com', '$argon2id$v=19$m=65536,t=3,p=4$...', TRUE);

-- Assign admin role
INSERT INTO user_roles (user_id, role_id) VALUES
    ((SELECT id FROM users WHERE email = 'admin@example.com'),
     (SELECT id FROM roles WHERE name = 'admin'));
```

### Step 3: Populate Timeline Categories (Optional)

Migrate existing category data to new table:

```sql
-- Extract unique categories from historical_events
INSERT INTO timeline_categories (name, description, strategy_name)
SELECT DISTINCT
    category AS name,
    NULL AS description,
    COALESCE(s.name, 'unknown') AS strategy_name
FROM historical_events he
LEFT JOIN strategies s ON he.strategy_id = s.id
WHERE he.category IS NOT NULL
ON CONFLICT (name) DO NOTHING;

-- Update historical_events with category_id
UPDATE historical_events he
SET category_id = tc.id
FROM timeline_categories tc
WHERE he.category = tc.name;
```

---

## Data Access Patterns

### 1. User Authentication (Login)

```sql
-- Lookup user by email
SELECT id, email, password_hash, is_active
FROM users
WHERE email = $1 AND is_active = TRUE;

-- Fetch user roles for JWT claims
SELECT r.name
FROM user_roles ur
JOIN roles r ON ur.role_id = r.id
WHERE ur.user_id = $1;
```

**Performance**: O(1) via unique index on `users.email`, O(N) for roles (typically N=1-2)

### 2. Admin User Management

```sql
-- List all users with roles
SELECT
    u.id,
    u.email,
    u.is_active,
    u.created_at,
    ARRAY_AGG(r.name) AS roles
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
GROUP BY u.id
ORDER BY u.created_at DESC;

-- Create user and assign role (two queries)
INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING id;
INSERT INTO user_roles (user_id, role_id) VALUES ($1, (SELECT id FROM roles WHERE name = $2));

-- Change password
UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2;

-- Deactivate user (soft delete)
UPDATE users SET is_active = FALSE, updated_at = NOW() WHERE id = $1;
```

### 3. Timeline Category Management

```sql
-- List all categories with event counts
SELECT
    tc.id,
    tc.name,
    tc.description,
    tc.created_at,
    COUNT(he.id) AS events_count
FROM timeline_categories tc
LEFT JOIN historical_events he ON tc.id = he.category_id
GROUP BY tc.id
ORDER BY tc.name;

-- Create category
INSERT INTO timeline_categories (name, description, strategy_name, created_by)
VALUES ($1, $2, $3, $4)
RETURNING id;

-- Update category name
UPDATE timeline_categories
SET name = $1, updated_at = NOW()
WHERE id = $2;

-- Delete category (cascades to historical_events and ingestion_uploads)
DELETE FROM timeline_categories WHERE id = $1;
```

### 4. JSON Upload Processing

```sql
-- Record upload
INSERT INTO ingestion_uploads (category_id, uploaded_by, filename, file_size_bytes, events_count, status)
VALUES ($1, $2, $3, $4, $5, 'processing')
RETURNING id;

-- Insert events (via existing database_loader.py)
-- ... (bulk insert historical_events with category_id)

-- Update upload status
UPDATE ingestion_uploads
SET status = 'success', events_count = $1
WHERE id = $2;

-- Record failure
UPDATE ingestion_uploads
SET status = 'failed', error_message = $1
WHERE id = $2;
```

---

## Data Integrity Rules

### Foreign Key Constraints

1. **user_roles.user_id → users.id**: CASCADE DELETE
   - Deleting a user removes their role assignments

2. **user_roles.role_id → roles.id**: CASCADE DELETE
   - Deleting a role removes all assignments (should be prevented in application)

3. **timeline_categories.created_by → users.id**: SET NULL
   - Preserve category if creating admin is deleted

4. **historical_events.category_id → timeline_categories.id**: CASCADE DELETE
   - Deleting a category removes all its events

5. **ingestion_uploads.category_id → timeline_categories.id**: CASCADE DELETE
   - Deleting a category removes upload history

6. **ingestion_uploads.uploaded_by → users.id**: SET NULL
   - Preserve audit trail if admin is deleted

### Unique Constraints

- `users.email`: Prevent duplicate accounts
- `roles.name`: Prevent duplicate role definitions
- `timeline_categories.name`: Prevent duplicate category names
- `historical_events.event_key`: Existing constraint for enrichment association

### Business Logic Validation (Application Layer)

- Email format validation (RFC 5322)
- Password strength requirements (min 8 chars, complexity)
- Category name format (no special chars, max 255 chars)
- Role assignment: Only admins can assign roles
- Upload size limits (5 MB max)
- JSON schema validation before insertion

---

## Performance Considerations

### Indexing Strategy

**Primary Indexes:**
- `users.email` (UNIQUE): O(1) login lookups
- `timeline_categories.name` (UNIQUE): O(1) category lookups
- `historical_events.category_id`: O(log N) category event queries
- `ingestion_uploads.uploaded_at DESC`: O(log N) recent upload queries

**Composite Indexes:**
- `user_roles(user_id, role_id)`: PRIMARY KEY for junction queries

**Partial Indexes:**
- `users.is_active`: Only index active users (reduces index size)

**GIN Indexes:**
- `timeline_categories.metadata`: JSONB queries (future use)

### Query Optimization

**Avoid N+1 Queries:**
- Use `LEFT JOIN` + `ARRAY_AGG()` to fetch users with roles in single query
- Preload category event counts with `COUNT()` aggregation

**Batch Operations:**
- Bulk insert events from JSON upload (use `executemany()` or `COPY`)
- Transaction wrapping for upload processing (rollback on error)

**Connection Pooling:**
- Reuse existing `psycopg2` connection pool in API service

---

## Testing Strategy

### Unit Tests (Data Layer)

**test_user_model.py:**
- Create user with valid/invalid data
- Unique email constraint violation
- Password hash storage (never plaintext)
- Soft delete (is_active flag)

**test_role_model.py:**
- Seed roles exist ('admin', 'user')
- Role assignment/removal
- Cannot delete role with active assignments

**test_category_model.py:**
- Create/update/delete category
- Cascade delete to historical_events
- Unique category name constraint

**test_upload_model.py:**
- Record upload with success/failure status
- Audit trail preservation

### Integration Tests (Service Layer)

**test_user_service.py:**
- User CRUD operations
- Password change
- Role assignment/revocation
- List users with roles

**test_category_service.py:**
- Category CRUD operations
- Cascade delete verification
- Upload processing (JSON → database)

**test_upload_service.py:**
- JSON validation
- Event insertion
- Upload status tracking
- Error handling

### Fixtures

```python
# conftest.py additions
@pytest.fixture
def admin_user(db_conn):
    """Create admin user with hashed password."""
    from argon2 import PasswordHasher
    ph = PasswordHasher()
    password_hash = ph.hash("admin123")
    
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
        ("admin@test.com", password_hash)
    )
    user_id = cursor.fetchone()[0]
    
    # Assign admin role
    cursor.execute(
        "INSERT INTO user_roles (user_id, role_id) VALUES (%s, (SELECT id FROM roles WHERE name = 'admin'))",
        (user_id,)
    )
    db_conn.commit()
    return user_id

@pytest.fixture
def timeline_category(db_conn, admin_user):
    """Create sample timeline category."""
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO timeline_categories (name, description, created_by) VALUES (%s, %s, %s) RETURNING id",
        ("Test Category", "Test description", admin_user)
    )
    category_id = cursor.fetchone()[0]
    db_conn.commit()
    return category_id
```

---

## Security Considerations

### Password Storage
- **NEVER** store plaintext passwords
- Use Argon2id PHC format: `$argon2id$v=19$m=65536,t=3,p=4$...`
- Configure hashing params for 0.2-0.5s latency
- Rehash on login if params outdated

### SQL Injection Prevention
- Use parameterized queries (psycopg2 `%s` placeholders)
- Never concatenate user input into SQL strings
- Validate input at application layer before DB queries

### Cascade Delete Safety
- Cascade deletes are intentional and documented
- Warn admins before deleting categories (UI confirmation)
- Log all cascade deletes for audit trail

### Audit Logging
- Log all admin operations (user CRUD, role assignments, category changes, uploads)
- Include context: admin_id, target_id, action, timestamp
- Store logs in structured format (JSON) for analysis

---

## Future Enhancements

### Phase 2 (Future)
- **User Profiles**: Add `first_name`, `last_name`, `avatar_url` to users table
- **Password Reset**: Add `password_reset_tokens` table (no email integration yet)
- **Granular Permissions**: Add `permissions` JSONB to roles for fine-grained scopes
- **Category Visibility**: Add `is_public` BOOLEAN to timeline_categories
- **Category Hierarchy**: Add `parent_id` for nested categories (e.g., 'History' → 'Roman History')
- **Event Versioning**: Track changes to events in `event_history` table
- **Rate Limiting**: Add `api_rate_limits` table for per-user limits

### Phase 3 (Future)
- **Multi-tenancy**: Add `organizations` table for isolated data partitions
- **Collaboration**: Add `category_permissions` for user-level access control
- **Webhooks**: Add `webhooks` table for upload/category change notifications

---

## Summary

This data model provides a solid foundation for admin timeline management with:
- **Authentication**: Secure user accounts with Argon2id password hashing
- **Authorization**: Role-based access control with user-role assignments
- **Categories**: Logical grouping of events with admin-managed metadata
- **Audit**: Complete upload history with success/failure tracking
- **Integrity**: Foreign key constraints with appropriate cascade behavior
- **Performance**: Strategic indexing for common query patterns
- **Extensibility**: JSONB columns for future metadata expansion

The schema integrates seamlessly with existing tables (`historical_events`, `event_enrichments`, `event_categories`) and follows PostgreSQL best practices for maintainability and scalability.
