"""Test configuration, fixtures, and mock factories."""

import os
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from app.config import Settings, get_settings
from app.models import CalendarEntry, ContentPillar, ResearchResult, ResearchSource

TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"


@pytest.fixture(autouse=True)
def reset_settings(monkeypatch):
    """Ensure tests run with safe isolated default environment."""
    monkeypatch.setenv("AUTO_PUBLISH", "false")
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("PUBLISH_TIMEZONE", "Asia/Kolkata")
    monkeypatch.setenv("GITHUB_STATE_BRANCH", "automation-state")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_testmockkey1234567890abcdef")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_testmockgithubtoken1234567890")
    monkeypatch.setenv("GITHUB_REPOSITORY", "testuser/testrepo")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "AQXtestlinkedinaccesstoken123456789")
    monkeypatch.setenv("LINKEDIN_AUTHOR_URN", "urn:li:person:mock12345")
    monkeypatch.setenv("LINKEDIN_API_VERSION", "202501")

    # Force re-instantiation of settings
    import app.config
    app.config._settings = None
    yield
    app.config._settings = None


@pytest.fixture
def sample_pillar() -> ContentPillar:
    return ContentPillar(
        id="tech_trends",
        name="Technology Industry & Software Trends",
        category="Authority",
        description="Architectural shifts and software engineering principles.",
        preferred_formulas=["F10", "F7"],
        preferred_angles=["A1", "A10"],
        primary_goal="saves",
        sample_topics=["Why architectural simplicity beats microservice sprawl"]
    )


@pytest.fixture
def sample_entry() -> CalendarEntry:
    return CalendarEntry(
        day=1,
        pillar_id="tech_trends",
        hook_formula="F10",
        founder_angle="A10",
        goal="saves",
        topic="Why architectural simplicity beats microservice sprawl in mid-stage teams."
    )


@pytest.fixture
def sample_research() -> ResearchResult:
    return ResearchResult(
        is_live_search=False,
        query="Why architectural simplicity beats microservice sprawl",
        summary="Industry case studies demonstrate that premature distributed architectures multiply cognitive and operational overhead.",
        sources=[
            ResearchSource(
                title="Monolith vs Microservices Trade-offs",
                url="https://martinfowler.com/articles/break-monolith.html",
                publisher="Martin Fowler",
                claim="Premature service boundaries increase network failure modes."
            )
        ]
    )
