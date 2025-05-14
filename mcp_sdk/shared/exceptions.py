"""
Exception classes for MCP SDK.

This module defines custom exceptions used throughout the MCP SDK.
"""

from typing import Optional

from mcp_sdk.types import ErrorData


class McpError(Exception):
    """Base exception class for all MCP SDK exceptions.
    
    Attributes:
        error: The ErrorData object containing error details
        message: The error message
        code: Optional error code
    """

    error: ErrorData
    message: str
    code: Optional[int] = None

    def __init__(self, error: ErrorData, message: Optional[str] = None):
        """Initialize McpError.
        
        Args:
            error: The ErrorData object containing error details
            message: Optional custom error message. If not provided, uses error.message
        """
        self.error = error
        self.code = error.code
        self.message = message or error.message
        super().__init__(self.message)


class McpConnectionError(McpError):
    """Raised when there is a connection error with the MCP server."""
    pass


class McpTimeoutError(McpError):
    """Raised when an operation times out."""
    pass


class McpValidationError(McpError):
    """Raised when input validation fails."""
    pass


class McpAuthenticationError(McpError):
    """Raised when authentication fails."""
    pass


class McpAuthorizationError(McpError):
    """Raised when authorization fails."""
    pass


class McpResourceNotFoundError(McpError):
    """Raised when a requested resource is not found."""
    pass


class McpRateLimitError(McpError):
    """Raised when rate limits are exceeded."""
    pass


class McpServerError(McpError):
    """Raised when the server encounters an error."""
    pass


def create_error_from_code(code: int, message: str) -> McpError:
    """Create an appropriate exception based on the error code.
    
    Args:
        code: The error code
        message: The error message
        
    Returns:
        An appropriate exception instance
    """
    error_data = ErrorData(code=code, message=message)
    
    if 400 <= code < 500:
        if code == 401:
            return McpAuthenticationError(error_data)
        elif code == 403:
            return McpAuthorizationError(error_data)
        elif code == 404:
            return McpResourceNotFoundError(error_data)
        elif code == 429:
            return McpRateLimitError(error_data)
        else:
            return McpValidationError(error_data)
    elif 500 <= code < 600:
        return McpServerError(error_data)
    else:
        return McpError(error_data)