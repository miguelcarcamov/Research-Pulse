"""Unit tests for research_agent.local_config."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_agent import local_config as lc

pytestmark = pytest.mark.unit


class TestLocalConfig:
    def test_save_and_get_topics(self, tmp_data_dir: Path):
        assert lc.get_topics() == []
        ok = lc.save(["ai-ml", "nlp"], source="manual")
        assert ok is True
        assert lc.get_topics() == ["ai-ml", "nlp"]
        assert (tmp_data_dir / "local.json").is_file()

    def test_save_rejects_all_invalid(self, tmp_data_dir: Path):
        assert lc.save(["not-a-real-topic-id"], source="manual") is False

    def test_set_papers_per_topic(self, tmp_data_dir: Path):
        lc.set_papers_per_topic(7)
        assert lc.get_papers_per_topic() == 7
        assert lc.effective_papers_per_topic() == 7

    def test_set_papers_per_topic_bounds(self, tmp_data_dir: Path):
        with pytest.raises(ValueError):
            lc.set_papers_per_topic(0)
        with pytest.raises(ValueError):
            lc.set_papers_per_topic(100)
