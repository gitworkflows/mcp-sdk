"""
MCP SDK - A Python SDK for Media Control Protocol
"""

from .client import MCPClient
from .models import MCPRequest, MCPResponse
from .exceptions import (
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

# Import product-specific modules
from .products import (
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