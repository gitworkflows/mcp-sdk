from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class ImageRequest(BaseModel):
    """Image processing request model"""
    prompt: Optional[str] = None
    operation: str
    image: Optional[str] = None  # Base64 encoded image
    model: str = Field(default="dall-e-3")
    size: str = Field(default="1024x1024")
    quality: str = Field(default="standard")
    style: Optional[str] = None
    n: int = Field(default=1, ge=1, le=4)
    metadata: Optional[Dict[str, Any]] = None

class ImageResponse(BaseModel):
    """Image processing response model"""
    id: str
    model: str
    images: List[str]  # List of base64 encoded images
    created_at: str
    usage: Dict[str, int]
    metadata: Optional[Dict[str, Any]] = None 