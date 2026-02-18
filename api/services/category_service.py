"""Category service for managing timeline categories and uploads."""

import json
import jsonschema
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import os


def _load_import_schema() -> Dict:
    """Load the import schema JSON."""
    # Build a path that works in both local and Docker environments
    # Local: /Users/chris/Timeline/api/services/ → navigate to wikipedia-ingestion/
    # Docker: /app/api/services/ → navigate to wikipedia-ingestion/
    
    service_dir = os.path.dirname(__file__)  # e.g., /app/api/services or /Users/chris/Timeline/api/services
    
    # Navigate up to project root (2 levels up: services/ → api/ → app/)
    project_root = os.path.dirname(os.path.dirname(service_dir))
    
    # Schema should be at: {project_root}/wikipedia-ingestion/import_schema.json
    schema_path = os.path.join(project_root, "wikipedia-ingestion", "import_schema.json")
    schema_path = os.path.normpath(schema_path)
    
    if not os.path.exists(schema_path):
        # Fallback: try from environment or current working directory
        fallback_paths = [
            os.environ.get("SCHEMA_PATH"),  # If explicitly set
            os.path.join(os.getcwd(), "wikipedia-ingestion", "import_schema.json"),
            "wikipedia-ingestion/import_schema.json",
        ]
        
        for fallback in fallback_paths:
            if fallback and os.path.exists(fallback):
                schema_path = os.path.normpath(fallback)
                break
        else:
            # None of the paths worked
            raise FileNotFoundError(
                f"Schema file not found.\n"
                f"Tried: {schema_path}\n"
                f"Current working directory: {os.getcwd()}\n"
                f"Service directory: {service_dir}\n"
                f"Project root: {project_root}"
            )
    
    with open(schema_path, "r") as f:
        return json.load(f)


def validate_import_schema(data: Dict) -> Tuple[bool, Optional[List[str]]]:
    """
    Validate upload data against import schema.
    
    Args:
        data: Upload data to validate
        
    Returns:
        Tuple of (is_valid, errors)
    """
    try:
        schema = _load_import_schema()
        jsonschema.validate(instance=data, schema=schema)
        return (True, None)
    except jsonschema.ValidationError as e:
        return (False, [str(e)])
    except jsonschema.SchemaError as e:
        return (False, [f"Invalid schema: {str(e)}"])
    except Exception as e:
        return (False, [f"Validation error: {str(e)}"])


def list_categories(conn) -> List[Dict]:
    """
    List all timeline categories.
    
    Args:
        conn: Database connection
        
    Returns:
        List of category dictionaries
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                id,
                name,
                description,
                strategy_name,
                metadata,
                created_by,
                created_at,
                updated_at
            FROM timeline_categories
            ORDER BY name ASC
        """)
        categories = cur.fetchall()
        return [dict(cat) for cat in categories]


def get_category(conn, category_id: int) -> Optional[Dict]:
    """
    Get a single category by ID.
    
    Args:
        conn: Database connection
        category_id: Category ID
        
    Returns:
        Category dictionary or None if not found
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                id,
                name,
                description,
                strategy_name,
                metadata,
                created_by,
                created_at,
                updated_at
            FROM timeline_categories
            WHERE id = %s
        """, (category_id,))
        category = cur.fetchone()
        return dict(category) if category else None


