# Phase 0: Research - Admin Timeline Management

**Date**: 2026-02-13  
**Branch**: 001-admin-timeline-management  
**Purpose**: Resolve technical unknowns and establish design decisions for admin authentication, RBAC, password management, JSON validation, and file upload security.

## 1. Password Hashing Strategy

### Decision: Argon2id via argon2-cffi or pwdlib

**Rationale:**
- **Industry Standard**: Argon2id won the Password Hashing Competition (2015) and is recommended by OWASP
- **Security**: Combines Argon2i (side-channel resistant) and Argon2d (GPU-resistant) for best security
- **Performance**: Configurable to target 0.2-0.5s hashing time (OWASP recommendation for interactive logins)
- **PHC Format**: Standard storage format: `$argon2id$v=19$m=65536,t=3,p=4$saltbase64$hashbase64`

**Libraries Evaluated:**
1. **argon2-cffi** (Python bindings to C implementation)
   - Pros: Fast, battle-tested, widely used
   - Cons: Requires C compiler for installation
   - Recommendation: Use for production

2. **pwdlib** (Pure Python, wraps argon2-cffi)
   - Pros: High-level API, migration-aware (rehash on login if params outdated)
   - Cons: Additional abstraction layer
   - Recommendation: Use if API simplicity preferred

**Configuration:**
- Memory: 64 MiB (OWASP minimum: 19 MiB for interactive logins)
- Iterations: 3 (OWASP minimum: 2)
- Parallelism: 4 threads
- Salt: 16 bytes random (auto-generated)
- Output: 32 bytes hash

**Implementation Pattern:**
```python
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost=3,        # iterations
    memory_cost=65536,  # 64 MiB
    parallelism=4,      # threads
    hash_len=32,        # output hash length
    salt_len=16         # salt length
)

# Hash password on registration/change
password_hash = ph.hash("user_password")  # Returns PHC string

# Verify password on login
try:
    ph.verify(password_hash, "user_password")  # Raises on mismatch
    if ph.check_needs_rehash(password_hash):
        # Rehash with updated params if needed
        password_hash = ph.hash("user_password")
except VerifyMismatchError:
    # Invalid password
    pass
```

**Storage:**
- Database column: `password_hash TEXT NOT NULL`
- Never log or expose password hashes
- Rehash on login if `check_needs_rehash()` returns True

**Alternatives Considered:**
- bcrypt: Older, less memory-hard (vulnerable to ASICs)
- scrypt: Good but less adoption than Argon2
- PBKDF2: Computationally expensive but GPU-vulnerable

---

## 2. Role-Based Access Control (RBAC) with JWT Cookies

### Decision: Roles + Scopes in JWT Claims with FastAPI Dependencies

**Rationale:**
- **Stateless**: No server-side session storage needed
- **Standards-Based**: JWT claims (`sub`, `roles`, `scopes`) are well-understood
- **Granular**: Roles (admin/user) + scopes (fine-grained permissions) support future expansion
- **FastAPI Native**: Dependency injection pattern integrates cleanly with existing auth

**JWT Claims Structure:**
```json
{
  "sub": "user123",           // User ID
  "email": "admin@example.com",
  "roles": ["admin"],         // Role names
  "scopes": ["users:write", "categories:write"],  // Fine-grained permissions
  "iat": 1675000000,
  "exp": 1675003600,
  "jti": "uuid-token-id"
}
```

**Implementation Pattern:**

**1. Extend JWT Service:**
```python
# auth/jwt_service.py
def generate_token(config: AuthConfig, user_id: str, roles: List[str], scopes: List[str]) -> TokenPayload:
    claims = {
        "sub": user_id,
        "roles": roles,
        "scopes": scopes,
        "iat": int(_utcnow().timestamp()),
        "exp": int((_utcnow() + timedelta(seconds=config.token_ttl_seconds)).timestamp()),
        "jti": str(uuid4())
    }
    token = jwt.encode(claims, config.jwt_secret, algorithm="HS256")
    return TokenPayload(token=token, ...)
```

