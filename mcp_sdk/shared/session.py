"""MCP Session Management Module.

This module provides a robust implementation of JSON-RPC 2.0 client/server
session handling with connection management, timeouts, and metrics.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from types import TracebackType
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

import anyio
import httpx
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from pydantic import BaseModel
from typing_extensions import Self

from mcp_sdk.shared.exceptions import McpError
from mcp_sdk.shared.message import (
    MessageMetadata,
    ServerMessageMetadata,
    SessionMessage,
)
from mcp_sdk.types import (
    CancelledNotification,
    ClientNotification,
    ClientRequest,
    ClientResult,
    ErrorData,
    JSONRPCError,
    JSONRPCMessage,
    JSONRPCNotification,
    JSONRPCRequest,
    JSONRPCResponse,
    RequestParams,
    ServerNotification,
    ServerRequest,
    ServerResult,
)

SendRequestT = TypeVar("SendRequestT", ClientRequest, ServerRequest)
SendResultT = TypeVar("SendResultT", ClientResult, ServerResult)
SendNotificationT = TypeVar("SendNotificationT", ClientNotification, ServerNotification)
ReceiveRequestT = TypeVar("ReceiveRequestT", ClientRequest, ServerRequest)
ReceiveResultT = TypeVar("ReceiveResultT", bound=BaseModel)
ReceiveNotificationT = TypeVar(
    "ReceiveNotificationT", ClientNotification, ServerNotification
)

RequestId = Union[str, int]


class ConnectionState(Enum):
    """Represents the connection state of the session."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    DISCONNECTING = auto()
    ERROR = auto()


