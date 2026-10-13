"""Unit tests for topic rotation, Asia/Kolkata date handling, and pillar distribution."""

from datetime import datetime
import pytz
import pytest

from app.topic_rotation import TopicRotationManager


def test_topic_rotation_loading():
    mgr = TopicRotationManager()
    assert len(mgr.pillars_by_id) == 8
    assert len(mgr.schedule_by_day) == 30


def test_kolkata_timezone_calculation():
    mgr = TopicRotationManager()
    now_kolkata = mgr.get_current_kolkata_date()
    assert now_kolkata.tzinfo is not None
    assert "Kolkata" in str(now_kolkata.tzinfo) or "+05:30" in str(now_kolkata.tzinfo)


def test_continuous_day_of_year_mapping():
    mgr = TopicRotationManager()
    tz = pytz.timezone("Asia/Kolkata")

    # Day 1 of year (Jan 1) -> day 1
    d1 = tz.localize(datetime(2026, 1, 1, 9, 0, 0))
    assert mgr.get_day_index_for_date(d1) == 1

    # Day 30 of year (Jan 30) -> day 30
    d30 = tz.localize(datetime(2026, 1, 30, 9, 0, 0))
    assert mgr.get_day_index_for_date(d30) == 30

    # Day 31 of year (Jan 31) -> day 1
    d31 = tz.localize(datetime(2026, 1, 31, 9, 0, 0))
    assert mgr.get_day_index_for_date(d31) == 1


def test_balanced_30_day_pillar_distribution():
    mgr = TopicRotationManager()
    pillar_counts = {}
    for day in range(1, 31):
        entry = mgr.schedule_by_day[day]
        pillar_counts[entry.pillar_id] = pillar_counts.get(entry.pillar_id, 0) + 1

    # All 8 pillars must be present
    assert len(pillar_counts) == 8

    # KodeToCareer and Viato should be present but balanced (around 10% each: 3 days)
    assert pillar_counts.get("kodetocareer_education") == 3
    assert pillar_counts.get("viato_travel_tech") == 3

    # No pillar exceeds 5 days (overuse check)
    for p_id, count in pillar_counts.items():
        assert count <= 5, f"Pillar {p_id} appears {count} times, exceeding balance threshold"


def test_fact_extraction_isolation():
    mgr = TopicRotationManager()

    # 1. KodeToCareer pillar extracts company facts for KodeToCareer
    facts_ktc = mgr._extract_relevant_facts("kodetocareer_education")
    assert facts_ktc["company"] is not None
    assert facts_ktc["company"]["name"] == "KodeToCareer"
    assert len(facts_ktc["allowed_talking_points"]) > 0

    # 2. Viato pillar extracts company facts for Viato
    facts_viato = mgr._extract_relevant_facts("viato_travel_tech")
    assert facts_viato["company"] is not None
    assert facts_viato["company"]["name"] == "Viato"

    # 3. Generic tech pillar does NOT inject company promo
    facts_tech = mgr._extract_relevant_facts("tech_trends")
    assert facts_tech["company"] is None
