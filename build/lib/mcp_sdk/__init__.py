"""
MCP SDK - A Python SDK for Media Control Protocol
"""

from mcp_sdk.client import MCPClient
from mcp_sdk.models import MCPRequest, MCPResponse
from mcp_sdk.exceptions import (
    MCPError,
    MCPConnectionError,
    MCPAuthenticationError,
    MCPValidationError,
    MCPRateLimitError,
    MCPTimeoutError,
    MCPResourceNotFoundError,
    MCPPermissionError,
    MCPConfigurationError
)
from mcp_sdk.server import MCPServer
from mcp_sdk.server_config import ServerConfig

# Import product-specific modules
from mcp_sdk.products import (
    text,
    image,
    audio,
    video
)

__version__ = "0.1.0"
__all__ = [
    "MCPClient",
    "MCPRequest",
    "MCPResponse",
    "MCPServer",
    "ServerConfig",
    "MCPError",
    "MCPConnectionError",
    "MCPAuthenticationError",
    "MCPValidationError",
    "MCPRateLimitError",
    "MCPTimeoutError",
    "MCPResourceNotFoundError",
    "MCPPermissionError",
    "MCPConfigurationError",
    "text",
    "image",
    "audio",
    "video"
] 