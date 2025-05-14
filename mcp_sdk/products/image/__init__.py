"""
Image Processing Module - Tools for image-based operations
"""

from .client import ImageClient
from .models import ImageRequest, ImageResponse
from .tools import generate, edit, variation, analyze, caption

# For consistency with products/__init__.py naming conventions
image_generate = generate
image_analyze = analyze

__all__ = [
    # Classes
    "ImageClient",
    "ImageRequest",
    "ImageResponse",
    # Direct function exports
    "generate",
    "edit",
    "variation",
    "analyze",
    "caption",
    # Aliased function exports (for consistent naming across modules)
    "image_generate",
    "image_analyze",
]
