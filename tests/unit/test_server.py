import pytest
from unittest.mock import patch, Mock, AsyncMock
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import requests

from mcp_sdk.server import MCPServer, ServerConfig
from mcp_sdk.messages import (
    MessageType,
    MessageStatus,
    MessageMetadata,
    MessageContext,
    BaseMessage,
    MessageResponse,
    MessageProcessor,
    TextContent,
    TextParameters,
    TextResult,
    TextMessage,
    TextResponse,
    TextHandler
)
from mcp_sdk.models import MCPRequest, MCPResponse, ClientInfo
from mcp_sdk.exceptions import MCPError

class TestServer:
    """Tests for the MCPServer class and its components."""
    
    @pytest.fixture
    def sample_message_metadata(self):
        """Create sample message metadata."""
        return MessageMetadata(
            source="test-client",
            tags=["test"]
        )
    
    @pytest.fixture
    def sample_request(self):
        """Create a sample request."""
        return MCPRequest(
            model="text:gpt-4",
            context="Hello, world!",
            settings={
                "temperature": 0.7,
                "max_tokens": 100
            },
            metadata={
                "language": "en",
                "format": "json"
            }
        )
    
    def test_server_initialization(self, server_config):
        """Test server initialization."""
        server = MCPServer(config=server_config)
        
        assert isinstance(server.app, FastAPI)
        assert server.config == server_config
        assert isinstance(server.message_processor, MessageProcessor)
    
    def test_server_config_defaults(self):
        """Test server config default values."""
        server = MCPServer()
        
        assert server.config.host == "0.0.0.0"
        assert server.config.port == 8000
        assert server.config.debug is False
        assert server.config.workers == 1
        assert "*" in server.config.cors_origins
    
    def test_server_handler_registration(self):
        """Test server handler registration."""
        server = MCPServer()
        
        # The TextHandler should be registered by default
        assert MessageType.TEXT in server.message_processor._handlers
        assert isinstance(server.message_processor._handlers[MessageType.TEXT], TextHandler)
    
    @patch("uuid.uuid4")
    def test_create_message(self, mock_uuid, sample_request):
        """Test message creation from request."""
        # Mock UUID generation
        mock_uuid.return_value = "test-uuid-123"
        
        server = MCPServer()
        client_info = ClientInfo(
            name="test-client",
            version="1.0",
            platform="test",
            language="python",
            language_version="3.8",
            sdk_version="0.1.0"
        )
        
        # Create a test request
        request = MCPRequest(
            id="test-request-id",
            type=MessageType.TEXT,
            content=TextContent(text="Test message"),
            context=MessageContext(
                parameters=TextParameters(temperature=0.7)
            )
        )
        
        message = server._create_message(request, client_info)
        
        assert message.id == "test-uuid-123"
        assert message.type == MessageType.TEXT
        assert message.content.text == "Test message"
        assert message.context.parameters.temperature == 0.7
        assert message.metadata.source == "test-client"
        assert message.metadata.created_at is not None
        assert message.metadata.status == MessageStatus.PENDING
    
    def test_create_mcp_response(self, sample_message_metadata):
        """Test MCP response creation from message response."""
        from mcp_sdk.messages import TextResult, TextParameters
        from mcp_sdk.models import MCPResponse
        
        server = MCPServer()
        
        # Create a sample text result
        text_result = TextResult(
            processed_text="PROCESSED TEXT",
            language="en",
            confidence=0.95,
            parameters=TextParameters()
        )
        
        # Create a sample message response
        message_response = TextResponse(
            message_id="msg-123",
            type=MessageType.TEXT,
            result=text_result,
            metadata=sample_message_metadata,
            processing_time=0.1,
            created_at=datetime.utcnow()
        )

        # Create MCP response
        mcp_response = server._create_mcp_response(message_response)
        
        assert isinstance(mcp_response, MCPResponse)
        assert mcp_response.id == "msg-123"
        assert mcp_response.type == MessageType.TEXT
        assert mcp_response.result.processed_text == "PROCESSED TEXT"
        assert mcp_response.metadata == sample_message_metadata
    
    def test_create_message_with_custom_id(self, sample_request):
        """Test message creation with a custom message ID."""
        server = MCPServer()
        client_info = ClientInfo(
            name="test-client",
            version="1.0",
            platform="test",
            language="python",
            language_version="3.8",
            sdk_version="0.1.0"
        )
        
        # Create a test request with a custom ID
        request = MCPRequest(
            id="custom-request-id",
            type=MessageType.TEXT,
            content=TextContent(text="Test message"),
            context=MessageContext(
                parameters=TextParameters(temperature=0.7)
            )
        )
        
        message = server._create_message(request, client_info)
        
        assert message.id == "custom-request-id"
        assert message.type == MessageType.TEXT
        assert message.content.text == "Test message"
        assert message.context.parameters.temperature == 0.7
        assert message.metadata.source == "test-client"
        assert message.metadata.created_at is not None
        assert message.metadata.status == MessageStatus.PENDING
    
    @patch("uuid.uuid4")
    def test_create_message_with_uuid(self, mock_uuid):
        """Test message creation from request with UUID."""
        from uuid import UUID
        test_uuid = "12345678-1234-5678-1234-567812345678"
        mock_uuid.return_value = UUID(test_uuid)
        
        server = MCPServer()
        client_info = ClientInfo(
            name="test-client",
            version="1.0",
            platform="test",
            language="python",
            language_version="3.8",
            sdk_version="0.1.0"
        )
        
        # Create a test request without an ID
        request = MCPRequest(
            type=MessageType.TEXT,
            content=TextContent(text="Test message"),
            context=MessageContext(
                parameters=TextParameters(temperature=0.7)
            )
        )
        
        message = server._create_message(request, client_info)
        
        assert message.id == test_uuid
        assert message.type == MessageType.TEXT
        assert message.content.text == "Test message"
        assert message.context.parameters.temperature == 0.7
        assert message.metadata.source == "test-client"
        assert message.metadata.created_at is not None
        assert message.metadata.status == MessageStatus.PENDING

    @pytest.mark.asyncio
    async def test_process_request(self, sample_request, monkeypatch):
        """Test processing a request through the server."""
        # Mock the message processor
        mock_processor = AsyncMock()
        mock_processor.process.return_value = TextResponse(
            message_id="msg-test",
            type=MessageType.TEXT,
            result=TextResult(
                processed_text="Processed response",
                language="en",
                confidence=0.95,
                parameters=TextParameters()
            ),
            metadata=MessageMetadata(source="test"),
            processing_time=0.1,
            created_at=datetime.now()
        )
        
        server = MCPServer()
        server.message_processor = mock_processor
        
        client_info = ClientInfo(
            name="test-client",
            version="1.0",
            platform="test",
            language="python",
            language_version="3.8",
            sdk_version="0.1.0"
        )
        
        # We need to mock the process_request method since it's not directly accessible
        async def mock_process_endpoint(request, client_info):
            message = server._create_message(request, client_info)
            response = await server.message_processor.process(message)
            return server._create_mcp_response(response)
            
        with patch.object(server.app, "post") as mock_post:
            mock_post.side_effect = mock_process_endpoint
            
            response = await mock_process_endpoint(sample_request, client_info)
            
            assert isinstance(response, MCPResponse)
            assert "Processed response" in response.content
            assert response.created_at is not None

    def test_server_error_handling(self, sample_request):
        """Test server error handling."""
        server = MCPServer()
        
        # Test with unsupported model
        bad_request = sample_request.model_copy(update={"model": "unsupported-model"})
        
        with pytest.raises(MCPError) as exc_info:
            server._create_message(bad_request, ClientInfo(
                name="test-client",
                version="1.0",
                platform="test",
                language="python",
                language_version="3.8",
                sdk_version="0.1.0"
            ))
        
        assert "Unsupported model type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_server_startup_shutdown(self, monkeypatch):
        """Test server startup and shutdown hooks."""
        # Mock logging to verify calls
        mock_logger = Mock()
        monkeypatch.setattr("mcp_sdk.server.logger", mock_logger)
        
        server = MCPServer()
        
        # Test startup
        await server._startup()
        mock_logger.info.assert_called_with("Initializing server resources...")
        
        # Test shutdown
        await server._shutdown()
        mock_logger.info.assert_called_with("Cleaning up server resources...")

    def test_server_middleware(self):
        """Test server middleware configuration."""
        server = MCPServer()
        
        # Check if the CORS middleware is added
        middleware_added = False
        for middleware in server.app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                middleware_added = True
                break
        
        assert middleware_added, "CORS middleware not added to the server"
