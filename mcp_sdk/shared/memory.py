"""
In-memory transport implementation for MCP protocol.

This module provides in-memory transport implementations for testing and development
purposes, allowing client and server to communicate without network overhead.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any, Generic, Optional, TypeVar, cast

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from mcp_sdk.types import Implementation
from mcp_sdk.client.session import (
    ClientSession,
    ListRootsFnT,
    LoggingFnT,
    MessageHandlerFnT,
    SamplingFnT,
)
from mcp_sdk.server import Server
from mcp_sdk.shared.exceptions import McpError
from mcp_sdk.shared.message import SessionMessage

# Type variables for generic type hints
T = TypeVar('T')

__all__ = [
    'MessageStream',
    'create_client_server_memory_streams',
    'create_connected_server_and_client_session',
]

# Type alias for message streams
MessageStream = tuple[
    MemoryObjectReceiveStream[SessionMessage | Exception],
    MemoryObjectSendStream[SessionMessage],
]


class MemoryTransportError(McpError):
    """Raised when there is an error with the in-memory transport."""
    pass


@asynccontextmanager
async def create_client_server_memory_streams(
    max_buffer_size: int = 100
) -> AsyncGenerator[tuple[MessageStream, MessageStream], None]:
    """Create a pair of bidirectional memory streams for client-server communication.
    
    This creates two pairs of in-memory streams that can be used to simulate a
    network connection between a client and server. The streams are connected
    in a loopback configuration:
    
    - Client writes to client_send -> Server reads from server_receive
    - Server writes to server_send -> Client reads from client_receive
    
    Args:
        max_buffer_size: Maximum number of messages to buffer in each direction
        
    Yields:
        A tuple of (client_streams, server_streams) where each is a tuple of
        (receive_stream, send_stream)
        
    Raises:
        MemoryTransportError: If there's an error creating the streams
        
    Example:
        ```python
        async with create_client_server_memory_streams() as (client_streams, server_streams):
            client_receive, client_send = client_streams
            server_receive, server_send = server_streams
            
            # Client sends a message
            await client_send.send(message)
            
            # Server receives the message
            received = await server_receive.receive()
        ```
    """
    try:
        # Create streams for client -> server direction
        client_send, server_receive = anyio.create_memory_object_stream[
            SessionMessage | Exception
        ](max_buffer_size)
        
        # Create streams for server -> client direction
        server_send, client_receive = anyio.create_memory_object_stream[
            SessionMessage | Exception
        ](max_buffer_size)
        
        client_streams = (client_receive, client_send)
        server_streams = (server_receive, server_send)
        
        yield (client_streams, server_streams)
        
    except Exception as e:
        raise MemoryTransportError(
            f"Failed to create memory streams: {str(e)}"
        ) from e
        
    finally:
        # Ensure all streams are properly closed even if an error occurs
        for stream in (client_send, client_receive, server_send, server_receive):
            if not stream._closed:  # type: ignore[attr-defined]
                await stream.aclose()


async def create_connected_server_and_client_session(
    server: Server[Any],
    read_timeout_seconds: timedelta | None = None,
    sampling_callback: SamplingFnT | None = None,
    list_roots_callback: ListRootsFnT | None = None,
    logging_callback: LoggingFnT | None = None,
    message_handler: MessageHandlerFnT | None = None,
    client_info: Implementation | None = None,
    raise_exceptions: bool = False,
    max_buffer_size: int = 100,
) -> ClientSession:
    """Create a ClientSession connected to an in-memory MCP server.
    
    This function creates an in-memory connection between a client and server,
    which is useful for testing and development without requiring network access.
    
    Args:
        server: The MCP server instance to connect to
        read_timeout_seconds: Optional read timeout for the client
        sampling_callback: Optional callback for sampling messages
        list_roots_callback: Optional callback for listing roots
        logging_callback: Optional callback for logging
        message_handler: Optional callback for handling incoming messages
        client_info: Optional client implementation info
        raise_exceptions: Whether to raise exceptions (True) or return errors (False)
        max_buffer_size: Maximum number of messages to buffer in each direction
        
    Returns:
        A connected ClientSession instance
        
    Raises:
        MemoryTransportError: If there's an error creating the connection
        
    Example:
        ```python
        # Create a server
        server = Server()
        
        # Create a connected client
        client = await create_connected_server_and_client_session(
            server,
            read_timeout_seconds=timedelta(seconds=30)
        )
        
        # Use the client
        response = await client.some_method()
        ```
    """
    try:
        # Create in-memory streams
        client_streams, server_streams = await create_client_server_memory_streams(
            max_buffer_size=max_buffer_size
        )
        
        # Start the server with the server-side streams
        server_task = anyio.create_task(server.handle_connection(*server_streams))
        
        # Create and return a client session with the client-side streams
        return ClientSession(
            *client_streams,
            read_timeout_seconds=read_timeout_seconds,
            sampling_callback=sampling_callback,
            list_roots_callback=list_roots_callback,
            logging_callback=logging_callback,
            message_handler=message_handler,
            client_info=client_info,
            raise_exceptions=raise_exceptions,
        )
        
    except Exception as e:
        raise MemoryTransportError(
            f"Failed to create connected session: {str(e)}"
        ) from e