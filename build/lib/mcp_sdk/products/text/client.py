from typing import Optional, Dict, Any
from ...client import MCPClient
from .models import TextRequest, TextResponse

class TextClient:
    """Client for text processing operations"""

    def __init__(self, base_client: MCPClient):
        """
        Initialize the text client.

        Args:
            base_client: An instance of MCPClient
        """
        self.client = base_client

    def generate(self, prompt: str, **kwargs) -> TextResponse:
        """
        Generate text based on a prompt.

        Args:
            prompt: The input prompt
            **kwargs: Additional generation parameters

        Returns:
            TextResponse: The generated text response
        """
        request = TextRequest(
            prompt=prompt,
            **kwargs
        )
        response = self.client.send(request.dict())
        return TextResponse(**response)

    def summarize(self, text: str, **kwargs) -> TextResponse:
        """
        Summarize the given text.

        Args:
            text: The text to summarize
            **kwargs: Additional summarization parameters

        Returns:
            TextResponse: The summary response
        """
        request = TextRequest(
            prompt=f"Summarize the following text:\n\n{text}",
            **kwargs
        )
        response = self.client.send(request.dict())
        return TextResponse(**response)

    def translate(self, text: str, target_language: str, **kwargs) -> TextResponse:
        """
        Translate text to the target language.

        Args:
            text: The text to translate
            target_language: The target language code
            **kwargs: Additional translation parameters

        Returns:
            TextResponse: The translation response
        """
        request = TextRequest(
            prompt=f"Translate the following text to {target_language}:\n\n{text}",
            **kwargs
        )
        response = self.client.send(request.dict())
        return TextResponse(**response)

    def analyze_sentiment(self, text: str, **kwargs) -> TextResponse:
        """
        Analyze the sentiment of the given text.

        Args:
            text: The text to analyze
            **kwargs: Additional analysis parameters

        Returns:
            TextResponse: The sentiment analysis response
        """
        request = TextRequest(
            prompt=f"Analyze the sentiment of the following text:\n\n{text}",
            **kwargs
        )
        response = self.client.send(request.dict())
        return TextResponse(**response)

    def extract_keywords(self, text: str, **kwargs) -> TextResponse:
        """
        Extract keywords from the given text.

        Args:
            text: The text to extract keywords from
            **kwargs: Additional extraction parameters

        Returns:
            TextResponse: The keywords extraction response
        """
        request = TextRequest(
            prompt=f"Extract keywords from the following text:\n\n{text}",
            **kwargs
        )
        response = self.client.send(request.dict())
        return TextResponse(**response) 