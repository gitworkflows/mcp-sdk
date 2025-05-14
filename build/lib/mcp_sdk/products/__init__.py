"""
MCP Products - Collection of product-specific modules
"""

from . import text
from . import image
from . import audio
from . import video

# For convenience, allow direct imports
from .text import (
    generate as text_generate,
    summarize,
    translate,
    analyze_sentiment,
    extract_keywords
)

from .image import (
    generate as image_generate,
    edit,
    variation,
    analyze as image_analyze,
    caption
)

from .audio import (
    generate as audio_generate,
    transcribe,
    analyze as audio_analyze
)

from .video import (
    generate as video_generate,
    analyze as video_analyze,
    extract_frames
)

__all__ = [
    # Module exports
    "text",
    "image",
    "audio",
    "video",
    
    # Text functions
    "text_generate",
    "summarize",
    "translate",
    "analyze_sentiment",
    "extract_keywords",
    
    # Image functions
    "image_generate",
    "edit",
    "variation",
    "image_analyze",
    "caption",
    
    # Audio functions
    "audio_generate",
    "transcribe",
    "audio_analyze",
    
    # Video functions
    "video_generate",
    "video_analyze",
    "extract_frames"
]
