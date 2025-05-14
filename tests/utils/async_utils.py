import asyncio
import pytest
from typing import Any, Callable, Awaitable, TypeVar, List

T = TypeVar('T')

class AsyncTestUtils:
    """Utilities for async testing."""
    
    @staticmethod
    async def collect_results(count: int, fn: Callable[[], Awaitable[T]]) -> List[T]:
        """Collect results from multiple async function calls."""
        tasks = [fn() for _ in range(count)]
        return await asyncio.gather(*tasks)

    @staticmethod
    async def with_timeout(coro: Awaitable[T], timeout: float) -> T:
        """Run coroutine with timeout."""
        try:
            return await asyncio.wait_for(coro, timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout} seconds")

    @staticmethod
    async def simulate_load(
        request_fn: Callable[[], Awaitable[T]],
        num_requests: int,
        concurrency: int
    ) -> List[T]:
        """Simulate load with controlled concurrency."""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def controlled_request():
            async with semaphore:
                return await request_fn()
        
        return await AsyncTestUtils.collect_results(num_requests, controlled_request)
    
    @staticmethod
    async def staggered_requests(
        request_fn: Callable[[int], Awaitable[T]], 
        count: int,
        delay: float = 0.1
    ) -> List[T]:
        """Execute requests with staggered timing."""
        results = []
        for i in range(count):
            results.append(await request_fn(i))
            if i < count - 1:  # Don't delay after the last request
                await asyncio.sleep(delay)
        return results

@pytest.fixture
async def async_test_utils():
    """Fixture for async test utilities."""
    return AsyncTestUtils()

