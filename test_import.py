#!/usr/bin/env python3
"""
Test script to verify that the mcp_sdk package imports correctly
"""

try:
    import mcp_sdk
    from mcp_sdk.products import (
        text, image, audio, video,
        text_generate, summarize, translate,
        image_generate, edit, variation,
        audio_generate, transcribe,
        video_generate, extract_frames
    )
    
    print("✅ Successfully imported mcp_sdk and all modules!")
    print(f"✅ Package version: {mcp_sdk.__version__}")
    
    # Test a simple function
    result = text_generate("Hello, world!")
    print(f"✅ Text generation test: {result}")
    
    # Test image generation
    result = image_generate("A beautiful sunset")
    print(f"✅ Image generation test: {result}")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")

