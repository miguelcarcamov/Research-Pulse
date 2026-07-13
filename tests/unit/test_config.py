"""Unit tests for research_agent.config (real YAML from repo)."""

from __future__ import annotations

import pytest

from research_agent.config import load_settings, load_topics, topics_by_id

pytestmark = pytest.mark.unit


class TestConfig:
    def test_load_topics(self):
        topics, feeds = load_topics()
        assert len(topics) >= 5
        ids = {t.id for t in topics}
        assert "ai-ml" in ids
        assert "nlp" in ids
        assert all(t.keywords for t in topics if t.id == "ai-ml")
        assert isinstance(feeds, list)

    def test_load_settings(self):
        settings = load_settings()
        assert settings.papers_per_topic == 5
        assert settings.lookback_days == 2
        assert settings.newsletter_name == "ResearchPulse"
        assert settings.arxiv_request_delay >= 3

    def test_topics_by_id(self):
        topics, _ = load_topics()
        by_id = topics_by_id(topics)
        assert by_id["nlp"].label
        assert "nlp" in by_id
