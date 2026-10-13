"""Unit tests for FastAPI REST API endpoints and authentication."""

import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.auth import create_session_token, hash_password
from app.config import Settings, get_settings
from app.models import DailyState, DraftStatus, PublicationStatus


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_session_token("founder")
    return {"Authorization": f"Bearer {token}"}


def test_healthz_unauthenticated(client):
    """Healthz endpoint is accessible without authentication and exposes no secrets."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "FounderOS LinkedIn Studio"
    assert "GROQ_API_KEY" not in str(data)
    assert "LINKEDIN_ACCESS_TOKEN" not in str(data)


def test_session_unauthenticated(client):
    """Session endpoint returns authenticated: false when unauthenticated."""
    resp = client.get("/api/v1/auth/session")
    assert resp.status_code == 200
    assert resp.json()["authenticated"] is False


def test_login_invalid_credentials(client):
    """Login with invalid credentials returns 401 Unauthorized."""
    resp = client.post("/api/v1/auth/login", json={"username": "founder", "password": "wrongpassword"})
    assert resp.status_code == 401
    assert "Invalid username or password" in resp.json()["detail"]


def test_login_valid_credentials(client):
    """Login with valid dev credentials returns 200 and session token."""
    resp = client.post("/api/v1/auth/login", json={"username": "founder", "password": "founder123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["username"] == "founder"
    assert "founderos_session" in resp.cookies or "token" in data


def test_protected_endpoints_require_auth(client):
    """Protected endpoints reject requests missing credentials with 401."""
    endpoints = [
        "/api/v1/dashboard/summary",
        "/api/v1/dashboard/health",
        "/api/v1/posts",
        "/api/v1/calendar",
        "/api/v1/strategy",
        "/api/v1/history",
        "/api/v1/runs",
        "/api/v1/settings",
    ]
    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 401, f"Endpoint {ep} did not require authentication"


def test_dashboard_summary_authenticated(client, auth_headers):
    """Authenticated dashboard summary returns operational structure."""
    with patch("app.github_state.GitHubStateManager.load_daily_state", return_value=(None, None)), \
         patch("app.github_state.GitHubStateManager.list_directory", return_value=[]):
        resp = client.get("/api/v1/dashboard/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "today_date" in data
        assert "next_daily_run" in data
        assert "connections" in data
        assert len(data["next_7_topics"]) == 7


def test_settings_authenticated_exposes_no_secrets(client, auth_headers):
    """Settings endpoint returns non-secret configurations and no plaintext tokens."""
    resp = client.get("/api/v1/settings", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "groq_api_key" not in data
    assert "linkedin_access_token" not in data
    assert "github_token" not in data
    assert "dashboard_password_hash" not in data
    assert "publish_timezone" in data


def test_publishing_mode_requires_confirmation_phrase(client, auth_headers):
    """Enabling auto-publish requires exact confirmation phrase 'ENABLE AUTO-PUBLISH'."""
    # Attempt without confirmation phrase
    bad_resp = client.post(
        "/api/v1/settings/publishing-mode",
        headers=auth_headers,
        json={"mode": "auto_publish", "confirmation_phrase": "yes please"}
    )
    assert bad_resp.status_code == 400
    assert "ENABLE AUTO-PUBLISH" in bad_resp.json()["detail"]

    # Attempt with exact confirmation phrase
    good_resp = client.post(
        "/api/v1/settings/publishing-mode",
        headers=auth_headers,
        json={"mode": "auto_publish", "confirmation_phrase": "ENABLE AUTO-PUBLISH"}
    )
    assert good_resp.status_code == 200
    assert good_resp.json()["success"] is True


def test_pause_publishing_authenticated(client, auth_headers):
    """Emergency pause endpoint returns paused status."""
    resp = client.post("/api/v1/settings/pause-publishing", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


def test_post_audit_endpoint(client, auth_headers):
    """POST /posts/{id}/audit runs humanizer safety audit."""
    text = (
        "We spent six months refactoring the core distributed pipeline across our microservices.\n\n"
        "Here's the kicker: the real bottleneck was never the database or network serialization latency.\n\n"
        "It was unindexed query plans silently degrading database locks under concurrent write loads.\n\n"
        "What patterns do you enforce in your team before shipping database migrations?"
    )
    resp = client.post(
        "/api/v1/posts/2026-10-13/audit",
        headers=auth_headers,
        json={"text": text}
    )
    assert resp.status_code == 200
    audit_data = resp.json()
    assert "passed" in audit_data
    rules = [b["rule"] for b in audit_data["blockers"]]
    assert "reveal_bridge" in rules


def test_login_plain_text_dashboard_password(client, monkeypatch):
    """When DASHBOARD_PASSWORD is set in environment, login succeeds with it."""
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "dashboard_password", "render_super_secret_123")
    monkeypatch.setattr(settings, "dashboard_username", "founder")

    # Correct password succeeds
    resp = client.post("/api/v1/auth/login", json={"username": "founder", "password": "render_super_secret_123"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Wrong password fails
    resp = client.post("/api/v1/auth/login", json={"username": "founder", "password": "wrong_password"})
    assert resp.status_code == 401


def test_api_aliases_matching_section_5(client, auth_headers):
    """Verify /api/* route aliases function identically to /api/v1/*."""
    # /api/health
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    with patch("app.github_state.GitHubStateManager.list_directory", return_value=[]), \
         patch("app.github_state.GitHubStateManager.load_daily_state", return_value=(None, None)):
        # /api/dashboard/summary
        resp = client.get("/api/dashboard/summary", headers=auth_headers)
        assert resp.status_code == 200

        # /api/calendar
        resp = client.get("/api/calendar?start=2026-10-10&end=2026-10-15", headers=auth_headers)
        assert resp.status_code == 200
        assert "calendar" in resp.json()

        # /api/drafts
        resp = client.get("/api/drafts", headers=auth_headers)
        assert resp.status_code == 200
        assert "posts" in resp.json()

        # /api/history
        resp = client.get("/api/history", headers=auth_headers)
        assert resp.status_code == 200
        assert "history" in resp.json()

        # /api/runs/latest
        resp = client.get("/api/runs/latest", headers=auth_headers)
        assert resp.status_code == 200
        assert "latest_run" in resp.json()

        # /api/settings/status
        resp = client.get("/api/settings/status", headers=auth_headers)
        assert resp.status_code == 200
        assert "groq" in resp.json()

        # /api/settings/check-config
        resp = client.post("/api/settings/check-config", headers=auth_headers)
        assert resp.status_code == 200
        assert "all_valid" in resp.json()


def test_publish_blocked_when_dry_run_or_auto_publish_false(client, auth_headers):
    """Publishing via API is blocked when DRY_RUN=true or AUTO_PUBLISH=false."""
    resp = client.post("/api/drafts/2026-10-13/publish", headers=auth_headers)
    assert resp.status_code == 400
    assert "Publishing is blocked" in resp.json()["detail"]
