"""Unit tests for research engine and Groq browser search integration."""

from unittest.mock import MagicMock
import pytest

from app.config import Settings
from app.models import ResearchResult
from app.research import ResearchEngine


def test_research_disabled_web_search(monkeypatch):
    monkeypatch.setenv("ENABLE_WEB_SEARCH", "false")
    import app.config
    app.config._settings = None

    engine = ResearchEngine()
    result = engine.conduct_research("tech_trends", "Microservice architectural trade-offs")

    assert result.is_live_search is False
    assert "Web search disabled" in result.fallback_reason
    assert len(result.sources) > 0
    assert result.sources[0].url is None


def test_research_groq_exception_falls_back_gracefully():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("Model does not support browser_search tool")

    engine = ResearchEngine(groq_client=mock_client)
    result = engine.conduct_research("ai_agents_automation", "Production LLM circuit breakers")

    assert result.is_live_search is False
    assert "Groq search error" in result.fallback_reason
    assert len(result.sources) > 0


def test_research_successful_groq_tool_search():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = (
        "According to recent release notes from https://docs.python.org/3/whatsnew/3.12.html, "
        "Python 3.12 delivers significant performance improvements with isolated subinterpreters and cleaner tracebacks."
    )
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    engine = ResearchEngine(groq_client=mock_client)
    result = engine.conduct_research("tech_trends", "Python 3.12 performance enhancements")

    assert result.is_live_search is True
    assert "subinterpreters" in result.summary
    assert len(result.sources) > 0
    assert any("https://docs.python.org/3/whatsnew/3.12.html" in s.url for s in result.sources)
