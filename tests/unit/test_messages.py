import pytest
from datetime import datetime
from mcp_sdk.messages import (
    MessageType,
    MessageStatus,
    MessageMetadata,
    MessageContext,
    BaseMessage,
    MessageResponse,
    MessageHandler,
    MessageProcessor,
    TextParameters,
    TextContent,
    TextResult,
    TextMessage,
    TextResponse,
    TextHandler
)

class TestMessages:
    """Tests for message types and processing."""

    @pytest.fixture
    def text_parameters(self):
        return TextParameters(
            language="en",
            format="markdown",
            max_length=100,
            temperature=0.8
        )

    @pytest.fixture
    def message_metadata(self):
        return MessageMetadata(
            source="test-client",
            priority=5,
            tags=["test", "example"]
        )

    @pytest.fixture
    def text_content(self):
        return TextContent(
            text="Hello, world!",
            language="en",
            format="markdown"
        )

    @pytest.fixture
    def text_message(self, text_content, text_parameters, message_metadata):
        context = MessageContext(
            content="Test context",
            parameters=text_parameters
        )
        return TextMessage(
            id="msg-123",
            type=MessageType.TEXT,
            content=text_content,
            context=context,
            metadata=message_metadata,
            status=MessageStatus.PENDING
        )

    def test_message_type_enum(self):
        """Test MessageType enum values."""
        assert MessageType.TEXT == "text"
        assert MessageType.IMAGE == "image"
        assert MessageType.AUDIO == "audio"
        assert MessageType.VIDEO == "video"
        assert MessageType.SYSTEM == "system"

    def test_message_status_enum(self):
        """Test MessageStatus enum values."""
        assert MessageStatus.PENDING == "pending"
        assert MessageStatus.PROCESSING == "processing"
        assert MessageStatus.COMPLETED == "completed"
        assert MessageStatus.FAILED == "failed"

    def test_message_metadata(self, message_metadata):
        """Test MessageMetadata creation and validation."""
        assert message_metadata.source == "test-client"
        assert message_metadata.priority == 5
        assert "test" in message_metadata.tags
        assert isinstance(message_metadata.timestamp, datetime)

    def test_text_parameters(self, text_parameters):
        """Test TextParameters creation and validation."""
        assert text_parameters.language == "en"
        assert text_parameters.format == "markdown"
        assert text_parameters.max_length == 100
        assert text_parameters.temperature == 0.8

    def test_text_message(self, text_message):
        """Test TextMessage creation and validation."""
        assert text_message.id == "msg-123"
        assert text_message.type == MessageType.TEXT
        assert text_message.content.text == "Hello, world!"
        assert text_message.status == MessageStatus.PENDING
        assert text_message.context.parameters.language == "en"

    async def test_text_handler(self, text_message):
        """Test TextHandler processing a TextMessage."""
        handler = TextHandler()
        response = await handler.process(text_message)
        
        assert isinstance(response, TextResponse)
        assert response.message_id == text_message.id
        assert response.type == MessageType.TEXT
        assert response.result.processed_text == "HELLO, WORLD!"
        assert response.result.language == "en"
        assert response.result.confidence > 0

    def test_message_processor_registration(self):
        """Test registering handlers with MessageProcessor."""
        processor = MessageProcessor()
        handler = TextHandler()
        
        processor.register_handler(handler)
        assert MessageType.TEXT in processor._handlers
        assert processor._handlers[MessageType.TEXT] == handler

    async def test_message_processor_processing(self, text_message):
        """Test MessageProcessor processing a message."""
        processor = MessageProcessor()
        handler = TextHandler()
        processor.register_handler(handler)
        
        response = await processor.process(text_message)
        
        assert isinstance(response, TextResponse)
        assert response.message_id == text_message.id
        assert response.type == MessageType.TEXT
        assert response.result.processed_text == "HELLO, WORLD!"

    @pytest.mark.asyncio
    async def test_message_processor_unknown_handler(self, text_message):
        """Test MessageProcessor with unknown message type."""
        processor = MessageProcessor()
        metadata = MessageMetadata(
            message_id=uuid.uuid4(),
            timestamp=datetime.utcnow(),
            status=MessageStatus.PENDING,
            source="test"
        )
        message = TextMessage(
            type=MessageType.TEXT,
            content="Test message",
            metadata=metadata
        )
        
        with pytest.raises(ValueError, match="No handler registered"):
            await processor.process(message)

    def test_message_handler_validation(self, text_message):
        """Test MessageHandler validation."""
        handler = TextHandler()
        
        # Should validate successfully
        handler.validate(text_message)
        
        # Create a message with wrong type
        wrong_message = text_message.model_copy()
        wrong_message.type = MessageType.IMAGE
        
        with pytest.raises(ValueError, match="Invalid message type"):
            handler.validate(wrong_message)

    def test_text_result(self):
        """Test TextResult creation and validation."""
        from mcp_sdk.messages import TextParameters, TextResult
        
        params = TextParameters(
            language="en",
            confidence=0.95,
            sentiment="positive"
        )
        
        result = TextResult(
            processed_text="PROCESSED TEXT",
            language="en",
            confidence=0.95,
            parameters=params
        )
        
        assert result.processed_text == "PROCESSED TEXT"
        assert result.language == "en"
        assert result.confidence == 0.95
        assert result.parameters == params
