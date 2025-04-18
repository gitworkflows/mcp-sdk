from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class TextRequest(BaseModel):
    """Text processing request model"""
    prompt: str
    model: str = Field(default="gpt-4")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=150, gt=0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)
    stop: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class TextResponse(BaseModel):
    """Text processing response model"""
    id: str
    model: str
    content: str
    created_at: str
    usage: Dict[str, int]
    metadata: Optional[Dict[str, Any]] = None 