**2. Create RBAC Dependency:**
```python
# auth/rbac.py
from typing import Set
from fastapi import Depends, HTTPException, status
from auth.auth_dependency import get_current_token

def get_current_principal(token: dict = Depends(get_current_token)):
    """Extract user principal from JWT token."""
    return {
        "user_id": token.get("sub"),
        "roles": set(token.get("roles", [])),
        "scopes": set(token.get("scopes", []))
    }

def require_roles(required_roles: Set[str]):
    """Dependency factory to require specific roles."""
    def role_checker(principal: dict = Depends(get_current_principal)):
        user_roles = principal["roles"]
        if not required_roles.intersection(user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {required_roles}"
            )
        return principal
    return role_checker

def require_scopes(required_scopes: Set[str]):
    """Dependency factory to require specific scopes."""
    def scope_checker(principal: dict = Depends(get_current_principal)):
        user_scopes = principal["scopes"]
        if not required_scopes.issubset(user_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required scopes: {required_scopes}"
            )
        return principal
    return scope_checker
```

**3. Protect Admin Endpoints:**
```python
# api/api.py
from auth.rbac import require_roles

@app.post("/admin/users")
def create_user(
    user_data: UserCreate,
    principal: dict = Depends(require_roles({"admin"}))
):
    # Only admins can create users
    return user_service.create_user(user_data)

@app.get("/admin/categories")
def list_categories(
    principal: dict = Depends(require_roles({"admin"}))
):
    # Only admins can list categories
    return category_service.list_categories()
```

**Role Design:**
- **admin**: Full access to user management, category management, uploads
- **user**: Regular user (reserved for future features, not required for MVP)

**Scope Design (Future Expansion):**
- `users:read`, `users:write`, `users:delete`
- `categories:read`, `categories:write`, `categories:delete`
- `uploads:write`

**Alternatives Considered:**
- Session-based auth: Requires Redis/DB storage, not stateless
- Middleware-based RBAC: Less flexible than per-endpoint dependencies
- OAuth2 scopes only: Roles provide coarser-grained grouping, simplify admin checks

---

## 3. JSON Schema Validation for Uploads

### Decision: jsonschema Library with Draft 2020-12 and Precompiled Validators

**Rationale:**
- **Standards-Based**: jsonschema implements JSON Schema specification (Draft 2020-12)
- **Performance**: Precompiling validators amortizes schema parsing cost
- **Security**: Built-in format validators, size limits, and $ref resolution controls
- **Existing Schema**: Project already has `import_schema.json` defining event structure

**Implementation Pattern:**

**1. Install and Configure:**
```bash
pip install jsonschema
```

**2. Precompile Validator:**
```python
# services/category_service.py
import json
from pathlib import Path
from jsonschema import Draft202012Validator, ValidationError

# Load and compile schema once at module load
SCHEMA_PATH = Path(__file__).parent.parent.parent / "wikipedia-ingestion" / "import_schema.json"
with open(SCHEMA_PATH) as f:
    IMPORT_SCHEMA = json.load(f)
    
VALIDATOR = Draft202012Validator(IMPORT_SCHEMA)
```

**3. Validate Upload:**
```python
def validate_upload(upload_content: dict) -> Tuple[bool, Optional[str]]:
    """Validate uploaded JSON against import schema.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        VALIDATOR.validate(upload_content)
        return (True, None)
    except ValidationError as e:
        error_msg = f"Validation failed at {'.'.join(str(p) for p in e.absolute_path)}: {e.message}"
        return (False, error_msg)
```

**4. Upload Endpoint with Validation:**
```python
@app.post("/admin/uploads")
async def upload_timeline_json(
    file: UploadFile,
    principal: dict = Depends(require_roles({"admin"}))
):
    # 1. Size check (FastAPI can enforce max_size in UploadFile)
    if file.size > 10 * 1024 * 1024:  # 10 MB
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")
    
    # 2. Content-type check
    if file.content_type != "application/json":
        raise HTTPException(status_code=415, detail="Must be application/json")
    
    # 3. Parse JSON
    try:
        content = await file.read()
        upload_data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    
    # 4. Schema validation
    is_valid, error_msg = validate_upload(upload_data)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # 5. Process upload (insert events, create category)
    return category_service.process_upload(upload_data, principal["user_id"])
```

**Security Controls:**
- **Size Limit**: 10 MB max (configured in FastAPI or web server)
- **Content-Type**: Validate `application/json` header
- **Schema Validation**: Reject unknown properties with `additionalProperties: false`
- **$ref Resolution**: Disable remote $ref resolution to prevent SSRF attacks
- **Streaming**: Use async file reading to avoid memory exhaustion

