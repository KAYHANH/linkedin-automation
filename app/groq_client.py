"""Groq client wrapper for structured and creative generation."""

import json
import logging
from typing import Any, Dict, List, Optional
from groq import Groq

from app.config import get_settings

logger = logging.getLogger(__name__)


class GroqClient:
    """Wrapper around the official Groq Python SDK with error redaction and JSON parsing."""

    def __init__(self, api_key: Optional[str] = None, client: Optional[Groq] = None):
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key
        self._client = client or (Groq(api_key=self.api_key) if self.api_key else None)

    def generate_chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1500,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """Call Groq API with robust error handling and token redaction."""
        settings = get_settings()

        if not self._client:
            raise ValueError("Groq client not initialized: GROQ_API_KEY is missing or invalid.")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        kwargs: Dict[str, Any] = {
            "model": settings.groq_model,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            content = choice.message.content or ""
            return content.strip()
        except Exception as e:
            redacted_msg = settings.redact(str(e))
            logger.error("Groq API error during generation: %s", redacted_msg)
            raise RuntimeError(f"Groq API call failed: {redacted_msg}") from None
