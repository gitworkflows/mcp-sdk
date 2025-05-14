import pytest
from unittest.mock import patch, Mock, MagicMock
import json
import requests

from mcp_sdk.client import MCPClient
from mcp_sdk.models import MCPRequest, MCPResponse
from mcp_sdk.exceptions import (
    MCPError,
    MCPConnectionError,
    MCPAuthenticationError,
    MCPValidationError,
    MCPRateLimitError,
    MCPTimeoutError
)

class TestMCPClient:
    """Tests for the MCPClient class."""

    def test_initialization(self, client_config, client_info):
        """Test client initialization with valid parameters."""
        with patch('requests.Session'):
            client = MCPClient(
                api_key="test-api-key",
                endpoint="https://api.example.com",
                client_info=client_info,
                config=client_config
            )
            
            assert client.api_key == "test-api-key"
            assert client.endpoint == "https://api.example.com"
            assert client.client_info == client_info
            assert client.config == client_config

    def test_initialization_missing_api_key(self):
        """Test client initialization with missing API key."""
        with pytest.raises(MCPError):
            MCPClient(api_key="", endpoint="https://api.example.com")

    def test_initialization_missing_endpoint(self):
        """Test client initialization with missing endpoint."""
        with pytest.raises(MCPError):
            MCPClient(api_key="test-api-key", endpoint="")

    @patch('requests.Session.post')
    async def test_send_success(self, mock_post, mcp_client, mock_response):
        """Test successful API request."""
        mock_post.return_value = mock_response
        
        request = MCPRequest(
            model="gpt-4",
            context="Test context",
            settings={"temperature": 0.7, "max_tokens": 100}
        )
        
        response = await mcp_client.send(request)
        assert response is not None
        assert "data" in response

    @patch('requests.Session.post')
    async def test_send_connection_error(self, mock_post, mcp_client):
        """Test connection error handling."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        request = MCPRequest(
            model="gpt-4",
            context="Test context",
            settings={"temperature": 0.7, "max_tokens": 100}
        )
        
        with pytest.raises(MCPConnectionError):
            await mcp_client.send(request)

    @patch('requests.Session.post')
    async def test_send_timeout(self, mock_post, mcp_client):
        """Test timeout error handling."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        
        request = MCPRequest(
            model="gpt-4",
            context="Test context",
            settings={"temperature": 0.7, "max_tokens": 100}
        )
        
        with pytest.raises(MCPTimeoutError):
            await mcp_client.send(request)

    def test_prepare_headers(self, mcp_client):
        """Test header preparation."""
        headers = mcp_client._prepare_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {mcp_client.api_key}"
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert "X-Client-Name" in headers
        assert headers["X-Client-Name"] == mcp_client.client_info.name