**Performance:**
- Precompiled validators: ~10-100x faster than parsing schema on each request
- Use `orjson` for faster JSON parsing if needed (5-10x faster than stdlib)

**Alternatives Considered:**
- Pydantic models: More Pythonic but harder to share schema with ingestion pipeline
- Custom validation: Reinventing the wheel, error-prone
- No validation: Security risk, allows malformed data into database

---

## 4. File Upload Security Limits

### Decision: 10 MB Max, Content-Type Validation, Streaming with Byte Limits

**Rationale:**
- **10 MB Limit**: Timeline JSON files can exceed 5 MB for large categories; 10 MB provides headroom
- **Content-Type Validation**: Prevent upload of executables or HTML disguised as JSON
- **Streaming**: Avoid loading entire file into memory, enforce byte limits during upload
- **FastAPI Integration**: Use `UploadFile` with size/type checks before processing

**Implementation Pattern:**

**1. FastAPI Upload with Limits:**
```python
from fastapi import File, UploadFile, HTTPException

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

@app.post("/admin/uploads")
async def upload_timeline_json(
    file: UploadFile = File(...),
    principal: dict = Depends(require_roles({"admin"}))
):
    # 1. Content-Type validation
    if file.content_type not in ["application/json", "text/json"]:
        raise HTTPException(
            status_code=415,
            detail="Invalid content type. Expected application/json"
        )
    
    # 2. Size validation (streaming with byte limit)
    chunks = []
    total_size = 0
    
    while chunk := await file.read(8192):  # Read 8KB at a time
        total_size += len(chunk)
        if total_size > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE / 1024 / 1024} MB"
            )
        chunks.append(chunk)
    
    # 3. Parse JSON
    try:
        content = b"".join(chunks).decode("utf-8")
        upload_data = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    
    # 4. Proceed with validation and processing
    ...
```

**2. Nginx/Web Server Limits (Defense in Depth):**
```nginx
# frontend/nginx.conf
client_max_body_size 11M;  # Slightly larger than app limit
client_body_timeout 30s;   # Prevent slow-loris attacks
```

**Security Controls:**
- **Request Timeout**: 30-60s to prevent slowloris attacks
- **Rate Limiting**: Existing rate limiter can be extended to uploads
- **File Type Whitelist**: Only allow `application/json`, reject executables
- **Virus Scanning**: Not required for JSON (no executable content)
- **Logging**: Log upload metadata (user_id, filename, size, timestamp)

**Error Handling:**
- **413 Payload Too Large**: File exceeds 10 MB
- **415 Unsupported Media Type**: Content-Type not application/json
- **400 Bad Request**: JSON parsing or schema validation failed
- **500 Internal Server Error**: Database insertion failed (logged)

**Monitoring:**
- Log all uploads: `admin_upload: user_id={user_id} filename={filename} size={size} status={status}`
- Track upload failures by error type for security monitoring

**Alternatives Considered:**
- S3/Object Storage: Overkill for 10 MB files, adds complexity
- Virus Scanning: Not needed for JSON (no executable content)
- 20 MB Limit: Unnecessarily large for timeline data

---

## 5. Database Schema Design Considerations

### Key Entities and Relationships

