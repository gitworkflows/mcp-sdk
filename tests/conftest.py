import os
import pytest
from unittest.mock import Mock, patch
import json
from datetime import datetime
from fastapi.testclient import TestClient

from mcp_sdk.client import MCPClient
from mcp_sdk.models import ClientInfo, ClientConfig
from mcp_sdk.server import MCPServer, ServerConfig
from mcp_sdk.config import MCPConfig

@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": {"result": "success"}}
    mock_resp.headers = {"X-Request-ID": "test-request-id"}
    mock_resp.url = "https://api.example.com/endpoint"
    return mock_resp

@pytest.fixture
def client_config():
    """Create a test client configuration."""
    return ClientConfig(
        api_key="test-api-key",
        endpoint="https://api.example.com",
        timeout=5,
        max_retries=2,
        retry_backoff_factor=0.1,
        verify_ssl=False
    )

@pytest.fixture
def client_info():
    """Create test client information."""
    return ClientInfo(
        name="test-client",
        version="1.0.0",
        platform="test",
        language="python",
        language_version="3.8",
        sdk_version="0.1.0"
    )

@pytest.fixture
def mcp_client(client_config, client_info):
    """Create an MCP client for testing."""
    with patch('requests.Session') as mock_session:
        client = MCPClient(
            api_key="test-api-key",
            endpoint="https://api.example.com",
            client_info=client_info,
            config=client_config
        )
        yield client

@pytest.fixture
def server_config():
    """Create a test server configuration."""
    return ServerConfig(
        host="127.0.0.1",
        port=8888,
        debug=True,
        workers=1,
        cors_origins=["*"],
        cors_methods=["*"],
        cors_headers=["*"]
    )

@pytest.fixture
def test_server(server_config):
    """Create a test server instance."""
    server = MCPServer(config=server_config)
    return server

@pytest.fixture
def test_client(test_server):
    """Create a test client for FastAPI."""
    with TestClient(test_server.app) as client:
        yield client
