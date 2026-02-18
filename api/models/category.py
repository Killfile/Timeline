"""Category and upload data access helpers."""

from __future__ import annotations

from typing import Any


def fetch_category_by_id(conn, category_id: int) -> dict[str, Any] | None:
    """Fetch a category by id."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, name, description, strategy_name, metadata, created_by, created_at, updated_at
            FROM timeline_categories
            WHERE id = %s
            """,
            (category_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()
