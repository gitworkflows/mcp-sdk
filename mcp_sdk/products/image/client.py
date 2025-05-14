from typing import Optional, Dict, Any, List
from ...client import MCPClient
from .models import ImageRequest, ImageResponse


class ImageClient:
    """Client for image processing operations"""

    def __init__(self, base_client: MCPClient):
        """
        Initialize the image client.

        Args:
            base_client: An instance of MCPClient
        """
        self.client = base_client

    def generate(self, prompt: str, size: str = "1024x1024", **kwargs) -> ImageResponse:
        """
        Generate an image based on a text prompt.

        Args:
            prompt: The text description of the image to generate
            size: The size of the generated image (e.g., "1024x1024")
            **kwargs: Additional generation parameters

        Returns:
            ImageResponse: The generated image response
        """
        request = ImageRequest(prompt=prompt, operation="generate", size=size, **kwargs)
        response = self.client.send(request.dict())
        return ImageResponse(**response)

    def edit(self, image: str, prompt: str, **kwargs) -> ImageResponse:
        """
        Edit an existing image based on a text prompt.

        Args:
            image: Base64 encoded image to edit
            prompt: The text description of the desired edits
            **kwargs: Additional edit parameters

        Returns:
            ImageResponse: The edited image response
        """
        request = ImageRequest(prompt=prompt, operation="edit", image=image, **kwargs)
        response = self.client.send(request.dict())
        return ImageResponse(**response)

    def resize(self, image: str, size: str, **kwargs) -> ImageResponse:
        """
        Resize an image to the specified dimensions.

        Args:
            image: Base64 encoded image to resize
            size: Target size (e.g., "512x512")
            **kwargs: Additional resize parameters

        Returns:
            ImageResponse: The resized image response
        """
        request = ImageRequest(operation="resize", image=image, size=size, **kwargs)
        response = self.client.send(request.dict())
        return ImageResponse(**response)

    def apply_style(self, image: str, style: str, **kwargs) -> ImageResponse:
        """
        Apply a specific style to an image.

        Args:
            image: Base64 encoded image to style
            style: The style to apply (e.g., "cartoon", "oil-painting")
            **kwargs: Additional style parameters

        Returns:
            ImageResponse: The styled image response
        """
        request = ImageRequest(operation="style", image=image, style=style, **kwargs)
        response = self.client.send(request.dict())
        return ImageResponse(**response)

    def analyze(self, image: str, **kwargs) -> ImageResponse:
        """
        Analyze the content of an image.

        Args:
            image: Base64 encoded image to analyze
            **kwargs: Additional analysis parameters

        Returns:
            ImageResponse: The analysis response
        """
        request = ImageRequest(operation="analyze", image=image, **kwargs)
        response = self.client.send(request.dict())
        return ImageResponse(**response)
