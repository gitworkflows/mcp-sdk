import pytest
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field

from mcp_sdk.resources import (
    ResourceMetadata,
    ResourceLinks,
    ResourceResponse,
    PaginationInfo,
    PaginatedResponse,
    ResourceError,
    ResourceErrorResponse,
    ResourceFilter,
    ResourceQuery,
    ResourceCreate,
    ResourceUpdate,
    ResourceDelete
)

# Sample data models for testing
class TestResource(BaseModel):
    """Sample resource model for testing"""
    id: str
    name: str
    value: int
    
class TestResourceList(BaseModel):
    """Sample resource list model for testing"""
    items: List[TestResource]

class TestResources:
    """Tests for resource models and responses."""
    
    @pytest.fixture
    def resource_metadata(self):
        """Create test resource metadata."""
        return ResourceMetadata(
            id="meta-123",
            version="1.0",
            status="success",
            tags=["test", "resource"]
        )
    
    @pytest.fixture
    def resource_links(self):
        """Create test resource links."""
        return ResourceLinks(
            self="https://api.example.com/resources/123",
            parent="https://api.example.com/resources",
            children=["https://api.example.com/resources/123/items"],
            related=["https://api.example.com/other-resources"]
        )
    
    @pytest.fixture
    def sample_resource(self):
        """Create a sample test resource."""
        return TestResource(
            id="res-123",
            name="Test Resource",
            value=42
        )
    
    def test_resource_metadata(self, resource_metadata):
        """Test ResourceMetadata creation and properties."""
        assert resource_metadata.id == "meta-123"
        assert resource_metadata.version == "1.0"
        assert resource_metadata.status == "success"
        assert "test" in resource_metadata.tags
        assert isinstance(resource_metadata.created_at, datetime)
        assert isinstance(resource_metadata.updated_at, datetime)
    
    def test_resource_links(self, resource_links):
        """Test ResourceLinks creation and properties."""
        assert resource_links.self == "https://api.example.com/resources/123"
        assert resource_links.parent == "https://api.example.com/resources"
        assert len(resource_links.children) == 1
        assert len(resource_links.related) == 1
    
    def test_resource_response(self, sample_resource, resource_metadata, resource_links):
        """Test ResourceResponse creation and properties."""
        response = ResourceResponse(
            data=sample_resource,
            metadata=resource_metadata,
            links=resource_links
        )
        
        assert response.data == sample_resource
        assert response.metadata == resource_metadata
        assert response.links == resource_links
        assert response.included is None
    
    def test_pagination_info(self):
        """Test PaginationInfo creation and properties."""
        pagination = PaginationInfo(
            total=100,
            page=2,
            per_page=25,
            total_pages=4,
            has_next=True,
            has_prev=True,
            next_page="https://api.example.com/resources?page=3",
            prev_page="https://api.example.com/resources?page=1"
        )
        
        assert pagination.total == 100
        assert pagination.page == 2
        assert pagination.per_page == 25
        assert pagination.total_pages == 4
        assert pagination.has_next is True
        assert pagination.has_prev is True
        assert pagination.next_page == "https://api.example.com/resources?page=3"
        assert pagination.prev_page == "https://api.example.com/resources?page=1"
    
    def test_paginated_response(self, resource_metadata, resource_links):
        """Test PaginatedResponse creation and properties."""
        resources = [
            TestResource(id=f"res-{i}", name=f"Resource {i}", value=i) 
            for i in range(1, 4)
        ]
        
        pagination = PaginationInfo(
            total=10,
            page=1,
            per_page=3,
            total_pages=4,
            has_next=True,
            has_prev=False
        )
        
        response = PaginatedResponse(
            data=resources,
            metadata=[resource_metadata] * 3,
            links=resource_links,
            pagination=pagination
        )
        
        assert len(response.data) == 3
        assert response.pagination.total == 10
        assert response.pagination.page == 1
        assert response.pagination.has_next is True
        assert response.pagination.has_prev is False
    
    def test_resource_error(self):
        """Test ResourceError creation and properties."""
        error = ResourceError(
            code="not_found",
            message="Resource not found",
            details={"resource_id": "res-123"},
            field="id"
        )
        
        assert error.code == "not_found"
        assert error.message == "Resource not found"
        assert error.details["resource_id"] == "res-123"
        assert error.field == "id"
    
    def test_resource_error_response(self, resource_metadata, resource_links):
        """Test ResourceErrorResponse creation and properties."""
        errors = [
            ResourceError(code="validation_error", message="Name is required", field="name"),
            ResourceError(code="validation_error", message="Value must be positive", field="value")
        ]
        
        error_response = ResourceErrorResponse(
            errors=errors,
            metadata=resource_metadata,
            links=resource_links
        )
        
        assert len(error_response.errors) == 2
        assert error_response.errors[0].code == "validation_error"
        assert error_response.errors[0].field == "name"
        assert error_response.errors[1].message == "Value must be positive"
    
    def test_resource_filter(self):
        """Test ResourceFilter creation and properties."""
        filter = ResourceFilter(
            field="name",
            operator="contains",
            value="test"
        )
        
        assert filter.field == "name"
        assert filter.operator == "contains"
        assert filter.value == "test"
    
    def test_resource_query(self):
        """Test ResourceQuery creation and properties."""
        filters = [
            ResourceFilter(field="name", operator="contains", value="test"),
            ResourceFilter(field="value", operator="gt", value=10)
        ]
        
        query = ResourceQuery(
            filters=filters,
            sort=["name", "-created_at"],
            include=["metadata", "related"],
            page=2,
            per_page=25
        )
        
        assert len(query.filters) == 2
        assert query.filters[0].field == "name"
        assert query.filters[1].operator == "gt"
        assert len(query.sort) == 2
        assert query.page == 2
        assert query.per_page == 25
    
    def test_resource_create(self, sample_resource):
        """Test ResourceCreate creation and properties."""
        create = ResourceCreate(
            data=sample_resource,
            metadata={"user_id": "user-123"}
        )
        
        assert create.data == sample_resource
        assert create.metadata["user_id"] == "user-123"
    
    def test_resource_update(self, sample_resource):
        """Test ResourceUpdate creation and properties."""
        update = ResourceUpdate(
            data=sample_resource,
            metadata={"updated_by": "user-123"}
        )
        
        assert update.data == sample_resource
        assert update.metadata["updated_by"] == "user-123"
    
    def test_resource_delete(self):
        """Test ResourceDelete creation and properties."""
        delete = ResourceDelete(
            force=True,
            reason="Duplicate resource"
        )
        
        assert delete.force is True
        assert delete.reason == "Duplicate resource"