def create_category(
    conn,
    name: str,
    description: Optional[str] = None,
    strategy_name: Optional[str] = None,
    metadata: Optional[Dict] = None,
    created_by: Optional[int] = None
) -> Dict:
    """
    Create a new timeline category.
    
    Args:
        conn: Database connection
        name: Category name (must be unique)
        description: Optional category description
        strategy_name: Optional strategy name
        metadata: Optional metadata dictionary
        created_by: Optional user ID who created the category
        
    Returns:
        Created category dictionary
        
    Raises:
        ValueError: If category name already exists
    """
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO timeline_categories (
                name,
                description,
                strategy_name,
                metadata,
                created_by
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING 
                id,
                name,
                description,
                strategy_name,
                metadata,
                created_by,
                created_at,
                updated_at
        """, (
            name,
            description,
            strategy_name,
            json.dumps(metadata) if metadata else '{}',
            created_by
        ))
        category = cur.fetchone()
        cur.close()
        conn.commit()
        return dict(category)
    except Exception as e:
        conn.rollback()
        # Check if this is an integrity error (duplicate key, etc.)
        error_msg = str(e).lower()
        if "unique constraint" in error_msg or "duplicate" in error_msg or isinstance(e, psycopg2.IntegrityError):
            raise ValueError(f"Category with name '{name}' already exists")
        raise


def update_category(
    conn,
    category_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    strategy_name: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Optional[Dict]:
    """
    Update an existing category.
    
    Args:
        conn: Database connection
        category_id: Category ID to update
        name: Optional new name
        description: Optional new description
        strategy_name: Optional new strategy name
        metadata: Optional new metadata
        
    Returns:
        Updated category dictionary or None if not found
    """
    # Build dynamic update query
    updates = []
    params = []
    
    if name is not None:
        updates.append("name = %s")
        params.append(name)
    
    if description is not None:
        updates.append("description = %s")
        params.append(description)
    
    if strategy_name is not None:
        updates.append("strategy_name = %s")
        params.append(strategy_name)
    
    if metadata is not None:
        updates.append("metadata = %s")
        params.append(json.dumps(metadata))
    
    if not updates:
        # No updates provided, just return current category
        return get_category(conn, category_id)
    
    updates.append("updated_at = NOW()")
    params.append(category_id)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = f"""
                UPDATE timeline_categories
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING 
                    id,
                    name,
                    description,
                    strategy_name,
                    metadata,
                    created_by,
                    created_at,
                    updated_at
            """
            cur.execute(query, params)
            category = cur.fetchone()
            
            if category:
                conn.commit()
                return dict(category)
            else:
                conn.rollback()
                return None
    except psycopg2.IntegrityError as e:
        conn.rollback()
        if "unique constraint" in str(e).lower():
            raise ValueError(f"Category with name '{name}' already exists")
        raise


def delete_category(conn, category_id: int) -> bool:
    """
    Delete a category and all associated events (CASCADE).
    
    Args:
        conn: Database connection
        category_id: Category ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM timeline_categories
            WHERE id = %s
        """, (category_id,))
        deleted = cur.rowcount > 0
        
        if deleted:
            conn.commit()
        else:
            conn.rollback()
        
        return deleted


def process_upload(
    conn,
    upload_data: Dict,
    category_name: str,
    uploaded_by: int,
    overwrite: bool = False
) -> Dict[str, Any]:
    """
    Process a JSON upload and create/update category with events.
    
    Args:
        conn: Database connection
        upload_data: Validated upload JSON data
        category_name: Name for the category
        uploaded_by: User ID who uploaded
        overwrite: If True, overwrite existing category; if False, reject duplicates
        
    Returns:
        Dictionary with upload results (category_id, events_inserted, events_deleted)
        
    Raises:
        ValueError: If category exists and overwrite=False
    """
    result = {
        "category_id": None,
        "events_inserted": 0,
        "events_deleted": 0
    }
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if category exists
            cur.execute("""
                SELECT id, name FROM timeline_categories
                WHERE name = %s
            """, (category_name,))
            existing_category = cur.fetchone()
            
            if existing_category:
                if not overwrite:
                    raise ValueError(
                        f"Category '{category_name}' already exists. "
                        "Set overwrite=True to replace it."
                    )
                
                # Delete existing events
                cur.execute("""
                    DELETE FROM historical_events
                    WHERE category_id = %s
                """, (existing_category["id"],))
                result["events_deleted"] = cur.rowcount
                
                category_id = existing_category["id"]
                
                # Update category metadata
                cur.execute("""
                    UPDATE timeline_categories
                    SET 
                        strategy_name = %s,
                        metadata = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    upload_data.get("strategy"),
                    json.dumps(upload_data.get("metadata", {})),
                    category_id
                ))
            else:
                # Create new category
                cur.execute("""
                    INSERT INTO timeline_categories (
                        name,
                        description,
                        strategy_name,
                        metadata,
                        created_by
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    category_name,
                    f"Imported from {upload_data.get('strategy', 'unknown')}",
                    upload_data.get("strategy"),
                    json.dumps(upload_data.get("metadata", {})),
                    uploaded_by
                ))
                category_id = cur.fetchone()["id"]
            
            result["category_id"] = category_id
            
            # Insert events
            events = upload_data.get("events", [])
            for event in events:
                # Generate event_key from title, years, and description (deterministic)
                import hashlib
                event_key_input = f"{event.get('title')}|{event.get('start_year')}|{event.get('end_year')}|{event.get('description')}"
                event_key = hashlib.sha256(event_key_input.encode()).hexdigest()
                
                # Prefer uploaded weight; fall back to computed weight if missing
                if "weight" in event and event.get("weight") is not None:
                    weight = int(event.get("weight"))
                else:
                    # Calculate weight from precision and span as a fallback
                    precision = event.get("precision", 1.0)
                    span_days = abs(event.get("end_year", event.get("start_year")) - event.get("start_year", 0)) * 365
                    weight = int(precision * span_days) if precision and span_days else 0
                
                cur.execute("""
                    INSERT INTO historical_events (
                        event_key,
                        title,
                        description,
                        start_year,
                        start_month,
                        start_day,
                        end_year,
                        end_month,
                        end_day,
                        is_bc_start,
                        is_bc_end,
                        weight,
                        precision,
                        category,
                        wikipedia_url,
                        category_id,
                        strategy_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            (SELECT id FROM strategies WHERE name = %s LIMIT 1))
                    ON CONFLICT (event_key) DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        category = EXCLUDED.category,
                        category_id = EXCLUDED.category_id,
                        updated_at = NOW()
                """, (
                    event_key,
                    event["title"],
                    event.get("description"),
                    event["start_year"],
                    event.get("start_month"),
                    event.get("start_day"),
                    event.get("end_year"),
                    event.get("end_month"),
                    event.get("end_day"),
                    event.get("is_bc_start", False),
                    event.get("is_bc_end", False),
                    weight,
                    event.get("precision", 1.0),
                    event.get("category"),
                    event.get("url"),
                    category_id,
                    upload_data.get("strategy")
                ))
                result["events_inserted"] += 1
            
            # Record upload in ingestion_uploads table
            cur.execute("""
                INSERT INTO ingestion_uploads (
                    category_id,
                    uploaded_by,
                    filename,
                    file_size_bytes,
                    events_count,
                    status,
                    metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                category_id,
                uploaded_by,
                f"{upload_data.get('strategy')}_{upload_data.get('run_id')}.json",
                len(json.dumps(upload_data)),
                len(events),
                "completed",
                json.dumps({
                    "run_id": upload_data.get("run_id"),
                    "generated_at_utc": upload_data.get("generated_at_utc"),
                    "overwrite": overwrite
                })
            ))
            
            conn.commit()
            return result
            
    except Exception as e:
        conn.rollback()
        raise


class CategoryService:
    """Service class for category operations (alternative interface)."""
    
    def __init__(self, conn):
        self.conn = conn
    
    def list_categories(self) -> List[Dict]:
        return list_categories(self.conn)
    
    def get_category(self, category_id: int) -> Optional[Dict]:
        return get_category(self.conn, category_id)
    
    def create_category(
        self,
        name: str,
        description: Optional[str] = None,
        strategy_name: Optional[str] = None,
        metadata: Optional[Dict] = None,
        created_by: Optional[int] = None
    ) -> Dict:
        return create_category(
            self.conn, name, description, strategy_name, metadata, created_by
        )
    
    def update_category(
        self,
        category_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        strategy_name: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[Dict]:
        return update_category(
            self.conn, category_id, name, description, strategy_name, metadata
        )
    
    def delete_category(self, category_id: int) -> bool:
        return delete_category(self.conn, category_id)
    
    def process_upload(
        self,
        upload_data: Dict,
        category_name: str,
        uploaded_by: int,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        return process_upload(
            self.conn, upload_data, category_name, uploaded_by, overwrite
        )
    
    @staticmethod
    def validate_import_schema(data: Dict) -> Tuple[bool, Optional[List[str]]]:
        return validate_import_schema(data)
