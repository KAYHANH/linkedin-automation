"""Unit tests for official LinkedIn API client, error responses, and timeout safety."""

import pytest
import respx
import httpx

from app.linkedin_client import LinkedInClient


@respx.mock
def test_linkedin_posts_api_success():
    respx.post("https://api.linkedin.com/rest/posts").respond(
        status_code=201,
        headers={"x-restli-id": "urn:li:share:7123456789012345678"}
    )

    client = LinkedInClient(
        access_token="valid_token",
        author_urn="urn:li:person:12345",
        api_version="202501",
        endpoint_style="rest/posts"
    )

    resp = client.publish_text_post("Thoughtful post content here.")
    assert resp.success is True
    assert resp.status_code == 201
    assert resp.post_id == "urn:li:share:7123456789012345678"
    assert resp.is_ambiguous_timeout is False


@respx.mock
def test_linkedin_ugc_posts_api_success():
    respx.post("https://api.linkedin.com/v2/ugcPosts").respond(
        status_code=201,
        json={"id": "urn:li:ugcPost:987654321"}
    )

    client = LinkedInClient(
        access_token="valid_token",
        author_urn="urn:li:person:12345",
        endpoint_style="v2/ugcposts"
    )

    resp = client.publish_text_post("Thoughtful post content for UGC endpoint.")
    assert resp.success is True
    assert resp.status_code == 201
    assert resp.post_id == "urn:li:ugcPost:987654321"


@respx.mock
def test_linkedin_401_unauthorized():
    respx.post("https://api.linkedin.com/rest/posts").respond(
        status_code=401,
        json={"message": "Expired access token"}
    )

    client = LinkedInClient(
        access_token="expired_token",
        author_urn="urn:li:person:12345"
    )

    resp = client.publish_text_post("Test content")
    assert resp.success is False
    assert resp.status_code == 401
    assert "Unauthorized" in resp.error_message


@respx.mock
def test_linkedin_403_forbidden_missing_scope():
    respx.post("https://api.linkedin.com/rest/posts").respond(
        status_code=403,
        json={"message": "Not enough permissions to access: POST-posts"}
    )

    client = LinkedInClient(
        access_token="restricted_token",
        author_urn="urn:li:person:12345"
    )

    resp = client.publish_text_post("Test content")
    assert resp.success is False
    assert resp.status_code == 403
    assert "w_member_social" in resp.error_message or "Forbidden" in resp.error_message


@respx.mock
def test_linkedin_ambiguous_timeout_no_retry():
    # Simulate a network timeout during the write request
    respx.post("https://api.linkedin.com/rest/posts").mock(
        side_effect=httpx.TimeoutException("Connection timed out after 25s")
    )

    client = LinkedInClient(
        access_token="valid_token",
        author_urn="urn:li:person:12345"
    )

    resp = client.publish_text_post("Test content")

    # Critical requirement: ambiguous timeout is flagged, no automatic retry attempted
    assert resp.success is False
    assert resp.is_ambiguous_timeout is True
    assert "Ambiguous timeout" in resp.error_message
    assert "manual reconciliation" in resp.error_message.lower()
