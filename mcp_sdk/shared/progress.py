"""
Progress tracking utilities for MCP operations.

This module provides tools for tracking and reporting progress of long-running
operations through the MCP protocol.
"""

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from mcp_sdk.shared.context import LifespanContextT, RequestContext
from mcp_sdk.shared.exceptions import McpValidationError
from mcp_sdk.shared.session import (
    BaseSession,
    ReceiveNotificationT,
    ReceiveRequestT,
    SendNotificationT,
    SendRequestT,
    SendResultT,
)
from mcp_sdk.types import ProgressToken

# Define type variables for better type hints
T = TypeVar('T')


class Progress(BaseModel):
    """Represents progress information for an operation.
    
    Attributes:
        progress: Current progress value (e.g., number of items processed)
        total: Total expected value (None if unknown)
    """
    progress: float
    total: float | None


@dataclass
class ProgressContext(
    Generic[
        SendRequestT,
        SendNotificationT,
        SendResultT,
        ReceiveRequestT,
        ReceiveNotificationT,
    ]
):
    """Context for tracking and reporting progress of an operation.
    
    This class provides methods to update and report progress during long-running
    operations. It's typically used as a context manager via the `progress()`
    function.
    
    Attributes:
        session: The MCP session for sending progress notifications
        progress_token: Unique token identifying this progress tracker
        total: Total expected progress value (None if unknown)
        current: Current progress value (starts at 0.0)
    """
    
    session: BaseSession[
        SendRequestT,
        SendNotificationT,
        SendResultT,
        ReceiveRequestT,
        ReceiveNotificationT,
    ]
    progress_token: ProgressToken
    total: float | None
    current: float = field(default=0.0, init=False)
    _last_reported: float = field(default=0.0, init=False)
    _min_report_interval: float = 0.1  # Minimum seconds between progress reports

    async def progress(self, amount: float = 1.0) -> None:
        """Update the progress by the specified amount.
        
        Args:
            amount: The amount to add to the current progress
            
        Raises:
            ValueError: If amount is negative
        """
        if amount < 0:
            raise ValueError("Progress amount cannot be negative")
            
        import time
        current_time = time.time()
        
        self.current += amount
        
        # Throttle progress updates to avoid flooding the client
        if current_time - self._last_reported >= self._min_report_interval:
            await self._report_progress()
            self._last_reported = current_time
    
    async def _report_progress(self) -> None:
        """Send a progress notification to the client."""
        await self.session.send_progress_notification(
            self.progress_token, self.current, total=self.total
        )
    
    async def set_total(self, total: float | None) -> None:
        """Update the total expected progress value.
        
        Args:
            total: New total value, or None if unknown
        """
        self.total = total
        await self._report_progress()
    
    async def set_progress(self, current: float) -> None:
        """Set the current progress to a specific value.
        
        Args:
            current: The new current progress value
            
        Raises:
            ValueError: If current is negative
        """
        if current < 0:
            raise ValueError("Progress value cannot be negative")
        self.current = current
        await self._report_progress()
    
    def as_fraction(self) -> float | None:
        """Get the current progress as a fraction of the total (0.0 to 1.0).
        
        Returns:
            Progress as a fraction, or None if total is not set
        """
        if self.total is None or self.total == 0:
            return None
        return min(1.0, max(0.0, self.current / self.total))
    
    def as_percent(self) -> float | None:
        """Get the current progress as a percentage (0.0 to 100.0).
        
        Returns:
            Progress as a percentage, or None if total is not set
        """
        fraction = self.as_fraction()
        return fraction * 100.0 if fraction is not None else None


@contextmanager
def progress(
    ctx: RequestContext[
        BaseSession[
            SendRequestT,
            SendNotificationT,
            SendResultT,
            ReceiveRequestT,
            ReceiveNotificationT,
        ],
        LifespanContextT,
    ],
    total: float | None = None,
) -> Generator[
    ProgressContext[
        SendRequestT,
        SendNotificationT,
        SendResultT,
        ReceiveRequestT,
        ReceiveNotificationT,
    ],
    None,
]:
    """Context manager for tracking progress of an operation.
    
    This context manager creates a ProgressContext that can be used to report
    progress during a long-running operation. Progress notifications are
    automatically throttled to avoid overwhelming the client.
    
    Args:
        ctx: The request context containing the MCP session
        total: Total expected progress value (None if unknown)
        
    Yields:
        A ProgressContext instance for reporting progress
        
    Raises:
        McpValidationError: If no progress token is available in the context
        
    Example:
        ```python
        with progress(ctx, total=100) as p:
            for i in range(100):
                # Do some work...
                await p.progress(1)  # Report progress for each item
        ```
    """
    if ctx.meta is None or ctx.meta.progressToken is None:
        raise McpValidationError("No progress token provided in request context")

    progress_ctx = ProgressContext(
        session=ctx.session,
        progress_token=ctx.meta.progressToken,
        total=total
    )
    
    try:
        yield progress_ctx
    finally:
        # Ensure final progress is reported
        try:
            import asyncio
            asyncio.create_task(progress_ctx._report_progress())
        except Exception:
            # Don't let progress reporting errors propagate
            pass