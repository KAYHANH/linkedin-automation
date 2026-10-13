"""Unit tests for the CLI pipeline, safety guards, and state transitions."""

import datetime
import json
from unittest.mock import MagicMock, patch
import pytest
import pytz

from app.main import run_automation, run_check_config
from app.models import DailyState, DraftStatus, ExecutionMode, LinkedInPostResponse, PublicationStatus


def test_cli_check_config(capsys):
    exit_code = run_check_config()
    captured = capsys.readouterr()
    assert "GROQ-LINKEDIN AUTOMATION CONFIGURATION CHECK" in captured.out
    assert "AUTO_PUBLISH:" in captured.out
    assert "DRY_RUN:" in captured.out


@patch("app.content.ContentGenerator.generate_post")
@patch("app.github_state.GitHubStateManager.save_daily_state")
@patch("app.linkedin_client.LinkedInClient.publish_text_post")
def test_dry_run_makes_no_github_or_linkedin_writes(
    mock_publish,
    mock_save_state,
    mock_gen_post,
    sample_entry,
    sample_pillar
):
    from app.models import GeneratedPost
    mock_gen_post.return_value = GeneratedPost(
        text=(
            "Software engineering discipline starts with testing boundaries.\n\n"
            "Testing early saves hours of debugging later.\n\n"
            "What testing patterns do you rely on most?"
        ),
        hook="Software engineering discipline starts with testing boundaries.",
        closing_question="What testing patterns do you rely on most?",
        hashtags=[],
        formula_used="F10",
        angle_used="A10",
        pillar_id="tech_trends",
        character_count=350,
        content_hash="mock_hash"
    )

    exit_code = run_automation(ExecutionMode.DRY_RUN)
    assert exit_code == 0
    # Dry run must NEVER call GitHub save or LinkedIn publish
    mock_save_state.assert_not_called()
    mock_publish.assert_not_called()


@patch("app.content.ContentGenerator.generate_post")
@patch("app.github_state.GitHubStateManager.load_daily_state")
@patch("app.github_state.GitHubStateManager.save_daily_state")
@patch("app.github_state.GitHubStateManager.save_outbox_markdown")
@patch("app.linkedin_client.LinkedInClient.publish_text_post")
def test_draft_mode_saves_to_github_but_never_calls_linkedin(
    mock_publish,
    mock_save_outbox,
    mock_save_state,
    mock_load_state,
    mock_gen_post
):
    from app.models import GeneratedPost
    mock_load_state.return_value = (None, None)
    mock_gen_post.return_value = GeneratedPost(
        text=(
            "Software engineering discipline starts with testing boundaries.\n\n"
            "Testing early saves hours of debugging later in production.\n\n"
            "What testing patterns do you rely on most?"
        ),
        hook="Software engineering discipline starts with testing boundaries.",
        closing_question="What testing patterns do you rely on most?",
        hashtags=[],
        formula_used="F10",
        angle_used="A10",
        pillar_id="tech_trends",
        character_count=350,
        content_hash="mock_hash"
    )

    exit_code = run_automation(ExecutionMode.DRAFT)
    assert exit_code == 0

    # Draft mode must save to GitHub
    mock_save_state.assert_called_once()
    mock_save_outbox.assert_called_once()
    saved_state = mock_save_state.call_args[0][0]
    assert saved_state.draft_status == DraftStatus.SAVED
    assert saved_state.publication_status == PublicationStatus.NOT_STARTED

    # Draft mode must NEVER call LinkedIn publish endpoint
    mock_publish.assert_not_called()


@patch("app.github_state.GitHubStateManager.load_daily_state")
@patch("app.linkedin_client.LinkedInClient.publish_text_post")
def test_publish_mode_blocked_when_already_published(mock_publish, mock_load_state, monkeypatch):
    monkeypatch.setenv("AUTO_PUBLISH", "true")
    monkeypatch.setenv("DRY_RUN", "false")
    import app.config
    app.config._settings = None

    already_published_state = DailyState(
        date="2026-10-14",
        pillar_id="tech_trends",
        pillar_name="Tech Trends",
        topic="Simplicity",
        hook_formula="F10",
        founder_angle="A10",
        draft_status=DraftStatus.SAVED,
        publication_status=PublicationStatus.PUBLISHED,
        linkedin_post_id="urn:li:share:existing123",
        created_at="2026-10-14T09:00:00",
        updated_at="2026-10-14T09:00:30"
    )
    mock_load_state.return_value = (already_published_state, "sha_existing")

    tz = pytz.timezone("Asia/Kolkata")
    test_dt = tz.localize(datetime.datetime(2026, 10, 14, 9, 0, 0))

    exit_code = run_automation(ExecutionMode.PUBLISH, target_date_override=test_dt)
    assert exit_code == 0  # Gracefully finishes without error, preventing duplicate
    mock_publish.assert_not_called()


