"""
Message wrapper with metadata support for MCP protocol.

This module defines a wrapper type that combines JSONRPCMessage with metadata
to support transport-specific features like resumability and request tracking.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeAlias, TypeVar, Union, overload

from pydantic import BaseModel, Field, validator

from mcp_sdk.types import JSONRPCMessage, RequestId

__all__ = [
    "ResumptionToken",
    "ResumptionTokenUpdateCallback",
    "ClientMessageMetadata",
    "ServerMessageMetadata",
    "MessageMetadata",
    "SessionMessage",
]

# Type aliases
ResumptionToken = str
ResumptionTokenUpdateCallback = Callable[[ResumptionToken], Awaitable[None]]

# Type variables for generic message handling
T = TypeVar("T", bound=JSONRPCMessage)


class MessageValidationError(ValueError):
    """Raised when message validation fails."""

    pass


@dataclass
class ClientMessageMetadata:
    """Metadata specific to client messages.

    Attributes:
        resumption_token: Optional token for resuming interrupted sessions
        on_resumption_token_update: Optional callback for token updates
    """

    resumption_token: ResumptionToken | None = None
    on_resumption_token_update: ResumptionTokenUpdateCallback | None = None

    def __post_init__(self) -> None:
        """Validate metadata after initialization."""
        if self.on_resumption_token_update is not None and not callable(
            self.on_resumption_token_update
        ):
            raise MessageValidationError("on_resumption_token_update must be callable")


@dataclass
class ServerMessageMetadata:
    """Metadata specific to server messages.

    Attributes:
        related_request_id: ID of the related request, if any
    """

    related_request_id: RequestId | None = None


# Union type for all possible metadata types
MessageMetadata: TypeAlias = Union[ClientMessageMetadata, ServerMessageMetadata, None]


@dataclass
class SessionMessage(Generic[T]):
    """A message with specific metadata for transport-specific features.

    This class wraps a JSON-RPC message with additional metadata that's
    specific to the MCP protocol, such as resumption tokens and request tracking.

    Attributes:
        message: The JSON-RPC message
        metadata: Optional metadata associated with the message
    """

    message: T
    metadata: MessageMetadata = field(default_factory=lambda: None)

    def __post_init__(self) -> None:
        """Validate the message and metadata after initialization."""
        if not isinstance(self.message, dict):
            raise MessageValidationError("Message must be a dictionary")

        if "jsonrpc" not in self.message:
            raise MessageValidationError("Missing required field: jsonrpc")

        if self.message.get("jsonrpc") != "2.0":
            raise MessageValidationError("Invalid JSON-RPC version")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionMessage:
        """Create a SessionMessage from a dictionary.

        Args:
            data: Dictionary containing message data

        Returns:
            A new SessionMessage instance

        Raises:
            MessageValidationError: If the input data is invalid
        """
        if not isinstance(data, dict):
            raise MessageValidationError("Input must be a dictionary")

        if "message" not in data:
            raise MessageValidationError("Missing required field: message")

        return cls(message=data["message"], metadata=data.get("metadata"))

    def to_dict(self) -> dict[str, Any]:
        """Convert the message to a dictionary.

        Returns:
            Dictionary representation of the message
        """
        return {"message": self.message, "metadata": self.metadata}
