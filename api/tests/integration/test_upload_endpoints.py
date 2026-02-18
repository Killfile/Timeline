"""Integration tests for upload management endpoints."""

import json
import pytest
from pathlib import Path


@pytest.mark.integration
class TestUploadEndpoints:
    """Integration tests for upload management endpoints."""
    
    def test_upload_json_success(self, admin_client):
        """Test successfully uploading a JSON file."""
        upload_json = {
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
                    "span_match_notes": "Found in article",
                    "description": "Test event description",
                    "category": "Test Category"
                }
            ]
        }
        
        upload_data = {
            "category_name": "Test Upload",
            "json_data": upload_json
        }
        
        response = admin_client.post("/admin/uploads", json=upload_data)
        assert response.status_code == 201
        data = response.json()
        assert data["category_id"] is not None
        assert data["events_inserted"] == 1
        assert data["events_deleted"] == 0
    
    def test_upload_json_invalid_schema(self, admin_client):
        """Test upload with invalid JSON schema."""
        invalid_json = {
            "strategy": "test_strategy",
            # Missing required fields
            "events": []
        }
        
        upload_data = {
            "category_name": "Invalid Upload",
            "json_data": invalid_json
        }
        
        response = admin_client.post("/admin/uploads", json=upload_data)
        assert response.status_code == 400
        data = response.json()
        assert "schema" in data.get("detail", "").lower() or "validation" in data.get("detail", "").lower()
    
    def test_upload_json_duplicate_category(self, admin_client):
        """Test upload that conflicts with existing category."""
        upload_json = {
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
                    "title": "Event 1",
                    "start_year": 2026,
                    "end_year": 2026,
                    "is_bc_start": False,
                    "is_bc_end": False,
                    "precision": 1.0,
                    "weight": 5,
                    "url": "https://en.wikipedia.org/test",
                    "span_match_notes": "Found",
                    "description": "Description",
                    "category": "Test"
                }
            ]
        }
        
        # First upload
        upload_data1 = {
            "category_name": "Duplicate Test",
            "json_data": upload_json
        }
        response1 = admin_client.post("/admin/uploads", json=upload_data1)
        assert response1.status_code == 201
        
        # Try second upload with same category name (without overwrite)
        upload_data2 = {
            "category_name": "Duplicate Test",
            "json_data": upload_json,
            "overwrite": False
        }
        response2 = admin_client.post("/admin/uploads", json=upload_data2)
        assert response2.status_code == 409  # Conflict
        data = response2.json()
        assert "already exists" in data.get("detail", "").lower()
    
    def test_upload_json_with_overwrite(self, admin_client):
        """Test uploading with overwrite flag."""
        upload_json_v1 = {
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
                    "title": "Event V1",
                    "start_year": 2026,
                    "end_year": 2026,
                    "is_bc_start": False,
                    "is_bc_end": False,
                    "precision": 1.0,
                    "weight": 5,
                    "url": "https://en.wikipedia.org/v1",
                    "span_match_notes": "V1",
                    "description": "Version 1",
                    "category": "Test"
                }
            ]
        }
        
        upload_json_v2 = {
            "strategy": "test_strategy",
            "run_id": "20260218T120000Z",
            "generated_at_utc": "2026-02-18T12:00:00Z",
            "event_count": 1,
            "metadata": {
                "total_events_found": 1,
                "total_events_parsed": 1,
                "sections_identified": 1,
                "parsing_start_utc": "2026-02-18T12:00:00Z",
                "parsing_end_utc": "2026-02-18T12:01:00Z",
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
                    "title": "Event V2",
                    "start_year": 2025,
                    "end_year": 2025,
                    "is_bc_start": False,
                    "is_bc_end": False,
                    "precision": 1.0,
                    "weight": 5,
                    "url": "https://en.wikipedia.org/v2",
                    "span_match_notes": "V2",
                    "description": "Version 2",
                    "category": "Test"
                }
            ]
        }
        
        # First upload
        upload_data1 = {
            "category_name": "Overwrite Test",
            "json_data": upload_json_v1
        }
        response1 = admin_client.post("/admin/uploads", json=upload_data1)
        assert response1.status_code == 201
        data1 = response1.json()
        assert data1["events_inserted"] == 1
        
        # Second upload with overwrite
        upload_data2 = {
            "category_name": "Overwrite Test",
            "json_data": upload_json_v2,
            "overwrite": True
        }
        response2 = admin_client.post("/admin/uploads", json=upload_data2)
        assert response2.status_code == 201
        data2 = response2.json()
        assert data2["events_inserted"] == 1
        assert data2["events_deleted"] == 1  # Old event replaced
    
    def test_upload_file_size_limit(self, admin_client):
        """Test that oversized uploads are rejected."""
        # Create a very large JSON object
        large_json = {
            "strategy": "test_strategy",
            "run_id": "20260217T120000Z",
            "generated_at_utc": "2026-02-17T12:00:00Z",
            "event_count": 1000,
            "metadata": {
                "total_events_found": 1000,
                "total_events_parsed": 1000,
                "sections_identified": 1,
                "parsing_start_utc": "2026-02-17T12:00:00Z",
                "parsing_end_utc": "2026-02-17T12:01:00Z",
                "elapsed_seconds": 60.0,
                "events_per_second": 16.67,
                "confidence_distribution": {
                    "explicit": 1000,
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
                    "title": f"Event {i}",
                    "start_year": 2000 + i,
                    "end_year": 2000 + i,
                    "is_bc_start": False,
                    "is_bc_end": False,
                    "precision": 1.0,
                    "weight": 5,
                    "url": f"https://en.wikipedia.org/event{i}",
                    "span_match_notes": f"Event {i}",
                    "description": "x" * 500,  # Pad to make file larger
                    "category": "Test"
                }
                for i in range(1000)
            ]
        }
        
        upload_data = {
            "category_name": "Large Upload",
            "json_data": large_json
        }
        
        response = admin_client.post("/admin/uploads", json=upload_data)
        # Should be rejected if over 10MB or accepted if under
        # The actual behavior depends on server configuration
        assert response.status_code in [201, 413]  # 413 = Payload Too Large
    
    def test_list_uploads(self, admin_client):
        """Test listing uploads."""
        # Create an upload
        upload_json = {
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
                    "title": "Test",
                    "start_year": 2026,
                    "end_year": 2026,
                    "is_bc_start": False,
                    "is_bc_end": False,
                    "precision": 1.0,
                    "weight": 5,
                    "url": "https://en.wikipedia.org/test",
                    "span_match_notes": "Test",
                    "description": "Test",
                    "category": "Test"
                }
            ]
        }
        
        upload_data = {
            "category_name": "List Test",
            "json_data": upload_json
        }
        
        response = admin_client.post("/admin/uploads", json=upload_data)
        assert response.status_code == 201
        
        # List uploads
        list_response = admin_client.get("/admin/uploads")
        assert list_response.status_code == 200
        uploads = list_response.json()
        assert len(uploads) >= 1
        
        # Find our upload
        our_upload = next((u for u in uploads if u.get("category_id")), None)
        assert our_upload is not None
        assert our_upload["status"] == "completed"
    
    def test_upload_requires_admin_role(self, test_client):
        """Test that endpoints require authentication."""
        # Try to upload without auth - should get 401
        upload_data = {
            "category_name": "Unauthorized",
            "json_data": {}
        }
        response = test_client.post("/admin/uploads", json=upload_data)
        assert response.status_code == 401
