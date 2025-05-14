from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import uuid
from datetime import datetime
from .models import MCPRequest, MCPResponse, ClientInfo
from .exceptions import MCPError
from .server_config import ServerConfig
from .messages import (
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
from .server_utils.runner import ServerRunner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server implementation with lifespan support"""

    def __init__(self, config: Optional[ServerConfig] = None):
        """
        Initialize the MCP server.

        Args:
            config: Server configuration
        """
        self.config = config or ServerConfig()
        self.app = self._create_app()
        self._setup_middleware()
        self._setup_routes()
        self.message_processor = MessageProcessor()
        self._register_handlers()
        self.runner = ServerRunner(self.app, self.config)

    def _register_handlers(self):
        """Register message handlers"""
        self.message_processor.register_handler(TextHandler())
        # Register other handlers here

    def _create_app(self) -> FastAPI:
        """Create the FastAPI application with lifespan support"""
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info("Starting MCP server...")
            try:
                # Initialize resources
                await self._startup()
                yield
            except Exception as e:
                logger.error(f"Startup failed: {str(e)}")
                raise

            # Shutdown
            logger.info("Shutting down MCP server...")
            try:
                # Cleanup resources
                await self._shutdown()
            except Exception as e:
                logger.error(f"Shutdown failed: {str(e)}")
                raise

        return FastAPI(
            title="MCP Server",
            description="Media Control Protocol Server",
            version="1.0.0",
            lifespan=lifespan
        )

    def _setup_middleware(self):
        """Setup middleware for the application"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins,
            allow_methods=self.config.cors_methods,
            allow_headers=self.config.cors_headers,
            allow_credentials=True,
        )

    def _setup_routes(self):
        """Setup API routes"""
        @self.app.post("/api/v1/process", response_model=MCPResponse)
        async def process_request(
            request_data: MCPRequest,
            request: Request,
            client_info: ClientInfo = Depends(lambda: self._get_client_info(request))
        ) -> MCPResponse:
            """
            Process an MCP request.

            Args:
                request: The MCP request
                client_info: Client information

            Returns:
                MCPResponse: The processed response
            """
            try:
                # Convert MCPRequest to typed message
                message = self._create_message(request_data, client_info)
                
                # Process the message
                response = await self.message_processor.process(message)
                
                # Convert response to MCPResponse
                return self._create_mcp_response(response)
            except MCPError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"Request processing failed: {str(e)}")
                raise HTTPException(status_code=500, detail="Internal server error")

    def _create_message(self, request: MCPRequest, client_info: ClientInfo) -> BaseMessage:
        """Create a typed message from MCPRequest"""
        metadata = MessageMetadata(
            source=client_info.name,
            priority=0,
            tags=["mcp"],
            custom_data={
                "client_version": client_info.version,
                "platform": client_info.platform
            }
        )

        # Create appropriate message type based on request
        if request.model.startswith("text"):
            # Extract parameters from request metadata
            parameters = TextParameters(
                language=request.metadata.get("language"),
                format=request.metadata.get("format"),
                max_length=request.metadata.get("max_length"),
                temperature=request.metadata.get("temperature", 0.7),
                top_p=request.metadata.get("top_p"),
                frequency_penalty=request.metadata.get("frequency_penalty"),
                presence_penalty=request.metadata.get("presence_penalty")
            )

            # Create context with parameters
            context = MessageContext[TextParameters](
                content=request.context,
                parameters=parameters,
                metadata=request.metadata
            )

            # Create content
            content = TextContent(
                text=request.context,
                language=parameters.language,
                format=parameters.format
            )

            return TextMessage(
                id=str(uuid.uuid4()),
                type=MessageType.TEXT,
                content=content,
                context=context,
                metadata=metadata
            )
        else:
            raise MCPError(f"Unsupported model type: {request.model}")

    def _create_mcp_response(self, response: MessageResponse) -> MCPResponse:
        """Convert MessageResponse to MCPResponse"""
        return MCPResponse(
            id=response.message_id,
            model=response.type.value,
            content=str(response.result),
            created_at=response.created_at.isoformat(),
            usage={"tokens": 0},  # Update with actual usage
            metadata=response.metadata.custom_data
        )

    async def _get_client_info(self, request: Request) -> ClientInfo:
        """Get client information from request headers"""
        headers = request.headers
        return ClientInfo(
            name=headers.get("x-client-name", "unknown"),
            version=headers.get("x-client-version", "1.0.0"),
            platform=headers.get("x-client-platform", "unknown"),
            environment=headers.get("x-client-environment", "production"),
            language=headers.get("x-client-language", "python"),
            language_version=headers.get("x-client-language-version", "3.8"),
            sdk_version=headers.get("x-client-sdk-version", "0.1.0"),
            client_id=headers.get("x-client-id"),
            user_agent=headers.get("user-agent"),
            ip_address=request.client.host if request.client else None
        )

    async def _startup(self):
        """Initialize resources on startup"""
        logger.info("Initializing server resources...")

    async def _shutdown(self):
        """Cleanup resources on shutdown"""
        logger.info("Cleaning up server resources...")

    def run(self):
        """Run the server"""
        self.runner.run() 