@dataclass
class SessionMetrics:
    """Tracks metrics for the session."""

    start_time: float = field(default_factory=time.monotonic)
    requests_sent: int = 0
    requests_completed: int = 0
    request_errors: int = 0
    notifications_sent: int = 0
    notifications_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    reconnection_attempts: int = 0
    last_error: Optional[Exception] = None
    last_activity: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a dictionary."""
        uptime = time.monotonic() - self.start_time
        return {
            "uptime_seconds": uptime,
            "requests_sent": self.requests_sent,
            "requests_completed": self.requests_completed,
            "request_errors": self.request_errors,
            "notifications_sent": self.notifications_sent,
            "notifications_received": self.notifications_received,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "reconnection_attempts": self.reconnection_attempts,
            "last_error": str(self.last_error) if self.last_error else None,
            "last_activity": self.last_activity.isoformat(),
        }


class RequestResponder(Generic[ReceiveRequestT, SendResultT]):
    """Handles responding to MCP requests and manages request lifecycle.

    This class MUST be used as a context manager to ensure proper cleanup and
    cancellation handling:

    Example:
        with request_responder as resp:
            await resp.respond(result)

    The context manager ensures:
    1. Proper cancellation scope setup and cleanup
    2. Request completion tracking
    3. Cleanup of in-flight requests
    """

    def __init__(
        self,
        request_id: RequestId,
        request_meta: Optional[RequestParams.Meta],
        request: ReceiveRequestT,
        session: "BaseSession[SendRequestT, SendNotificationT, SendResultT, ReceiveRequestT, ReceiveNotificationT]",
        on_complete: Callable[["RequestResponder[ReceiveRequestT, SendResultT]"], Any],
        timeout: Optional[float] = 30.0,  # Default 30 second timeout
    ) -> None:
        """Initialize a new RequestResponder.

        Args:
            request_id: Unique identifier for the request
            request_meta: Optional metadata for the request
            request: The request object
            session: Reference to the parent session
            on_complete: Callback when request is completed
            timeout: Timeout in seconds for this request
        """
        self.request_id = request_id
        self.request_meta = request_meta
        self.request = request
        self._session = session
        self._completed = False
        self._start_time = time.monotonic()
        self._timeout = timeout
        self._cancel_scope = anyio.CancelScope()
        self._on_complete = on_complete
        self._entered = False
        self._logger = logging.getLogger(f"{__name__}.RequestResponder")

        # Log request initiation
        self._logger.debug(
            "Initializing request responder",
            extra={"request_id": request_id, "timeout": timeout},
        )

    def __enter__(self) -> "RequestResponder[ReceiveRequestT, SendResultT]":
        """Enter the context manager, enabling request cancellation tracking."""
        self._entered = True
        self._cancel_scope = anyio.CancelScope()
        self._cancel_scope.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager, performing cleanup and notifying completion."""
        try:
            if self._completed:
                self._on_complete(self)
        finally:
            self._entered = False
            if not self._cancel_scope:
                raise RuntimeError("No active cancel scope")
            self._cancel_scope.__exit__(exc_type, exc_val, exc_tb)

    async def respond(self, response: Union[SendResultT, ErrorData]) -> None:
        """
        Send a response for this request.

        Must be called within a context manager block.

        Args:
            response: The response to send, either a result or an error

        Raises:
            RuntimeError: If not used within a context manager
            AssertionError: If request was already responded to
            MCPTimeoutError: If the request has timed out
        """
        if not self._entered:
            raise RuntimeError("RequestResponder must be used as a context manager")

        if self._completed:
            raise AssertionError("Request was already responded to")

        # Check for timeout
        if self._timeout and (time.monotonic() - self._start_time) > self._timeout:
            self._completed = True
            self._on_complete(self)
            raise MCPTimeoutError(
                f"Request {self.request_id} timed out after {self._timeout} seconds"
            )

        try:
            self._completed = True
            await self._session._send_response(self.request_id, response)

            # Log successful response
            self._logger.debug(
                "Request completed successfully",
                extra={
                    "request_id": self.request_id,
                    "duration_seconds": time.monotonic() - self._start_time,
                },
            )
        except Exception as e:
            self._logger.error(
                "Error sending response",
                extra={"request_id": self.request_id},
                exc_info=True,
            )
            raise

    async def cancel(self) -> None:
        """
        Cancel this request and mark it as completed.

        This will trigger the on_complete callback and clean up resources.
        """
        if self._completed:
            return

        self._logger.debug("Cancelling request", extra={"request_id": self.request_id})

        self._cancel_scope.cancel()
        self._completed = True
        self._on_complete(self)

        self._logger.debug(
            "Request cancelled",
            extra={
                "request_id": self.request_id,
                "duration_seconds": time.monotonic() - self._start_time,
            },
        )

    @property
    def in_flight(self) -> bool:
        """
        Return True if this request is still in flight.

        Returns:
            bool: True if the request is still active and not cancelled
        """
        if self._timeout and (time.monotonic() - self._start_time) > self._timeout:
            return False
        return not self._completed and not self._cancel_scope.cancel_called

    @property
    def cancelled(self) -> bool:
        """
        Return True if this request was cancelled.

        Returns:
            bool: True if the request was cancelled
        """
        return self._cancel_scope.cancel_called


