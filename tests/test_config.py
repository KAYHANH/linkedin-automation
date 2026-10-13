"""Unit tests for configuration management, timezone handling, and secret redaction."""

import pytest
from app.config import Settings, get_settings


def test_safe_defaults():
    settings = Settings(
        GROQ_API_KEY="test_key",
        GITHUB_TOKEN="test_gh",
        GITHUB_REPOSITORY="owner/repo"
    )
    assert settings.auto_publish is False
    assert settings.dry_run is True
    assert settings.publish_timezone == "Asia/Kolkata"
    assert settings.github_state_branch == "automation-state"


def test_timezone_validation():
    # Valid timezone
    s = Settings(PUBLISH_TIMEZONE="Asia/Kolkata")
    assert s.publish_timezone == "Asia/Kolkata"

    # Invalid timezone raises ValueError
    with pytest.raises(ValueError, match="Unknown timezone"):
        Settings(PUBLISH_TIMEZONE="Invalid/Fake_Zone")


def test_secret_redaction():
    secret_groq = "gsk_supersecret1234567890abcdef"
    secret_gh = "ghp_supergithubtoken1234567890"
    secret_li = "AQX_supersecretlinkedintoken_here"

    settings = Settings(
        GROQ_API_KEY=secret_groq,
        GITHUB_TOKEN=secret_gh,
        LINKEDIN_ACCESS_TOKEN=secret_li,
        GITHUB_REPOSITORY="owner/repo"
    )

    sample_log = f"Connecting to Groq with key {secret_groq} and GitHub {secret_gh} for LinkedIn {secret_li}."
    redacted = settings.redact(sample_log)

    assert secret_groq not in redacted
    assert secret_gh not in redacted
    assert secret_li not in redacted
    assert "[REDACTED]" in redacted


def test_generic_pattern_redaction():
    settings = Settings()
    text = "Failed call with header Authorization: Bearer secret_bearer_token_123456789"
    redacted = settings.redact(text)
    assert "secret_bearer_token_123456789" not in redacted
    assert "Bearer [REDACTED_TOKEN]" in redacted


def test_mode_validation_readiness():
    settings = Settings(
        GROQ_API_KEY="gsk_validkey1234567890",
        GITHUB_TOKEN="ghp_validtoken1234567890",
        GITHUB_REPOSITORY="user/repo",
        LINKEDIN_ACCESS_TOKEN=None,
        LINKEDIN_AUTHOR_URN=None,
        AUTO_PUBLISH=False,
        DRY_RUN=True
    )

    # Dry-run is ready
    dry_rep = settings.validate_for_mode("dry-run")
    assert len(dry_rep["missing"]) == 0

    # Draft is ready
    draft_rep = settings.validate_for_mode("draft")
    assert len(draft_rep["missing"]) == 0

    # Publish is blocked because AUTO_PUBLISH=False and DRY_RUN=True and no LinkedIn token
    pub_rep = settings.validate_for_mode("publish")
    assert len(pub_rep["missing"]) > 0
    assert any("AUTO_PUBLISH" in m for m in pub_rep["missing"])
    assert any("DRY_RUN" in m for m in pub_rep["missing"])
    assert any("LINKEDIN_ACCESS_TOKEN" in m for m in pub_rep["missing"])
