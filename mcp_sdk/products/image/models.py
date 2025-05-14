from typing import Optional, Dict, Any, List, Union, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum
import datetime


class OperationType(str, Enum):
    """Supported image operation types"""

    GENERATE = "generate"
    EDIT = "edit"
    VARIATION = "variation"
    ANALYZE = "analyze"
    CAPTION = "caption"
    RESIZE = "resize"
    STYLE = "style"


class AnalysisType(str, Enum):
    """Types of image analysis"""

    GENERAL = "general"
    OBJECTS = "objects"
    FACES = "faces"
    TEXT = "text"
    COLORS = "colors"
    NSFW = "nsfw"


class ImageRequest(BaseModel):
    """Image processing request model"""

    prompt: Optional[str] = None
    operation: OperationType
    image: Optional[str] = None  # Base64 encoded image
    model: str = Field(default="dall-e-3")
    size: str = Field(default="1024x1024")
    quality: str = Field(default="standard")
    style: Optional[str] = None
    n: int = Field(default=1, ge=1, le=4)
    metadata: Optional[Dict[str, Any]] = None
    analysis_type: Optional[AnalysisType] = Field(default=AnalysisType.GENERAL)
    max_length: Optional[int] = Field(default=100, ge=10, le=1000)
    mask: Optional[str] = None  # Base64 encoded mask for edit operation

    @validator("prompt")
    def validate_prompt(cls, v, values):
        """Validate that prompt is provided for operations that require it"""
        operation = values.get("operation")
        if operation in [OperationType.GENERATE, OperationType.EDIT] and not v:
            raise ValueError(f"Prompt is required for {operation} operation")
        return v

    @validator("image")
    def validate_image(cls, v, values):
        """Validate that image is provided for operations that require it"""
        operation = values.get("operation")
        if (
            operation
            in [
                OperationType.EDIT,
                OperationType.VARIATION,
                OperationType.ANALYZE,
                OperationType.CAPTION,
                OperationType.RESIZE,
                OperationType.STYLE,
            ]
            and not v
        ):
            raise ValueError(f"Image is required for {operation} operation")
        return v


class AnalysisResult(BaseModel):
    """Analysis result for image analysis operations"""

    objects: Optional[List[str]] = None
    scene: Optional[str] = None
    colors: Optional[List[str]] = None
    confidence: Optional[float] = None
    faces: Optional[int] = None
    text_content: Optional[str] = None
    nsfw_score: Optional[float] = None
    tags: Optional[List[str]] = None


class ImageResponse(BaseModel):
    """Image processing response model"""

    id: str
    model: str
    images: Optional[List[str]] = None  # List of base64 encoded images
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    usage: Dict[str, int] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None
    caption: Optional[str] = None  # For caption operation
    analysis: Optional[AnalysisResult] = None  # For analyze operation
    error: Optional[str] = None  # For error handling

    @validator("images", "caption", "analysis")
    def validate_response_content(cls, v, values):
        """Validate that appropriate content is provided based on the operation"""
        operation = values.get("metadata", {}).get("operation")

        if operation in [
            OperationType.GENERATE,
            OperationType.EDIT,
            OperationType.VARIATION,
            OperationType.RESIZE,
            OperationType.STYLE,
        ] and not values.get("images"):
            if not values.get("error"):
                raise ValueError(
                    f"Images are required for {operation} operation response"
                )

        if operation == OperationType.CAPTION and not values.get("caption"):
            if not values.get("error"):
                raise ValueError("Caption is required for caption operation response")

        if operation == OperationType.ANALYZE and not values.get("analysis"):
            if not values.get("error"):
                raise ValueError("Analysis is required for analyze operation response")

        return v
