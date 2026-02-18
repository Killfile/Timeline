"""Unit tests for category service."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from api.services.category_service import (
    CategoryService,
    validate_import_schema,
    list_categories,
    get_category,
    create_category,
    update_category,
    delete_category,
    process_upload,
)


class TestValidateImportSchema:
    """Tests for JSON schema validation."""

    def test_validate_valid_schema(self):
        """Test validation passes for valid schema."""
        valid_data = {
            "strategy": "test_strategy",
            "run_id": "20260217T120000Z",
            "generated_at_utc": "2026-02-17T12:00:00Z",
            "event_count": 1,
            "metadata": {
                "total_events_found": 1,
                "total_events_parsed": 1,
                "sections_identified": 1,
                "parsing_start_utc": "2026-02-17T12:00:00Z",
                "parsing_end_utc": "2026-02-17T12:01:00Z",
                "elapsed_seconds": 60.0,
                "events_per_second": 0.017,
                "confidence_distribution": {
                    "explicit": 1,
                    "inferred": 0,
                    "approximate": 0,
                    "contentious": 0,
                    "fallback": 0,
                    "legendary": 0
                },
                "undated_events": {
                    "total_undated": 0,
                    "events": []
                }
            },
            "events": [
                {
                    "title": "Test Event 1",
                    "start_year": 2026,
                    "end_year": 2026,
                    "is_bc_start": False,
                    "is_bc_end": False,
                    "precision": 1.0,
                    "weight": 5,
                    "url": "https://en.wikipedia.org/test",
                    "span_match_notes": "Found in article text",
                    "description": "Test Event 1 description",
                    "category": "Test Category"
                }
            ]
        }
        
        is_valid, errors = validate_import_schema(valid_data)
        assert is_valid
        assert errors is None
        assert errors is None

    def test_validate_missing_required_field(self):
        """Test validation fails for missing required fields."""
        invalid_data = {
            "strategy": "test_strategy",
            # Missing required fields
        }
        
        is_valid, errors = validate_import_schema(invalid_data)
        assert not is_valid
        assert errors is not None
        assert len(errors) > 0

    def test_validate_invalid_run_id_format(self):
        """Test validation fails for invalid run_id format."""
        invalid_data = {
            "strategy": "test_strategy",
            "run_id": "invalid_format",  # Should be YYYYMMDDTHHMMSSZ
            "generated_at_utc": "2026-02-17T12:00:00Z",
            "event_count": 0,
            "metadata": {
                "total_events_found": 0,
                "total_events_parsed": 0,
                "sections_identified": 0,
                "parsing_start_utc": "2026-02-17T12:00:00Z",
                "parsing_end_utc": "2026-02-17T12:01:00Z",
                "elapsed_seconds": 60.0,
                "events_per_second": 0.0,
                "confidence_distribution": {
                    "explicit": 0,
                    "inferred": 0,
                    "approximate": 0,
                    "contentious": 0,
                    "fallback": 0,
                    "legendary": 0
                },
                "undated_events": {
                    "total_undated": 0,
                    "events": []
                }
            },
            "events": []
        }
        
        is_valid, errors = validate_import_schema(invalid_data)
        assert not is_valid
        assert "run_id" in str(errors).lower()


class TestListCategories:
    """Tests for listing categories."""

    def test_list_categories_success(self):
        """Test successful category listing."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "name": "Test Category",
                "description": "Description",
                "strategy_name": "test_strategy",
                "metadata": {},
                "created_by": 1,
                "created_at": "2026-02-17T12:00:00Z",
                "updated_at": "2026-02-17T12:00:00Z"
            }
        ]
        
        categories = list_categories(mock_conn)
        assert len(categories) == 1
        assert categories[0]["name"] == "Test Category"

    def test_list_categories_empty(self):
        """Test listing categories when none exist."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        categories = list_categories(mock_conn)
        assert categories == []


class TestGetCategory:
    """Tests for getting a single category."""

    def test_get_category_success(self):
        """Test successful category retrieval."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "name": "Test Category",
            "description": "Description",
            "strategy_name": "test_strategy",
            "metadata": {},
            "created_by": 1,
            "created_at": "2026-02-17T12:00:00Z",
            "updated_at": "2026-02-17T12:00:00Z"
        }
        
        category = get_category(mock_conn, 1)
        assert category is not None
        assert category["name"] == "Test Category"

    def test_get_category_not_found(self):
        """Test getting non-existent category."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        category = get_category(mock_conn, 999)
        assert category is None


class TestCreateCategory:
    """Tests for creating categories."""

    def test_create_category_success(self):
        """Test successful category creation."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "name": "New Category",
            "description": "Description",
            "strategy_name": "test_strategy",
            "metadata": {},
            "created_by": 1,
            "created_at": "2026-02-17T12:00:00Z",
            "updated_at": "2026-02-17T12:00:00Z"
        }
        
        category = create_category(
            mock_conn,
            name="New Category",
            description="Description",
            strategy_name="test_strategy",
            metadata={},
            created_by=1
        )
        
        assert category is not None
        assert category["name"] == "New Category"
        mock_conn.commit.assert_called_once()

    def test_create_category_duplicate_name(self):
        """Test creating category with duplicate name."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Simulate unique constraint violation
        import psycopg2
        mock_cursor.execute.side_effect = psycopg2.IntegrityError("duplicate key")
        
        with pytest.raises(ValueError, match="already exists"):
            create_category(
                mock_conn,
                name="Duplicate Category",
                description="Description",
                strategy_name="test_strategy",
                metadata={},
                created_by=1
            )


class TestUpdateCategory:
    """Tests for updating categories."""

    def test_update_category_success(self):
        """Test successful category update."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "name": "Updated Category",
            "description": "New Description",
            "strategy_name": "test_strategy",
            "metadata": {},
            "created_by": 1,
            "created_at": "2026-02-17T12:00:00Z",
            "updated_at": "2026-02-17T12:05:00Z"
        }
        
        category = update_category(
            mock_conn,
            category_id=1,
            name="Updated Category",
            description="New Description"
        )
        
        assert category is not None
        assert category["name"] == "Updated Category"
        mock_conn.commit.assert_called_once()

    def test_update_category_not_found(self):
        """Test updating non-existent category."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        category = update_category(
            mock_conn,
            category_id=999,
            name="Updated"
        )
        
        assert category is None


class TestDeleteCategory:
    """Tests for deleting categories."""

    def test_delete_category_success(self):
        """Test successful category deletion."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        deleted = delete_category(mock_conn, 1)
        assert deleted is True
        mock_conn.commit.assert_called_once()

    def test_delete_category_not_found(self):
        """Test deleting non-existent category."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 0
        
        deleted = delete_category(mock_conn, 999)
        assert deleted is False


class TestProcessUpload:
    """Tests for upload processing."""

    def test_process_upload_success_new_category(self):
        """Test successful upload creating new category."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock category doesn't exist
        mock_cursor.fetchone.side_effect = [
            None,  # Category doesn't exist
            {"id": 1}  # Category created
        ]
        
        upload_data = {
            "strategy": "test_strategy",
            "run_id": "20260217T120000Z",
            "generated_at_utc": "2026-02-17T12:00:00Z",
            "event_count": 1,
            "metadata": {
                "total_events_found": 1,
                "total_events_parsed": 1,
                "sections_identified": 1,
                "parsing_start_utc": "2026-02-17T12:00:00Z",
                "parsing_end_utc": "2026-02-17T12:01:00Z",
                "elapsed_seconds": 60.0,
                "events_per_second": 0.017,
                "confidence_distribution": {
                    "explicit": 1,
                    "inferred": 0,
                    "approximate": 0,
                    "contentious": 0,
                    "fallback": 0,
                    "legendary": 0
                },
                "undated_events": {
                    "total_undated": 0,
                    "events": []
                }
            },
            "events": [
                {
                    "title": "Test Event",
                    "start_year": 2026,
                    "end_year": 2026,
                    "is_bc_start": False,
                    "is_bc_end": False,
                    "precision": 1.0,
                    "weight": 5,
                    "url": "https://en.wikipedia.org/test",
                    "span_match_notes": "Found in article text",
                    "description": "Test Event description",
                    "category": "Test Category"
                }
            ]
        }
        
        result = process_upload(
            mock_conn,
            upload_data=upload_data,
            category_name="Test Category",
            uploaded_by=1,
            overwrite=False
        )
        
        assert result["category_id"] == 1
        assert result["events_inserted"] == 1

    def test_process_upload_reject_existing_category(self):
        """Test upload rejected when category exists without overwrite."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock category exists
        mock_cursor.fetchone.return_value = {"id": 1, "name": "Existing Category"}
        
        upload_data = {
            "strategy": "test_strategy",
            "run_id": "20260217T120000Z",
            "generated_at_utc": "2026-02-17T12:00:00Z",
            "event_count": 0,
            "metadata": {
                "total_events_found": 0,
                "total_events_parsed": 0,
                "sections_identified": 0,
                "parsing_start_utc": "2026-02-17T12:00:00Z",
                "parsing_end_utc": "2026-02-17T12:01:00Z",
                "elapsed_seconds": 60.0,
                "events_per_second": 0.0,
                "confidence_distribution": {
                    "explicit": 0,
                    "inferred": 0,
                    "approximate": 0,
                    "contentious": 0,
                    "fallback": 0,
                    "legendary": 0
                },
                "undated_events": {
                    "total_undated": 0,
                    "events": []
                }
            },
            "events": []
        }
        
        with pytest.raises(ValueError, match="already exists"):
            process_upload(
                mock_conn,
                upload_data=upload_data,
                category_name="Existing Category",
                uploaded_by=1,
                overwrite=False
            )

    def test_process_upload_overwrite_existing_category(self):
        """Test upload overwrites existing category when overwrite=True."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock category exists
        mock_cursor.fetchone.return_value = {"id": 1, "name": "Existing Category"}
        mock_cursor.rowcount = 5  # 5 events deleted
        
        upload_data = {
            "strategy": "test_strategy",
            "run_id": "20260217T120000Z",
            "generated_at_utc": "2026-02-17T12:00:00Z",
            "event_count": 2,
            "metadata": {
                "total_events_found": 2,
                "total_events_parsed": 2,
                "sections_identified": 1,
                "parsing_start_utc": "2026-02-17T12:00:00Z",
                "parsing_end_utc": "2026-02-17T12:01:00Z",
                "elapsed_seconds": 60.0,
                "events_per_second": 0.033,
                "confidence_distribution": {
                    "explicit": 2,
                    "inferred": 0,
                    "approximate": 0,
                    "contentious": 0,
                    "fallback": 0,
                    "legendary": 0
                },
                "undated_events": {
                    "total_undated": 0,
                    "events": []
                }
            },
            "events": [
                {
                    "title": "Test Event 1",
                    "start_year": 2026,
                    "end_year": 2026,
                    "is_bc_start": False,
                    "is_bc_end": False,
                    "precision": 1.0,
                    "weight": 5,
                    "url": "https://en.wikipedia.org/test1",
                    "span_match_notes": "Found in article text",
                    "description": "Test Event 1 description",
                    "category": "Test Category"
                },
                {
                    "title": "Test Event 2",
                    "start_year": 2025,
                    "end_year": 2025,
                    "is_bc_start": False,
                    "is_bc_end": False,
                    "precision": 1.0,
                    "weight": 5,
                    "url": "https://en.wikipedia.org/test2",
                    "span_match_notes": "Found in article text",
                    "description": "Test Event 2 description",
                    "category": "Test Category"
                }
            ]
        }
        
        result = process_upload(
            mock_conn,
            upload_data=upload_data,
            category_name="Existing Category",
            uploaded_by=1,
            overwrite=True
        )
        
        assert result["category_id"] == 1
        assert result["events_deleted"] == 5
        assert result["events_inserted"] == 2
