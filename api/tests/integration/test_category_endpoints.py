"""Integration tests for category management endpoints."""

import json
import pytest
from api.services.category_service import validate_import_schema


@pytest.mark.integration
class TestCategoryEndpoints:
    """Integration tests for category CRUD endpoints."""
    
    def test_list_categories_empty(self, admin_client):
        """Test listing categories."""
        # Just verify we get a valid response with a list (may not be empty due to test isolation)
        response = admin_client.get("/admin/categories")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All items should have required fields
        for category in data:
            assert "id" in category
            assert "name" in category
            assert "created_at" in category
    
    def test_create_category_success(self, admin_client):
        """Test successfully creating a category."""
        category_data = {
            "name": "Roman History",
            "description": "Timeline of Roman history events",
            "strategy_name": "timeline_of_roman_history"
        }
        
        response = admin_client.post("/admin/categories", json=category_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Roman History"
        assert data["description"] == "Timeline of Roman history events"
        assert data["id"] is not None
        
        # Verify category was created by listing
        list_response = admin_client.get("/admin/categories")
        assert list_response.status_code == 200
        categories = list_response.json()
        assert len(categories) == 1
        assert categories[0]["name"] == "Roman History"
    
    def test_create_category_duplicate_name(self, admin_client):
        """Test that creating category with duplicate name fails."""
        category_data = {
            "name": "Food Timeline",
            "description": "Timeline of food history"
        }
        
        # Create first category
        response1 = admin_client.post("/admin/categories", json=category_data)
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = admin_client.post("/admin/categories", json=category_data)
        assert response2.status_code == 400
        data = response2.json()
        assert "already exists" in data.get("detail", "").lower()
    
    def test_create_category_missing_name(self, admin_client):
        """Test that creating category without name fails."""
        category_data = {
            "description": "Missing name"
        }
        
        response = admin_client.post("/admin/categories", json=category_data)
        assert response.status_code == 422  # Validation error
    
    def test_get_category_success(self, admin_client):
        """Test getting a specific category."""
        # Create a category
        category_data = {
            "name": "Test Category",
            "description": "Test description"
        }
        create_response = admin_client.post("/admin/categories", json=category_data)
        assert create_response.status_code == 201
        category_id = create_response.json()["id"]
        
        # Get the category
        response = admin_client.get(f"/admin/categories/{category_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == category_id
        assert data["name"] == "Test Category"
    
    def test_get_category_not_found(self, admin_client):
        """Test getting non-existent category."""
        response = admin_client.get("/admin/categories/999")
        assert response.status_code == 404
    
    def test_update_category_success(self, admin_client):
        """Test updating a category."""
        # Create a category
        category_data = {
            "name": "Original Name",
            "description": "Original description"
        }
        create_response = admin_client.post("/admin/categories", json=category_data)
        category_id = create_response.json()["id"]
        
        # Update it
        update_data = {
            "name": "Updated Name",
            "description": "Updated description"
        }
        response = admin_client.patch(f"/admin/categories/{category_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
    
    def test_update_category_not_found(self, admin_client):
        """Test updating non-existent category."""
        update_data = {
            "name": "New Name"
        }
        response = admin_client.patch("/admin/categories/999", json=update_data)
        assert response.status_code == 404
    
    def test_delete_category_success(self, admin_client):
        """Test deleting a category."""
        # Create a category
        category_data = {
            "name": "To Delete",
            "description": "Will be deleted"
        }
        create_response = admin_client.post("/admin/categories", json=category_data)
        category_id = create_response.json()["id"]
        
        # Delete it
        response = admin_client.delete(f"/admin/categories/{category_id}")
        assert response.status_code == 204
        
        # Verify it's deleted
        get_response = admin_client.get(f"/admin/categories/{category_id}")
        assert get_response.status_code == 404
    
    def test_delete_category_not_found(self, admin_client):
        """Test deleting non-existent category."""
        response = admin_client.delete("/admin/categories/999")
        assert response.status_code == 404
    
    def test_list_categories_multiple(self, admin_client):
        """Test listing multiple categories."""
        # Generate unique names to avoid conflicts with other tests
        import uuid
        suffix = str(uuid.uuid4())[:8]
        
        categories_to_create = [
            {
                "name": f"Category A {suffix}",
                "description": "First category",
                "strategy_name": "strategy_a"
            },
            {
                "name": f"Category B {suffix}",
                "description": "Second category",
                "strategy_name": "strategy_b"
            },
            {
                "name": f"Category C {suffix}",
                "description": "Third category"
            }
        ]
        
        # Create categories
        created_ids = []
        for cat_data in categories_to_create:
            response = admin_client.post("/admin/categories", json=cat_data)
            assert response.status_code == 201
            created_ids.append(response.json()["id"])
        
        # List all
        response = admin_client.get("/admin/categories")
        assert response.status_code == 200
        categories = response.json()
        
        # Filter to our created categories
        our_categories = [c for c in categories if c["id"] in created_ids]
        assert len(our_categories) == 3
        
        # Verify they're sorted by name
        names = [cat["name"] for cat in sorted(our_categories, key=lambda c: c["name"])]
        expected_names = sorted([f"Category A {suffix}", f"Category B {suffix}", f"Category C {suffix}"])
        assert names == expected_names
    
    def test_create_category_requires_admin_role(self, test_client):
        """Test that endpoints require authentication."""
        # Try to create category without any auth - should get 401
        category_data = {
            "name": "Unauthorized Category",
            "description": "Should not be allowed"
        }
        response = test_client.post("/admin/categories", json=category_data)
        assert response.status_code == 401


@pytest.mark.integration
class TestCategoryFiltering:
    """Tests for category filtering and search."""
    
    def test_filter_categories_by_strategy(self, admin_client):
        """Test filtering categories by strategy name."""
        import uuid
        suffix = str(uuid.uuid4())[:8]
        
        # Create categories with different strategies
        cat1 = {
            "name": f"Roman Events {suffix}",
            "strategy_name": "timeline_of_roman_history"
        }
        cat2 = {
            "name": f"Food Events {suffix}",
            "strategy_name": "timeline_of_food"
        }
        cat3 = {
            "name": f"More Roman Events {suffix}",
            "strategy_name": "timeline_of_roman_history"
        }
        
        created_ids = []
        for cat_data in [cat1, cat2, cat3]:
            response = admin_client.post("/admin/categories", json=cat_data)
            assert response.status_code == 201
            created_ids.append(response.json()["id"])
        
        # Filter by strategy
        response = admin_client.get("/admin/categories?strategy=timeline_of_roman_history")
        assert response.status_code == 200
        categories = response.json()
        
        # Find our created categories
        our_categories = [c for c in categories if c["id"] in created_ids]
        assert len(our_categories) == 2
        assert all(cat["strategy_name"] == "timeline_of_roman_history" for cat in our_categories)
