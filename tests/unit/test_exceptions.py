import pytest
import json
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

class TestExceptions:
    """Tests for MCP exception classes."""

    def test_base_error(self):
        """Test the base MCPError class."""
        error = MCPError("Test error message")
        assert "Test error message" in str(error)
        assert error.status_code is None
        assert error.response is None

    def test_error_with_status_code(self):
        """Test MCPError with status code."""
        error = MCPError("Test error message", status_code=404)
        assert "Test error message" in str(error)
        assert "404" in str(error)
        assert error.status_code == 404

    def test_error_with_response(self):
        """Test MCPError with response data."""
        response_data = {"error": "Not found", "details": "Resource doesn't exist"}
        error = MCPError("Test error message", response=response_data)
        assert "Test error message" in str(error)
        assert "Not found" in str(error)
        assert error.response == response_data

    def test_error_formatting(self):
        """Test error message formatting."""
        response_data = {"error": "Bad request", "code": "invalid_input"}
        error = MCPError(
            "Test error message",
            status_code=400,
            response=response_data
        )
        error_str = str(error)
        assert "Test error message" in error_str
        assert "400" in error_str
        assert "Bad request" in error_str
        assert "invalid_input" in error_str

    def test_connection_error(self):
        """Test MCPConnectionError."""
        error = MCPConnectionError()
        assert "Failed to connect" in str(error)
        
        custom_error = MCPConnectionError("Custom connection error")
        assert "Custom connection error" in str(custom_error)

    def test_authentication_error(self):
        """Test MCPAuthenticationError."""
        error = MCPAuthenticationError()
        assert "Authentication failed" in str(error)

    def test_validation_error(self):
        """Test MCPValidationError with validation errors."""
        validation_errors = {
            "field1": ["Value is required"],
            "field2": ["Must be a string"]
        }
        error = MCPValidationError(validation_errors=validation_errors)
        assert "Invalid request parameters" in str(error)
        assert "field1" in str(error)
        assert "field2" in str(error)
        assert error.validation_errors == validation_errors

    def test_rate_limit_error(self):
        """Test MCPRateLimitError with retry-after."""
        error = MCPRateLimitError(retry_after=30)
        assert "Rate limit exceeded" in str(error)
        assert "30 seconds" in str(error)
        assert error.retry_after == 30

    def test_timeout_error(self):
        """Test MCPTimeoutError with timeout value."""
        error = MCPTimeoutError(timeout=5.0)
        assert "Request timed out" in str(error)
        assert "5.0 seconds" in str(error)
        assert error.timeout == 5.0

    def test_resource_not_found_error(self):
        """Test MCPResourceNotFoundError with resource ID."""
        error = MCPResourceNotFoundError(resource_id="user-123")
        assert "Resource not found" in str(error)
        assert "user-123" in str(error)
        assert error.resource_id == "user-123"

    def test_permission_error(self):
        """Test MCPPermissionError with action."""
        error = MCPPermissionError(action="delete_user")
        assert "Permission denied" in str(error)
        assert "delete_user" in str(error)
        assert error.action == "delete_user"

    def test_configuration_error(self):
        """Test MCPConfigurationError with setting."""
        error = MCPConfigurationError(setting="api_key")
        assert "Configuration error" in str(error)
        assert "api_key" in str(error)
        assert error.setting == "api_key"

