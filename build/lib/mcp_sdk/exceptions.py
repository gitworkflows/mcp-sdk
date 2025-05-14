from typing import Optional, Dict, Any
import json

class MCPError(Exception):
    """Base exception for MCP SDK errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with additional context"""
        message = self.message
        if self.status_code:
            message = f"{message} (Status Code: {self.status_code})"
        if self.response:
            try:
                error_details = json.dumps(self.response, indent=2)
                message = f"{message}\nResponse: {error_details}"
            except:
                message = f"{message}\nResponse: {str(self.response)}"
        return message

class MCPConnectionError(MCPError):
    """Raised when there are connection issues with the MCP API"""
    def __init__(self, message: str = "Failed to connect to MCP API", **kwargs):
        super().__init__(message, **kwargs)

class MCPAuthenticationError(MCPError):
    """Raised when there are authentication issues with the MCP API"""
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, **kwargs)

class MCPValidationError(MCPError):
    """Raised when request validation fails"""
    def __init__(self, message: str = "Invalid request parameters", validation_errors: Optional[Dict[str, Any]] = None, **kwargs):
        self.validation_errors = validation_errors
        if validation_errors:
            message = f"{message}: {str(validation_errors)}"
        super().__init__(message, **kwargs)

class MCPRateLimitError(MCPError):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None, **kwargs):
        self.retry_after = retry_after
        if retry_after:
            message = f"{message}. Retry after {retry_after} seconds"
        super().__init__(message, **kwargs)

class MCPTimeoutError(MCPError):
    """Raised when a request times out"""
    def __init__(self, message: str = "Request timed out", timeout: Optional[float] = None, **kwargs):
        self.timeout = timeout
        if timeout:
            message = f"{message} after {timeout} seconds"
        super().__init__(message, **kwargs)

class MCPResourceNotFoundError(MCPError):
    """Raised when a requested resource is not found"""
    def __init__(self, message: str = "Resource not found", resource_id: Optional[str] = None, **kwargs):
        self.resource_id = resource_id
        if resource_id:
            message = f"{message}: {resource_id}"
        super().__init__(message, **kwargs)

class MCPPermissionError(MCPError):
    """Raised when the user doesn't have permission to perform an action"""
    def __init__(self, message: str = "Permission denied", action: Optional[str] = None, **kwargs):
        self.action = action
        if action:
            message = f"{message} for action: {action}"
        super().__init__(message, **kwargs)

class MCPConfigurationError(MCPError):
    """Raised when there are configuration issues"""
    def __init__(self, message: str = "Configuration error", setting: Optional[str] = None, **kwargs):
        self.setting = setting
        if setting:
            message = f"{message} in setting: {setting}"
        super().__init__(message, **kwargs)

class MCPSessionExpiredError(MCPAuthenticationError):
    """Raised when a session has expired and cannot be refreshed"""
    def __init__(self, message: str = "Session has expired", **kwargs):
        super().__init__(message, **kwargs)