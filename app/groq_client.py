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

    @property
    def client(self) -> Optional[Groq]:
        """Access underlying official Groq SDK client instance."""
        return self._client

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

        models_to_try = [settings.groq_model]
        fallbacks = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
        for fb in fallbacks:
            if fb not in models_to_try:
                models_to_try.append(fb)

        last_error = None
        for candidate_model in models_to_try:
            kwargs["model"] = candidate_model
            try:
                response = self._client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                content = choice.message.content or ""
                return content.strip()
            except Exception as e:
                err_str = str(e).lower()
                last_error = e
                # Fallback only if the model is not recognized or not available
                if "does not exist" in err_str or "model_not_found" in err_str or "404" in err_str:
                    logger.warning("Groq model %s not available, attempting fallback...", candidate_model)
                    continue
                # For auth, rate limits, or validation errors, do not loop
                break

        redacted_msg = settings.redact(str(last_error))
        logger.error("Groq API error during generation: %s", redacted_msg)
        raise RuntimeError(f"Groq API call failed: {redacted_msg}") from None