@patch("app.github_state.GitHubStateManager.load_daily_state")
@patch("app.linkedin_client.LinkedInClient.publish_text_post")
def test_publish_mode_blocked_when_state_is_claimed_or_unknown(mock_publish, mock_load_state, monkeypatch):
    monkeypatch.setenv("AUTO_PUBLISH", "true")
    monkeypatch.setenv("DRY_RUN", "false")
    import app.config
    app.config._settings = None

    claimed_state = DailyState(
        date="2026-10-14",
        pillar_id="tech_trends",
        pillar_name="Tech Trends",
        topic="Simplicity",
        hook_formula="F10",
        founder_angle="A10",
        draft_status=DraftStatus.SAVED,
        publication_status=PublicationStatus.CLAIMED,
        created_at="2026-10-14T09:00:00",
        updated_at="2026-10-14T09:00:00"
    )
    mock_load_state.return_value = (claimed_state, "sha_claimed")

    tz = pytz.timezone("Asia/Kolkata")
    test_dt = tz.localize(datetime.datetime(2026, 10, 14, 9, 0, 0))

    # Refuses to run if state is claimed
    exit_code = run_automation(ExecutionMode.PUBLISH, target_date_override=test_dt)
    assert exit_code == 1
    mock_publish.assert_not_called()


@patch("app.content.ContentGenerator.generate_post")
@patch("app.github_state.GitHubStateManager.load_daily_state")
@patch("app.github_state.GitHubStateManager.save_daily_state")
@patch("app.linkedin_client.LinkedInClient.publish_text_post")
def test_publish_success_claims_then_records_published(
    mock_publish,
    mock_save_state,
    mock_load_state,
    mock_gen_post,
    monkeypatch
):
    monkeypatch.setenv("AUTO_PUBLISH", "true")
    monkeypatch.setenv("DRY_RUN", "false")
    import app.config
    app.config._settings = None

    from app.models import GeneratedPost
    mock_load_state.return_value = (None, None)
    mock_gen_post.return_value = GeneratedPost(
        text=(
            "Clean code boundaries and tested software save hours of operational overhead.\n\n"
            "Testing early saves days of debugging in production environments.\n\n"
            "What architecture rules do you enforce?"
        ),
        hook="Clean code boundaries and tested software save hours of operational overhead.",
        closing_question="What architecture rules do you enforce?",
        hashtags=[],
        formula_used="F10",
        angle_used="A10",
        pillar_id="tech_trends",
        character_count=350,
        content_hash="mock_hash"
    )

    mock_save_state.side_effect = ["sha_claimed_1", "sha_published_2"]
    mock_publish.return_value = LinkedInPostResponse(
        success=True,
        status_code=201,
        post_id="urn:li:share:success999"
    )

    tz = pytz.timezone("Asia/Kolkata")
    test_dt = tz.localize(datetime.datetime(2026, 10, 14, 9, 0, 0))

    exit_code = run_automation(ExecutionMode.PUBLISH, target_date_override=test_dt)
    assert exit_code == 0

    # Ensure two state saves: 1st claimed, 2nd published
    assert mock_save_state.call_count == 2
    first_save = mock_save_state.call_args_list[0][0][0]
    second_save = mock_save_state.call_args_list[1][0][0]

    assert first_save.publication_status == PublicationStatus.CLAIMED
    assert second_save.publication_status == PublicationStatus.PUBLISHED
    assert second_save.linkedin_post_id == "urn:li:share:success999"


@patch("app.content.ContentGenerator.generate_post")
@patch("app.github_state.GitHubStateManager.load_daily_state")
@patch("app.github_state.GitHubStateManager.save_daily_state")
@patch("app.linkedin_client.LinkedInClient.publish_text_post")
def test_publish_ambiguous_timeout_marks_unknown(
    mock_publish,
    mock_save_state,
    mock_load_state,
    mock_gen_post,
    monkeypatch
):
    monkeypatch.setenv("AUTO_PUBLISH", "true")
    monkeypatch.setenv("DRY_RUN", "false")
    import app.config
    app.config._settings = None

    from app.models import GeneratedPost
    mock_load_state.return_value = (None, None)
    mock_gen_post.return_value = GeneratedPost(
        text=(
            "Clean code boundaries and tested software save hours of operational overhead.\n\n"
            "Testing early saves days of debugging in production environments.\n\n"
            "What architecture rules do you enforce?"
        ),
        hook="Clean code boundaries and tested software save hours of operational overhead.",
        closing_question="What architecture rules do you enforce?",
        hashtags=[],
        formula_used="F10",
        angle_used="A10",
        pillar_id="tech_trends",
        character_count=350,
        content_hash="mock_hash"
    )

    mock_save_state.side_effect = ["sha_claimed_1", "sha_unknown_2"]
    mock_publish.return_value = LinkedInPostResponse(
        success=False,
        status_code=0,
        is_ambiguous_timeout=True,
        error_message="Ambiguous timeout: connection drop"
    )

    tz = pytz.timezone("Asia/Kolkata")
    test_dt = tz.localize(datetime.datetime(2026, 10, 14, 9, 0, 0))

    exit_code = run_automation(ExecutionMode.PUBLISH, target_date_override=test_dt)
    assert exit_code == 1

    # Ensure second save was UNKNOWN
    second_save = mock_save_state.call_args_list[1][0][0]
    assert second_save.publication_status == PublicationStatus.UNKNOWN
