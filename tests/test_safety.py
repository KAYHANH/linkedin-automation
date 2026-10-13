"""Unit tests for safety audits, AI tell detection, and humanizer scrubbing."""

import pytest
from app.safety import audit_post, check_vocabulary_density, scrub_em_dashes, scrub_formatting


def test_valid_post_passes():
    post_text = (
        "Architectural simplicity is the most underrated competitive advantage in early-stage engineering.\n\n"
        "Over the last four years, I watched dozens of engineering teams adopt distributed microservices "
        "before they even understood their query access patterns. Within six months, developers were spending "
        "more hours debugging distributed transactions than shipping actual features.\n\n"
        "When you keep your core system as a well-modularized monolith with strict boundaries, database joins "
        "remain cheap and end-to-end integration tests run in seconds on your local machine.\n\n"
        "Boring technology lets you focus on domain problems instead of network infrastructure.\n\n"
        "How do you evaluate when a boundary genuinely justifies its own network service?\n\n"
        "#softwareengineering #architecture"
    )

    result = audit_post(post_text)
    assert result.passed is True
    assert len(result.blockers) == 0
    assert result.character_count > 300


def test_hook_question_opener_blocked():
    post_text = (
        "Have you ever wondered why distributed systems fail so frequently in production?\n\n"
        "Engineering teams often adopt complex architectures too early. This adds operational overhead "
        "and complicates testing without delivering measurable velocity improvements."
    )
    result = audit_post(post_text)
    assert result.passed is False
    assert any(b.rule == "hook_question_opener" for b in result.blockers)


def test_forensic_leakage_blocked():
    post_text = (
        "Here is our technical analysis for the quarter.\n\n"
        "According to oaicite:123 the performance improved significantly across instances. "
        "Please fill in [Your Company] before publishing this."
    )
    result = audit_post(post_text)
    assert result.passed is False
    assert any("oaicite" in b.message for b in result.blockers)
    assert any("placeholder" in b.message.lower() for b in result.blockers)


def test_reveal_bridge_blocked():
    post_text = (
        "We spent three weeks optimizing database indexes on PostgreSQL.\n\n"
        "The result? Query latency dropped by 40% across all heavy reporting tables.\n\n"
        "This proves that index hygiene is essential."
    )
    result = audit_post(post_text)
    assert result.passed is False
    assert any(b.rule == "reveal_bridge" for b in result.blockers)


def test_sincerity_announcement_blocked():
    post_text = (
        "Let me be honest, building production systems is much harder than following tutorials.\n\n"
        "Most tutorials skip error boundaries and database migration strategies completely."
    )
    result = audit_post(post_text)
    assert result.passed is False
    assert any(b.rule == "sincerity_announcement" for b in result.blockers)


def test_external_link_blocked():
    post_text = (
        "We released our comprehensive guide on test-driven development.\n\n"
        "You can read the entire article directly at https://example.com/guide to see all examples."
    )
    result = audit_post(post_text)
    assert result.passed is False
    assert any(b.rule == "external_link_in_body" for b in result.blockers)


def test_excess_em_dash_scrubbing():
    # 50 words with 4 em dashes -> cap is 1 em dash -> excess are converted to commas
    sample = "One idea — another clause — third clause — fourth clause — final thought and reflection."
    scrubbed = scrub_em_dashes(sample)
    assert scrubbed.count("—") <= 1
    assert "," in scrubbed


def test_ai_vocab_density_detection():
    clean_p = "We built a simple cache in Redis to keep response times under 50 milliseconds."
    assert len(check_vocabulary_density(clean_p)) == 0

    slop_p = "We must delve into this multifaceted realm to foster synergy and leverage our holistic landscape."
    hits = check_vocabulary_density(slop_p)
    assert len(hits) >= 3

    post_with_slop = (
        "A clear technical observation about software architectures.\n\n"
        + slop_p + "\n\n"
        "What patterns do you prefer for modular software?"
    )
    result = audit_post(post_with_slop)
    assert result.passed is False
    assert any(b.rule == "ai_vocab_density" for b in result.blockers)
