from typing import Optional, Dict, Any, TypeVar, Generic, Type, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# Type variables for generic message handling
T = TypeVar('T', bound=BaseModel)
R = TypeVar('R', bound=BaseModel)
P = TypeVar('P', bound=BaseModel)

class MessageType(str, Enum):
    """Types of messages that can be processed"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    SYSTEM = "system"

class MessageStatus(str, Enum):
    """Status of message processing"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class MessageMetadata(BaseModel):
    """Metadata for messages"""
    source: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    priority: int = Field(default=0, ge=0, le=10)
    tags: list[str] = Field(default_factory=list)
    custom_data: Optional[Dict[str, Any]] = None

class MessageContext(BaseModel, Generic[P]):
    """Generic context for messages with parameters"""
    content: str
    parameters: P
    metadata: Optional[Dict[str, Any]] = None

class BaseMessage(BaseModel, Generic[T, P]):
    """Base message class with type safety"""
    id: str
    type: MessageType
    content: T
    context: MessageContext[P]
    metadata: MessageMetadata
    status: MessageStatus = MessageStatus.PENDING
    error: Optional[str] = None

class MessageResponse(BaseModel, Generic[R]):
    """Base response class with type safety"""
    message_id: str
    type: MessageType
    result: R
    metadata: MessageMetadata
    processing_time: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MessageHandler(Generic[T, P, R]):
    """Base message handler with type safety"""
    def __init__(self, message_type: MessageType):
        self.message_type = message_type

    async def process(self, message: BaseMessage[T, P]) -> MessageResponse[R]:
        """Process a message and return a typed response"""
        raise NotImplementedError("Subclasses must implement process()")

    def validate(self, message: BaseMessage[T, P]) -> None:
        """Validate a message before processing"""
        if message.type != self.message_type:
            raise ValueError(f"Invalid message type. Expected {self.message_type}, got {message.type}")

class MessageProcessor:
    """Message processor that routes messages to appropriate handlers"""
    def __init__(self):
        self._handlers: Dict[MessageType, MessageHandler] = {}

    def register_handler(self, handler: MessageHandler) -> None:
        """Register a message handler"""
        self._handlers[handler.message_type] = handler

    async def process(self, message: BaseMessage) -> MessageResponse:
        """Process a message using the appropriate handler"""
        handler = self._handlers.get(message.type)
        if not handler:
            raise ValueError(f"No handler registered for message type: {message.type}")
        
        handler.validate(message)
        return await handler.process(message)

# Example usage:
class TextParameters(BaseModel):
    """Parameters for text processing"""
    language: Optional[str] = None
    format: Optional[str] = None
    max_length: Optional[int] = None
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)

class TextContent(BaseModel):
    """Content for text messages"""
    text: str
    language: Optional[str] = None
    format: Optional[str] = None

class TextResult(BaseModel):
    """Result for text processing"""
    processed_text: str
    language: str
    confidence: float
    parameters: TextParameters

class TextMessage(BaseMessage[TextContent, TextParameters]):
    """Text message with type-safe content and parameters"""
    pass

class TextResponse(MessageResponse[TextResult]):
    """Text response with type-safe result"""
    pass

class TextHandler(MessageHandler[TextContent, TextParameters, TextResult]):
    """Handler for text messages"""
    def __init__(self):
        super().__init__(MessageType.TEXT)

    async def process(self, message: TextMessage) -> TextResponse:
        # Process text message and return typed response
        result = TextResult(
            processed_text=message.content.text.upper(),
            language=message.context.parameters.language or "en",
            confidence=1.0,
            parameters=message.context.parameters
        )
        
        return TextResponse(
            message_id=message.id,
            type=message.type,
            result=result,
            metadata=message.metadata,
            processing_time=0.1
        ) 