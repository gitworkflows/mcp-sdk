import pytest
import json
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

from mcp_sdk.server import MCPServer
from mcp_sdk.models import MCPRequest, MCPResponse, ClientInfo
from mcp_sdk.messages import (
    MessageType,
    TextResult,
    TextParameters,
    TextResponse,
    MessageMetadata
)

@pytest.fixture
def api_client():
    """Create a test API client."""
    server = MCPServer()
    return TestClient(server.app)

class TestAPI:
    """Integration tests for the API endpoints."""
    
    def test_process_endpoint_structure(self, api_client, monkeypatch):
        """Test the structure of the /api/v1/process endpoint."""
        # Mock the message processor to avoid actual processing
        async def mock_process(*args, **kwargs):
            return TextResponse(
                message_id="test-msg-id",
                type=MessageType.TEXT,
                result=TextResult(
                    processed_text="Mocked response",
                    language="en",
                    confidence=0.95,
                    parameters=TextParameters()
                ),
                metadata=MessageMetadata(source="test"),
                processing_time=0.1,
                created_at=datetime.now()
            )
            
        with patch('mcp_sdk.messages.MessageProcessor.process', new=AsyncMock(side_effect=mock_process)):
            response = api_client.post(
                "/api/v1/process",
                json={
                    "model": "text:gpt-4",
                    "context": "Test message",
                    "settings": {
                        "temperature": 0.7,
                        "max_tokens": 100
                    }
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert "model" in data
            assert "content" in data
            assert "created_at" in data
            assert "usage" in data
    
    def test_process_with_invalid_data(self, api_client):
        """Test the /api/v1/process endpoint with invalid data."""
        # Test with missing required fields
        response = api_client.post(
            "/api/v1/process",
            json={"model": "text:gpt-4"}  # Missing context and settings
        )
        assert response.status_code in (400, 422)
        
        # Test with invalid model format
        response = api_client.post(
            "/api/v1/process",
            json={
                "model": "invalid-model",
                "context": "Test message",
                "settings": {
                    "temperature": 0.7,
                    "max_tokens": 100
                }
            }
        )
        assert response.status_code == 400 or "Unsupported model type" in response.text
        
        # Test with invalid temperature
        response = api_client.post(
            "/api/v1/process",
            json={
                "model": "text:gpt-4",
                "context": "Test message",
                "settings": {
                    "temperature": 2.0,  # Temperature should be <= 1.0
                    "max_tokens": 100
                }
            }
        )
        assert response.status_code == 422
        
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, api_client, monkeypatch):
        """Test handling multiple concurrent requests."""
        import asyncio
        
        # Mock the process method to avoid actual processing
        async def mock_process(*args, **kwargs):
            return TextResponse(
                message_id=f"test-msg-{asyncio.current_task().get_name()}",
                type=MessageType.TEXT,
                result=TextResult(
                    processed_text="Concurrent response",
                    language="en",
                    confidence=0.95,
                    parameters=TextParameters()
                ),
                metadata=MessageMetadata(source="test"),
                processing_time=0.1,
                created_at=datetime.now()
            )
            
        with patch('mcp_sdk.messages.MessageProcessor.process', new=AsyncMock(side_effect=mock_process)):
            async def make_request():
                return api_client.post(
                    "/api/v1/process",
                    json={
                        "model": "text:gpt-4",
                        "context": "Test message",
                        "settings": {
                            "temperature": 0.7,
                            "max_tokens": 100
                        }
                    }
                )
            
            # Make 5 concurrent requests
            tasks = [make_request() for _ in range(5)]
            responses = await asyncio.gather(*tasks)
            
            for response in responses:
                assert response.status_code == 200
                assert "content" in response.json()

    def test_error_response_format(self, api_client):
        """Test error response format."""
        response = api_client.post(
            "/api/v1/process",
            json={
                "model": "invalid:model",
                "context": "Test",
                "settings": {}
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)

    def test_content_type_headers(self, api_client):
        """Test content type headers in requests and responses."""
        response = api_client.post(
            "/api/v1/process",
            json={
                "model": "text:gpt-4",
                "context": "Test message",
                "settings": {
                    "temperature": 0.7,
                    "max_tokens": 100
                }
            },
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
    def test_request_id_headers(self, api_client, monkeypatch):
        """Test request ID headers are present in responses."""
        # This test depends on the server implementation.
        # If request IDs are included in headers, verify them here.
        response = api_client.post(
            "/api/v1/process",
            json={
                "model": "text:gpt-4",
                "context": "Test message",
                "settings": {"temperature": 0.7}
            },
            headers={"X-Request-ID": "test-request-123"}
        )
        
        assert response.status_code == 200
        # Verify the server echoes back the request ID or provides its own
        assert "x-request-id" in [h.lower() for h in response.headers.keys()]