class BaseSession(
    Generic[
        SendRequestT,
        SendNotificationT,
        SendResultT,
        ReceiveRequestT,
        ReceiveNotificationT,
    ],
):
    """
    Implements an MCP "session" on top of read/write streams, including features
    like request/response linking, notifications, and progress.

    This class is an async context manager that automatically starts processing
    messages when entered.

    Features:
    - Connection state management
    - Automatic reconnection
    - Request/response tracking
    - Timeout handling
    - Metrics collection
    - Thread-safe operations
    """

    # Default configuration
    DEFAULT_MAX_IN_FLIGHT = 100
    DEFAULT_RECONNECT_ATTEMPTS = 3
    DEFAULT_RECONNECT_DELAY = 1.0  # seconds
    DEFAULT_REQUEST_TIMEOUT = 30.0  # seconds
    DEFAULT_HEARTBEAT_INTERVAL = 30.0  # seconds

    def __init__(
        self,
        read_stream: MemoryObjectReceiveStream[Union[SessionMessage, Exception]],
        write_stream: MemoryObjectSendStream[SessionMessage],
        receive_request_type: Type[ReceiveRequestT],
        receive_notification_type: Type[ReceiveNotificationT],
        read_timeout_seconds: Optional[timedelta] = None,
        max_in_flight: int = DEFAULT_MAX_IN_FLIGHT,
        reconnect_attempts: int = DEFAULT_RECONNECT_ATTEMPTS,
        reconnect_delay: float = DEFAULT_RECONNECT_DELAY,
        request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
        heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL,
    ) -> None:
        """Initialize the session.

        Args:
            read_stream: Stream to read messages from
            write_stream: Stream to write messages to
            receive_request_type: Type of requests this session can receive
            receive_notification_type: Type of notifications this session can receive
            read_timeout_seconds: Timeout for read operations
            max_in_flight: Maximum number of in-flight requests
            reconnect_attempts: Number of reconnection attempts before giving up
            reconnect_delay: Delay between reconnection attempts in seconds
            request_timeout: Default timeout for requests in seconds
            heartbeat_interval: Interval for heartbeat messages in seconds
        """
        # Streams
        self._read_stream = read_stream
        self._write_stream = write_stream

        # Type information
        self._receive_request_type = receive_request_type
        self._receive_notification_type = receive_notification_type

        # Configuration
        self._session_read_timeout_seconds = (
            read_timeout_seconds.total_seconds() if read_timeout_seconds else None
        )
        self._max_in_flight = max_in_flight
        self._reconnect_attempts = reconnect_attempts
        self._reconnect_delay = reconnect_delay
        self._default_request_timeout = request_timeout
        self._heartbeat_interval = heartbeat_interval

        # State
        self._state = ConnectionState.DISCONNECTED
        self._state_lock = asyncio.Lock()
        self._connection_attempts = 0
        self._last_heartbeat: Optional[datetime] = None
        self._last_activity: datetime = datetime.utcnow()
        self._heartbeat_task: Optional[asyncio.Task[None]] = None
        self._reconnect_task: Optional[asyncio.Task[None]] = None

        # Request tracking
        self._request_id = 0
        self._response_streams: Dict[
            RequestId, MemoryObjectSendStream[Union[JSONRPCResponse, JSONRPCError]]
        ] = {}
        self._in_flight: Dict[
            RequestId, RequestResponder[ReceiveRequestT, SendResultT]
        ] = {}

        # Metrics
        self._metrics = SessionMetrics()
        self._metrics_lock = asyncio.Lock()

        # Logging
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._exit_stack = AsyncExitStack()

        self._logger.info(
            "Session initialized",
            extra={
                "max_in_flight": max_in_flight,
                "request_timeout": request_timeout,
                "reconnect_attempts": reconnect_attempts,
            },
        )

    @property
    def state(self) -> ConnectionState:
        """Get the current connection state."""
        return self._state

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get a dictionary of current metrics."""
        return self._metrics.to_dict()

    def _get_next_request_id(self) -> int:
        """Generate the next request ID in a thread-safe manner."""
        with anyio.Lock():
            self._request_id += 1
            return self._request_id

    async def _update_state(self, new_state: ConnectionState) -> None:
        """Update the connection state and log the transition."""
        async with self._state_lock:
            if self._state == new_state:
                return

            old_state = self._state
            self._state = new_state

            # Log state transition
            self._logger.info(
                f"Connection state changed: {old_state.name} -> {new_state.name}",
                extra={"old_state": old_state.name, "new_state": new_state.name},
            )

            # Update metrics
            if new_state == ConnectionState.CONNECTED:
                async with self._metrics_lock:
                    self._metrics.last_activity = datetime.utcnow()
                    if old_state == ConnectionState.RECONNECTING:
                        self._metrics.reconnection_attempts += 1

    async def _check_connection(self) -> bool:
        """Check if the connection is still alive."""
        if self._state != ConnectionState.CONNECTED:
            return False

        # Check last activity time
        time_since_activity = (datetime.utcnow() - self._last_activity).total_seconds()
        if time_since_activity > self._heartbeat_interval * 2:
            self._logger.warning(
                "No activity detected, connection may be dead",
                extra={"seconds_since_activity": time_since_activity},
            )
            await self._handle_connection_error(ConnectionError("No activity detected"))
            return False

        return True

    async def _handle_connection_error(self, error: Exception) -> None:
        """Handle connection errors and initiate reconnection if needed."""
        async with self._state_lock:
            if self._state in (
                ConnectionState.DISCONNECTING,
                ConnectionState.DISCONNECTED,
            ):
                return

            await self._update_state(ConnectionState.RECONNECTING)

            # Update metrics
            async with self._metrics_lock:
                self._metrics.last_error = error
                self._metrics.request_errors += 1

            # Cancel all in-flight requests
            for responder in list(self._in_flight.values()):
                try:
                    await responder.cancel()
                except Exception as e:
                    self._logger.warning(
                        "Error cancelling in-flight request",
                        extra={"request_id": responder.request_id},
                        exc_info=True,
                    )

            # Clear response streams
            for stream in self._response_streams.values():
                try:
                    await stream.aclose()
                except Exception as e:
                    self._logger.warning("Error closing response stream", exc_info=True)

            self._response_streams.clear()

            # Start reconnection if needed
            if self._reconnect_attempts > 0:
                self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Handle automatic reconnection attempts."""
        attempts = 0

        while attempts < self._reconnect_attempts:
            attempts += 1

            try:
                self._logger.info(
                    f"Attempting to reconnect (attempt {attempts}/{self._reconnect_attempts})",
                    extra={
                        "attempt": attempts,
                        "max_attempts": self._reconnect_attempts,
                    },
                )

                # Reset connection state
                await self._reset_connection()

                # Reinitialize the connection
                await self._initialize_connection()

                # If we get here, reconnection was successful
                await self._update_state(ConnectionState.CONNECTED)
                self._logger.info("Reconnection successful")
                return

            except Exception as e:
                self._logger.error(
                    f"Reconnection attempt {attempts} failed",
                    extra={"attempt": attempts, "error": str(e)},
                    exc_info=True,
                )

                if attempts < self._reconnect_attempts:
                    await asyncio.sleep(self._reconnect_delay)

        # If we get here, all reconnection attempts failed
        self._logger.error("All reconnection attempts failed")
        await self._update_state(ConnectionState.ERROR)

    async def _reset_connection(self) -> None:
        """Reset connection state."""
        # Clear any existing state
        self._in_flight.clear()

        # Close any existing streams
        for stream in self._response_streams.values():
            try:
                await stream.aclose()
            except Exception as e:
                self._logger.warning("Error closing stream during reset", exc_info=True)

        self._response_streams.clear()

    async def _initialize_connection(self) -> None:
        """Initialize a new connection."""
        # This method should be overridden by subclasses to implement
        # connection-specific initialization logic
        pass

    async def _heartbeat_loop(self) -> None:
        """Periodically check connection health."""
        while self._state != ConnectionState.DISCONNECTED:
            try:
                await asyncio.sleep(self._heartbeat_interval)

                if not await self._check_connection():
                    continue

                # Send heartbeat if needed
                if (
                    self._last_heartbeat is None
                    or (datetime.utcnow() - self._last_heartbeat).total_seconds()
                    > self._heartbeat_interval
                ):
                    try:
                        await self.send_heartbeat()
                        self._last_heartbeat = datetime.utcnow()
                    except Exception as e:
                        self._logger.warning("Failed to send heartbeat", exc_info=True)
                        await self._handle_connection_error(e)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error("Error in heartbeat loop", exc_info=True)
                await asyncio.sleep(1)  # Prevent tight error loops

    async def send_heartbeat(self) -> None:
        """Send a heartbeat message to keep the connection alive."""
        # This method should be overridden by subclasses to implement
        # protocol-specific heartbeat logic
        pass

    async def __aenter__(self) -> Self:
        """Enter the async context manager and start the session."""
        async with self._state_lock:
            if self._state != ConnectionState.DISCONNECTED:
                raise RuntimeError("Session is already active")

            await self._update_state(ConnectionState.CONNECTING)
            self._connection_attempts = 0

            # Create task group for background tasks
            self._task_group = anyio.create_task_group()
            await self._task_group.__aenter__()

            try:
                # Start the receive loop
                self._task_group.start_soon(self._receive_loop)

                # Start heartbeat if enabled
                if self._heartbeat_interval > 0:
                    self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                await self._update_state(ConnectionState.CONNECTED)
                self._connection_attempts = 0
                self._logger.info("Session started successfully")

            except Exception as e:
                await self._update_state(ConnectionState.ERROR)
                self._logger.error("Failed to start session", exc_info=True)
                await self._task_group.__aexit__(type(e), e, e.__traceback__)
                raise

        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        """Exit the async context manager and clean up resources."""
        self._logger.info("Shutting down session...")

        # Update state
        async with self._state_lock:
            if self._state == ConnectionState.DISCONNECTED:
                return None

            await self._update_state(ConnectionState.DISCONNECTING)

        # Cancel background tasks
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        # Clean up task group
        if hasattr(self, "_task_group") and self._task_group:
            self._task_group.cancel_scope.cancel()
            await self._task_group.__aexit__(exc_type, exc_val, exc_tb)

        # Close all response streams
        for stream in self._response_streams.values():
            try:
                await stream.aclose()
            except Exception as e:
                self._logger.warning("Error closing response stream", exc_info=True)

        # Clean up state
        self._response_streams.clear()
        self._in_flight.clear()

        # Update metrics
        async with self._metrics_lock:
            self._metrics.last_activity = datetime.utcnow()

        await self._update_state(ConnectionState.DISCONNECTED)
        self._logger.info("Session shutdown complete")

        return None

    async def send_request(
        self,
        request: SendRequestT,
        result_type: Type[ReceiveResultT],
        request_read_timeout_seconds: Optional[timedelta] = None,
        metadata: Optional[MessageMetadata] = None,
        timeout: Optional[float] = None,
    ) -> ReceiveResultT:
        """
        Sends a request and wait for a response.

        Args:
            request: The request to send
            result_type: Expected result type for validation
            request_read_timeout_seconds: Timeout for this specific request
            metadata: Optional metadata for the request
            timeout: Timeout in seconds (overrides request_read_timeout_seconds)

        Returns:
            The parsed response of type result_type

        Raises:
            MCPTimeoutError: If the request times out
            MCPValidationError: If the request is invalid
            MCPConnectionError: If there's a connection issue
            McpError: For other JSON-RPC errors
        """
        # Validate connection state
        if self.state != ConnectionState.CONNECTED:
            raise MCPConnectionError(
                f"Cannot send request: session is {self.state.name}"
            )

        # Check in-flight limit
        if len(self._in_flight) >= self._max_in_flight:
            raise MCPConnectionError(
                f"Too many in-flight requests (max {self._max_in_flight}). "
                "Please wait for some requests to complete."
            )

        # Determine timeout
        timeout_seconds = (
            timeout
            or (
                request_read_timeout_seconds.total_seconds()
                if request_read_timeout_seconds
                else None
            )
            or self._default_request_timeout
        )

        # Generate request ID
        request_id = self._get_next_request_id()

        # Log request initiation
        self._logger.debug(
            "Sending request",
            extra={
                "request_id": request_id,
                "request_type": type(request).__name__,
                "timeout": timeout_seconds,
            },
        )

        # Create response stream
        response_stream, response_stream_reader = anyio.create_memory_object_stream[
            Union[JSONRPCResponse, JSONRPCError]
        ](1)

        # Update metrics
        async with self._metrics_lock:
            self._metrics.requests_sent += 1
            self._metrics.last_activity = datetime.utcnow()

        try:
            # Store response stream before sending request
            self._response_streams[request_id] = response_stream

            # Prepare and send JSON-RPC request
            jsonrpc_request = JSONRPCRequest(
                jsonrpc="2.0",
                id=request_id,
                **request.model_dump(by_alias=True, mode="json", exclude_none=True),
            )

            # Send the request
            await self._send_message(
                SessionMessage(
                    message=JSONRPCMessage(jsonrpc_request),
                    metadata=metadata or {},
                )
            )

            # Wait for response with timeout
            try:
                with anyio.fail_after(timeout_seconds):
                    response_or_error = await response_stream_reader.receive()

                    # Update metrics
                    async with self._metrics_lock:
                        self._metrics.requests_completed += 1
                        self._metrics.last_activity = datetime.utcnow()

                    if isinstance(response_or_error, JSONRPCError):
                        self._logger.warning(
                            "Received error response",
                            extra={
                                "request_id": request_id,
                                "error_code": response_or_error.error.code,
                                "error_message": response_or_error.error.message,
                            },
                        )
                        raise McpError(response_or_error.error)

                    # Validate response type
                    try:
                        return result_type.model_validate(response_or_error.result)
                    except Exception as e:
                        self._logger.error(
                            "Response validation failed",
                            extra={
                                "request_id": request_id,
                                "error": str(e),
                                "expected_type": result_type.__name__,
                            },
                            exc_info=True,
                        )
                        raise MCPValidationError(
                            f"Invalid response format: {str(e)}"
                        ) from e

            except TimeoutError:
                self._logger.warning(
                    "Request timed out",
                    extra={
                        "request_id": request_id,
                        "timeout_seconds": timeout_seconds,
                        "request_type": type(request).__name__,
                    },
                )
                async with self._metrics_lock:
                    self._metrics.request_errors += 1
                raise MCPTimeoutError(
                    f"Request {request_id} timed out after {timeout_seconds} seconds"
                )

        except Exception as e:
            # Handle connection errors
            if not isinstance(e, (McpError, MCPTimeoutError)):
                self._logger.error(
                    "Error in send_request",
                    extra={"request_id": request_id},
                    exc_info=True,
                )
                async with self._metrics_lock:
                    self._metrics.request_errors += 1
                    self._metrics.last_error = e

                # Trigger reconnection if needed
                if self.state == ConnectionState.CONNECTED:
                    await self._handle_connection_error(e)

                raise MCPConnectionError(f"Failed to send request: {str(e)}") from e
            raise

        finally:
            # Clean up resources
            self._response_streams.pop(request_id, None)
            await response_stream.aclose()
            await response_stream_reader.aclose()

    async def send_notification(
        self,
        notification: SendNotificationT,
        related_request_id: Optional[RequestId] = None,
    ) -> None:
        """
        Emits a notification, which is a one-way message that does not expect
        a response.

        Args:
            notification: The notification to send
            related_request_id: Optional ID of a related request

        Raises:
            MCPConnectionError: If there's a connection issue
        """
        if self.state != ConnectionState.CONNECTED:
            raise MCPConnectionError(
                f"Cannot send notification: session is {self.state.name}"
            )

        try:
            jsonrpc_notification = JSONRPCNotification(
                jsonrpc="2.0",
                **notification.model_dump(
                    by_alias=True, mode="json", exclude_none=True
                ),
            )

            # Update metrics
            async with self._metrics_lock:
                self._metrics.notifications_sent += 1
                self._metrics.last_activity = datetime.utcnow()

            await self._send_message(
                SessionMessage(
                    message=JSONRPCMessage(jsonrpc_notification),
                    metadata=(
                        MessageMetadata(relatedRequestId=related_request_id)
                        if related_request_id is not None
                        else None
                    ),
                )
            )

            self._logger.debug(
                "Sent notification",
                extra={
                    "notification_type": type(notification).__name__,
                    "related_request_id": related_request_id,
                },
            )

        except Exception as e:
            self._logger.error(
                "Error sending notification",
                extra={"notification_type": type(notification).__name__},
                exc_info=True,
            )

            # Update metrics
            async with self._metrics_lock:
                self._metrics.last_error = e

            # Trigger reconnection if needed
            if self.state == ConnectionState.CONNECTED:
                await self._handle_connection_error(e)

            raise MCPConnectionError(f"Failed to send notification: {str(e)}") from e

    async def _send_message(self, message: SessionMessage) -> None:
        """
        Send a message through the write stream.

        Args:
            message: The message to send

        Raises:
            MCPConnectionError: If there's an error sending the message
        """
        try:
            await self._write_stream.send(message)

            # Update metrics
            async with self._metrics_lock:
                self._metrics.bytes_sent += len(str(message).encode("utf-8"))
                self._metrics.last_activity = datetime.utcnow()

        except Exception as e:
            self._logger.error("Error sending message", exc_info=True)

            # Update metrics
            async with self._metrics_lock:
                self._metrics.last_error = e

            # Trigger reconnection if needed
            if self.state == ConnectionState.CONNECTED:
                await self._handle_connection_error(e)

            raise MCPConnectionError(f"Failed to send message: {str(e)}") from e

    async def _send_response(
        self, request_id: RequestId, response: Union[SendResultT, ErrorData]
    ) -> None:
        """
        Send a response for a request.

        Args:
            request_id: The ID of the request being responded to
            response: The response data or error

        Raises:
            MCPConnectionError: If there's an error sending the response
        """
        try:
            if isinstance(response, ErrorData):
                jsonrpc_error = JSONRPCError(
                    jsonrpc="2.0", id=request_id, error=response
                )
                session_message = SessionMessage(message=JSONRPCMessage(jsonrpc_error))
            else:
                jsonrpc_response = JSONRPCResponse(
                    jsonrpc="2.0",
                    id=request_id,
                    result=response.model_dump(
                        by_alias=True, mode="json", exclude_none=True
                    ),
                )
                session_message = SessionMessage(
                    message=JSONRPCMessage(jsonrpc_response)
                )

            await self._send_message(session_message)

            self._logger.debug(
                "Sent response",
                extra={
                    "request_id": request_id,
                    "is_error": isinstance(response, ErrorData),
                },
            )

        except Exception as e:
            self._logger.error(
                "Error sending response",
                extra={"request_id": request_id},
                exc_info=True,
            )
            raise

    async def _receive_loop(self) -> None:
        """Main receive loop for processing incoming messages."""
        self._logger.debug("Starting receive loop")

        while self.state != ConnectionState.DISCONNECTED:
            try:
                async with anyio.fail_after(
                    self._session_read_timeout_seconds
                    if self._session_read_timeout_seconds
                    else None
                ):
                    # Wait for next message
                    message = await self._read_stream.receive()

                    # Update last activity
                    self._last_activity = datetime.utcnow()
                    async with self._metrics_lock:
                        self._metrics.last_activity = self._last_activity

                    # Process message based on type
                    if isinstance(message, Exception):
                        self._logger.error("Error in receive stream", exc_info=message)
                        await self._handle_connection_error(message)
                        continue

                    if not isinstance(message, SessionMessage) or not message.message:
                        self._logger.warning("Received invalid message format")
                        continue

                    # Update metrics
                    if isinstance(message.message.root, JSONRPCNotification):
                        async with self._metrics_lock:
                            self._metrics.notifications_received += 1

                    # Handle different message types
                    if isinstance(message.message.root, JSONRPCRequest):
                        await self._handle_incoming_request(message)
                    elif isinstance(message.message.root, JSONRPCNotification):
                        await self._handle_notification(message)
                    else:  # Response or error
                        await self._handle_response(message)

            except TimeoutError:
                # Handle read timeout
                if self.state == ConnectionState.CONNECTED:
                    self._logger.debug("Receive loop timeout, checking connection...")
                    await self._check_connection()
            except Exception as e:
                self._logger.error("Error in receive loop", exc_info=True)
                if self.state == ConnectionState.CONNECTED:
                    await self._handle_connection_error(e)
                # Add small delay to prevent tight error loops
                await asyncio.sleep(1)

        self._logger.info("Receive loop exiting")

    async def _handle_incoming_request(self, message: SessionMessage) -> None:
        """Handle an incoming request message."""
        try:
            validated_request = self._receive_request_type.model_validate(
                message.message.root.model_dump(
                    by_alias=True, mode="json", exclude_none=True
                )
            )

            # Create responder with timeout
            responder = RequestResponder(
                request_id=message.message.root.id,
                request_meta=(
                    validated_request.root.params.meta
                    if validated_request.root.params
                    else None
                ),
                request=validated_request,
                session=self,
                on_complete=lambda r: self._in_flight.pop(r.request_id, None),
                timeout=self._default_request_timeout,
            )

            # Track in-flight request
            self._in_flight[responder.request_id] = responder

            # Process the request
            await self._received_request(responder)

            if not responder._completed:  # type: ignore[reportPrivateUsage]
                await self._handle_incoming(responder)

        except Exception as e:
            self._logger.error(
                "Error handling incoming request",
                extra={"request_id": getattr(message.message.root, "id", None)},
                exc_info=True,
            )
            # Send error response if we have a request ID
            if hasattr(message.message.root, "id"):
                await self._send_response(
                    message.message.root.id,
                    ErrorData(
                        code=httpx.codes.INTERNAL_SERVER_ERROR,
                        message=f"Error processing request: {str(e)}",
                    ),
                )

    async def _handle_notification(self, message: SessionMessage) -> None:
        """Handle an incoming notification message."""
        try:
            notification = self._receive_notification_type.model_validate(
                message.message.root.model_dump(
                    by_alias=True, mode="json", exclude_none=True
                )
            )

            # Handle cancellation notifications
            if isinstance(notification.root, CancelledNotification):
                cancelled_id = notification.root.params.requestId
                if cancelled_id in self._in_flight:
                    await self._in_flight[cancelled_id].cancel()
            else:
                await self._received_notification(notification)
                await self._handle_incoming(notification)

        except Exception as e:
            self._logger.error(
                "Error handling notification",
                extra={"method": getattr(message.message.root, "method", None)},
                exc_info=True,
            )

    async def _handle_response(self, message: SessionMessage) -> None:
        """Handle an incoming response or error message."""
        stream = self._response_streams.pop(message.message.root.id, None)
        if stream:
            try:
                await stream.send(message.message.root)
            except Exception as e:
                self._logger.error(
                    "Error sending response to stream",
                    extra={"request_id": message.message.root.id},
                    exc_info=True,
                )
        else:
            self._logger.warning(
                "Received response for unknown request",
                extra={"request_id": message.message.root.id},
            )
            await self._handle_incoming(
                RuntimeError(
                    f"Received response with unknown request ID: {message.message.root.id}"
                )
            )

    async def _received_request(
        self, responder: RequestResponder[ReceiveRequestT, SendResultT]
    ) -> None:
        """
        Can be overridden by subclasses to handle a request without needing to
        listen on the message stream.

        If the request is responded to within this method, it will not be
        forwarded on to the message stream.

        Args:
            responder: The request responder for sending the response
        """
        # Default implementation does nothing - subclasses should override
        pass

    async def _received_notification(self, notification: ReceiveNotificationT) -> None:
        """
        Can be overridden by subclasses to handle a notification without needing
        to listen on the message stream.

        Args:
            notification: The received notification
        """
        # Default implementation does nothing - subclasses should override
        pass

    async def send_progress_notification(
        self,
        progress_token: Union[str, int],
        progress: float,
        total: Optional[float] = None,
    ) -> None:
        """
        Sends a progress notification for a request that is currently being
        processed.

        Args:
            progress_token: A token to identify the progress notification
            progress: Current progress value
            total: Optional total value for calculating percentage

        Raises:
            MCPConnectionError: If there's a connection issue
        """
        if self.state != ConnectionState.CONNECTED:
            raise MCPConnectionError(
                f"Cannot send progress: session is {self.state.name}"
            )

        try:
            notification = ProgressNotification(
                params=ProgressParams(
                    token=progress_token,
                    value=progress,
                    total=total,
                )
            )

            await self.send_notification(notification)

            self._logger.debug(
                "Sent progress notification",
                extra={
                    "progress_token": progress_token,
                    "progress": progress,
                    "total": total,
                },
            )

        except Exception as e:
            self._logger.error(
                "Error sending progress notification",
                extra={"progress_token": progress_token},
                exc_info=True,
            )

            # Update metrics
            async with self._metrics_lock:
                self._metrics.last_error = e

            # Trigger reconnection if needed
            if self.state == ConnectionState.CONNECTED:
                await self._handle_connection_error(e)

            raise MCPConnectionError(f"Failed to send progress: {str(e)}") from e

    async def _handle_incoming(
        self,
        req: Union[
            RequestResponder[ReceiveRequestT, SendResultT],
            ReceiveNotificationT,
            Exception,
        ],
    ) -> None:
        """
        A generic handler for incoming messages. Overwritten by subclasses.

        Args:
            req: The incoming message, which can be a request responder,
                 notification, or exception
        """
        # Default implementation does nothing - subclasses should override
        pass
