"""Unit tests for content generation and outbox formatting."""

import json
from unittest.mock import MagicMock
import pytest

from app.content import ContentGenerator
from app.models import CalendarEntry, ContentPillar, ResearchResult, ResearchSource


def test_content_generator_success(sample_entry, sample_pillar, sample_research):
    mock_groq = MagicMock()
    valid_json = {
        "hook": "Architectural simplicity is the highest leverage engineering discipline.",
        "post_text": (
            "Architectural simplicity is the highest leverage engineering discipline.\n\n"
            "When teams build distributed services before validating user demand, testing complexity "
            "explodes. Local development requires orchestrating half a dozen Docker containers and mocks.\n\n"
            "Keeping system boundaries clean inside a well-structured monolith allows you to refactor "
            "with compiler guarantees instead of tracking broken HTTP contracts.\n\n"
            "How do your teams manage early architecture trade-offs?\n\n"
            "#softwareengineering #architecture"
        ),
        "closing_question": "How do your teams manage early architecture trade-offs?",
        "hashtags": ["#softwareengineering", "#architecture"]
    }
    mock_groq.generate_chat_completion.return_value = json.dumps(valid_json)

    gen = ContentGenerator(groq_client=mock_groq)
    post = gen.generate_post(
        entry=sample_entry,
        pillar=sample_pillar,
        facts={"company": None, "allowed_talking_points": ["Simplicity"], "strictly_forbidden": []},
        research=sample_research,
        brand_profile_md="Brand profile content"
    )

    assert post.character_count > 300
    assert post.formula_used == "F10"
    assert len(post.content_hash) == 64  # SHA-256


def test_content_generator_repairs_bad_hook(sample_entry, sample_pillar, sample_research):
    mock_groq = MagicMock()
    # First response opens with a bad question
    bad_json = {
        "hook": "Have you ever wondered why distributed systems fail?",
        "post_text": (
            "Have you ever wondered why distributed systems fail?\n\n"
            "When teams build distributed services too early, testing complexity explodes. "
            "Local development requires orchestrating dozens of containers.\n\n"
            "Keeping boundaries clean inside a modular monolith allows you to refactor cleanly.\n\n"
            "How do you manage architecture trade-offs?"
        ),
        "closing_question": "How do you manage architecture trade-offs?",
        "hashtags": []
    }
    # Second response repairs it into a bold statement
    repaired_json = {
        "post_text": (
            "Premature distributed architectures fail because network boundaries multiply failure modes.\n\n"
            "When teams build microservices before understanding query patterns, local development "
            "slows down dramatically.\n\n"
            "Keeping system boundaries clean inside a modular monolith allows you to refactor with compiler safety.\n\n"
            "How do your teams manage early architecture trade-offs?\n\n"
            "#softwareengineering"
        )
    }

    mock_groq.generate_chat_completion.side_effect = [
        json.dumps(bad_json),
        json.dumps(repaired_json)
    ]

    gen = ContentGenerator(groq_client=mock_groq)
    post = gen.generate_post(
        entry=sample_entry,
        pillar=sample_pillar,
        facts={"company": None, "allowed_talking_points": [], "strictly_forbidden": []},
        research=sample_research,
        brand_profile_md="Brand profile content"
    )

    # Must have called generate twice (1 generation + 1 repair)
    assert mock_groq.generate_chat_completion.call_count == 2
    assert not post.text.startswith("Have you ever wondered")
    assert post.text.startswith("Premature distributed architectures fail")


def test_outbox_markdown_formatting(sample_entry, sample_pillar, sample_research):
    gen = ContentGenerator()
    from app.models import GeneratedPost
    from app.safety import audit_post

    sample_text = (
        "Simplicity in system design is the best productivity tool.\n\n"
        "Testing modular code locally takes seconds and prevents regression bugs.\n\n"
        "What is your philosophy on software boundaries?"
    )
    post = GeneratedPost(
        text=sample_text,
        hook="Simplicity in system design is the best productivity tool.",
        closing_question="What is your philosophy on software boundaries?",
        hashtags=[],
        formula_used="F10",
        angle_used="A10",
        pillar_id=sample_pillar.id,
        character_count=len(sample_text),
        content_hash="mock_hash_123"
    )
    audit = audit_post(sample_text)

    md = gen.format_outbox_markdown(
        date_str="2026-10-14",
        entry=sample_entry,
        pillar=sample_pillar,
        post=post,
        research=sample_research,
        audit=audit
    )

    assert "# Daily LinkedIn Draft: 2026-10-14" in md
    assert "F10" in md
    assert "mock_hash_123" in md
    assert sample_text in md
