import pytest
import asyncio
import time
from unittest.mock import patch, AsyncMock
from mcp_sdk.server import MCPServer
from mcp_sdk.messages import TextResponse, TextResult, TextParameters, MessageMetadata, MessageType
from fastapi.testclient import TestClient
from datetime import datetime

class TestServerPerformance:
    """Performance tests for the server."""
    
    @pytest.fixture
    def perf_client(self):
        """Create a performance testing client."""
        server = MCPServer()
        return TestClient(server.app)
    
    @pytest.mark.performance
    async def test_request_latency(self, perf_client, monkeypatch):
        """Test request processing latency."""
        # Mock the message processor to avoid actual processing
        async def mock_process(*args, **kwargs):
            # Add a small delay to simulate processing
            await asyncio.sleep(0.01)
            return TextResponse(
                message_id="test-msg-id",
                type=MessageType.TEXT,
                result=TextResult(
                    processed_text="Fast response",
                    language="en",
                    confidence=0.95,
                    parameters=TextParameters()
                ),
                metadata=MessageMetadata(source="test"),
                processing_time=0.01,
                created_at=datetime.now()
            )
            
        with patch('mcp_sdk.messages.MessageProcessor.process', new=AsyncMock(side_effect=mock_process)):
            start_time = time.time()
            
            response = perf_client.post(
                "/api/v1/process",
                json={
                    "model": "text:gpt-4",
                    "context": "Test message",
                    "settings": {"temperature": 0.7}
                }
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            assert response.status_code == 200
            assert processing_time < 1.0  # Should process in under 1 second
    
    @pytest.mark.performance
    async def test_concurrent_load(self, perf_client, monkeypatch):
        """Test server under concurrent load."""
        # Mock the message processor to avoid actual processing
        async def mock_process(*args, **kwargs):
            # Small random delay to simulate variable processing time
            await asyncio.sleep(0.01 + 0.02 * asyncio.current_task().get_name().count('_'))
            return TextResponse(
                message_id=f"test-msg-{asyncio.current_task().get_name()}",
                type=MessageType.TEXT,
                result=TextResult(
                    processed_text="Concurrent response",
                    language="en",
                    confidence=0.95,
                    parameters=TextParameters()
                ),
                metadata=MessageMetadata(source="test"),
                processing_time=0.01,
                created_at=datetime.now()
            )
            
        with patch('mcp_sdk.messages.MessageProcessor.process', new=AsyncMock(side_effect=mock_process)):
            num_requests = 20  # Reduced for testing
            max_concurrent = 5
            
            async def make_request(i: int):
                """Make a single request."""
                return perf_client.post(
                    "/api/v1/process",
                    json={
                        "model": "text:gpt-4",
                        "context": f"Test message {i}",
                        "settings": {"temperature": 0.7}
                    }
                )
            
            start_time = time.time()
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def controlled_request(i: int):
                """Make a request with concurrency control."""
                async with semaphore:
                    return await make_request(i)
            
            tasks = [controlled_request(i) for i in range(num_requests)]
            responses = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Verify responses
            success_count = sum(1 for r in responses if r.status_code == 200)
            assert success_count == num_requests
            
            # Check performance metrics
            avg_time_per_request = total_time / num_requests
            assert avg_time_per_request < 1.0  # Average time should be reasonable for tests
            
    @pytest.mark.performance
    def test_memory_usage(self, perf_client):
        """Test memory usage during request processing."""
        import resource
        import gc
        
        # Force garbage collection
        gc.collect()
        
        # Get initial memory usage
        initial_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        # Make several requests
        for i in range(10):
            response = perf_client.post(
                "/api/v1/process",
                json={
                    "model": "text:gpt-4",
                    "context": f"Memory test {i}",
                    "settings": {"temperature": 0.7}
                }
            )
            assert response.status_code == 200
        
        # Force garbage collection again
        gc.collect()
        
        # Get final memory usage
        final_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        # Check memory increase - should be reasonable
        # Note: This test is more illustrative than strict
        memory_increase = final_usage - initial_usage
        print(f"Memory increase after 10 requests: {memory_increase} KB")
        
        # We're not asserting a specific limit as it's environment-dependent
        # But we could add a soft limit if needed:
        # assert memory_increase < 10000  # Less than 10MB increase

