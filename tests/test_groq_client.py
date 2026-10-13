"""Unit tests for Groq client wrapper and error redaction."""

from unittest.mock import MagicMock
import pytest

from app.groq_client import GroqClient


def test_groq_client_missing_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    import app.config
    app.config._settings = None

    client = GroqClient(api_key=None, client=None)
    with pytest.raises(ValueError, match="GROQ_API_KEY is missing"):
        client.generate_chat_completion("System prompt", "User prompt")


def test_groq_client_successful_generation():
    mock_sdk = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"post_text": "Clean architectural post text without cliches."}'
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_sdk.chat.completions.create.return_value = mock_resp

    client = GroqClient(api_key="mock_key", client=mock_sdk)
    content = client.generate_chat_completion("System", "User")
    assert "Clean architectural post" in content


def test_groq_client_error_redaction():
    secret_key = "gsk_leakablekey1234567890abcdef"
    mock_sdk = MagicMock()
    mock_sdk.chat.completions.create.side_effect = RuntimeError(f"Connection failed for {secret_key}")

    client = GroqClient(api_key=secret_key, client=mock_sdk)
    with pytest.raises(RuntimeError) as exc_info:
        client.generate_chat_completion("System", "User")

    err_str = str(exc_info.value)
    assert secret_key not in err_str
    assert "[REDACTED]" in err_str or "[REDACTED_GROQ_KEY]" in err_str