**1. Users Table:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,  -- Argon2id PHC string
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**2. Roles Table:**
```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,  -- 'admin', 'user'
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**3. User-Role Junction Table:**
```sql
CREATE TABLE user_roles (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);
```

**4. Timeline Categories Table:**
```sql
CREATE TABLE timeline_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,  -- 'Roman History', 'Food Timeline'
    description TEXT,
    strategy_name VARCHAR(255),  -- Reference to ingestion strategy
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add category_id to historical_events (replaces/augments existing category VARCHAR)
ALTER TABLE historical_events
ADD COLUMN category_id INTEGER REFERENCES timeline_categories(id) ON DELETE CASCADE;
```

**5. Ingestion Uploads Table:**
```sql
CREATE TABLE ingestion_uploads (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES timeline_categories(id) ON DELETE CASCADE,
    uploaded_by INTEGER REFERENCES users(id),
    filename VARCHAR(500) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    events_count INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,  -- 'success', 'failed', 'processing'
    error_message TEXT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Cascade Constraints:**
- Deleting a user cascades to `user_roles` (removes role assignments)
- Deleting a role cascades to `user_roles` (removes assignments for that role)
- Deleting a category cascades to `historical_events` (removes category events)
- Deleting a category cascades to `ingestion_uploads` (removes upload records)

**Indexing:**
- `users.email` (unique index, for login lookups)
- `historical_events.category_id` (for category event queries)
- `ingestion_uploads.category_id` (for upload history queries)

**Migration Path:**
- Existing `historical_events.category` VARCHAR column is preserved for legacy data
- New `category_id` column is nullable initially, populated via admin uploads
- Future migration can consolidate categories into `timeline_categories` table

---

## 6. Existing Codebase Integration Points

**Authentication:**
- **Current**: Cookie-based JWT auth in `api/auth/` (jwt_service.py, auth_dependency.py)
- **Extension**: Add roles/scopes to JWT claims, create RBAC dependencies
- **Testing**: Existing conftest.py has auth fixtures (timeline_auth_test cookie, test-jwt-secret-67890)

**Database:**
- **Current**: PostgreSQL with migrations in `database/migrations/`
- **Extension**: Add migration 005_add_admin_tables.sql for new tables
- **Connection**: Existing `api.get_db_connection()` can be reused

**Ingestion:**
- **Current**: `wikipedia-ingestion/database_loader.py` handles JSON ingestion
- **Extension**: Expose as service for admin upload processing
- **Schema**: `import_schema.json` defines event structure

**Frontend:**
- **Current**: `frontend/candidate/` contains production UI
- **Extension**: Add admin.html, admin.js, admin.css for admin UI
- **Auth**: Leverage existing cookie-based auth (check for admin role in JWT)

---

## 7. Testing Strategy

**Unit Tests:**
- Password hashing: hash, verify, rehash detection
- RBAC dependencies: role checks, scope checks, error handling
- User service: create, update, delete, password change
- Category service: create, update, delete, cascade effects
- JSON validation: valid uploads, invalid schemas, size limits

**Integration Tests:**
- Admin authentication: login as admin, access admin endpoints
- User endpoints: CRUD operations with admin auth
- Category endpoints: CRUD operations with admin auth
- Upload endpoints: JSON upload, validation failures, processing

**Fixtures:**
- Admin user with hashed password (seed in conftest.py)
- Sample roles (admin, user) with assignments
- Sample timeline categories
- Valid/invalid JSON uploads for testing

**Coverage Target:**
- 80%+ for all new code
- 100% for password hashing and RBAC (security-critical)

---

## 8. Performance Considerations

**Password Hashing:**
- Target: 0.2-0.5s per hash (OWASP recommendation)
- Impact: Only on registration/password change (low frequency)
- Mitigation: Configurable Argon2 params for deployment environment

**JSON Validation:**
- Precompiled validators: <1ms for typical timeline JSON (~1 MB)
- Size limit: 10 MB prevents memory exhaustion
- Streaming upload: Avoids loading entire file into memory

**Database Queries:**
- User lookup by email: O(1) with unique index
- Role check: O(1) via JWT claims (no DB query needed)
- Category cascade delete: PostgreSQL handles efficiently with ON DELETE CASCADE

**API Response Time:**
- Target: <200ms p95 for admin endpoints
- Monitoring: Add structured logging with request duration

---

## Summary of Research Decisions

| Area | Decision | Key Libraries |
|------|----------|---------------|
| **Password Hashing** | Argon2id with PHC format | argon2-cffi or pwdlib |
| **RBAC** | Roles + scopes in JWT claims | FastAPI dependencies |
| **JSON Validation** | Draft 2020-12 with precompiled validators | jsonschema |
| **Upload Security** | 10 MB limit, content-type validation, streaming | FastAPI UploadFile |
| **Database** | New tables for users, roles, categories | PostgreSQL with migrations |
| **Testing** | pytest with mocks for DB/HTTP | pytest, unittest.mock |

**Next Steps:**
- Phase 1: Create data-model.md with detailed database schema
- Phase 1: Create contracts/ with OpenAPI specs for admin endpoints
- Phase 1: Create quickstart.md with setup instructions
- Phase 2: Create tasks.md with implementation roadmap
