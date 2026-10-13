"""Unit tests for GitHub state manager using respx mocked HTTP calls."""

import base64
import json
import pytest
import respx
import httpx

from app.github_state import GitHubStateConflictError, GitHubStateError, GitHubStateManager
from app.models import DailyState, DraftStatus, PublicationStatus


@respx.mock
def test_read_file_not_found():
    respx.get("https://api.github.com/repos/testuser/testrepo/contents/automation_state/2026-10-14.json").respond(status_code=404)

    mgr = GitHubStateManager()
    content, sha = mgr.read_file("automation_state/2026-10-14.json")
    assert content is None
    assert sha is None


@respx.mock
def test_read_file_success():
    expected_content = '{"date": "2026-10-14", "publication_status": "not_started"}'
    b64_content = base64.b64encode(expected_content.encode("utf-8")).decode("utf-8")

    respx.get("https://api.github.com/repos/testuser/testrepo/contents/automation_state/2026-10-14.json").respond(
        status_code=200,
        json={
            "sha": "blob_sha_123",
            "content": b64_content,
            "encoding": "base64"
        }
    )

    mgr = GitHubStateManager()
    content, sha = mgr.read_file("automation_state/2026-10-14.json")
    assert content == expected_content
    assert sha == "blob_sha_123"


@respx.mock
def test_write_file_optimistic_concurrency_conflict():
    # 409 conflict
    respx.put("https://api.github.com/repos/testuser/testrepo/contents/automation_state/2026-10-14.json").respond(
        status_code=409,
        text="Conflict: sha does not match"
    )

    mgr = GitHubStateManager()
    with pytest.raises(GitHubStateConflictError, match="Optimistic concurrency conflict"):
        mgr.write_file("automation_state/2026-10-14.json", "some content", "commit msg", sha="old_sha")


@respx.mock
def test_write_file_redacts_secrets_in_content():
    captured_payload = {}

    def capture_request(request):
        nonlocal captured_payload
        captured_payload = json.loads(request.content.decode("utf-8"))
        return httpx.Response(201, json={"content": {"sha": "new_sha_456"}})

    respx.put("https://api.github.com/repos/testuser/testrepo/contents/automation_state/2026-10-14.json").mock(
        side_effect=capture_request
    )

    secret_key = "gsk_testmockkey1234567890abcdef"
    state_with_secret = f'{{"secret": "{secret_key}"}}'

    mgr = GitHubStateManager()
    mgr.write_file("automation_state/2026-10-14.json", state_with_secret, f"Commit with {secret_key}")

    # Inspect decoded content that was sent in request
    sent_b64 = captured_payload.get("content", "")
    decoded_sent = base64.b64decode(sent_b64).decode("utf-8")

    assert secret_key not in decoded_sent
    assert "[REDACTED]" in decoded_sent
    assert secret_key not in captured_payload.get("message", "")
