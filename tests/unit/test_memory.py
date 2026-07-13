"""Unit tests for research_agent.memory."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_agent.memory import ResearchMemory

pytestmark = pytest.mark.unit


class TestResearchMemory:
    def test_record_rate_save_load(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        mem = ResearchMemory(path=path)
        mem.record_paper(
            paper_id="p1",
            title="A Paper",
            url="https://example.com/p1",
            source="OpenAlex",
            rating=5,
            notes="great",
            tags=["nlp"],
        )
        assert path.is_file()
        pm = mem.get_paper("p1")
        assert pm is not None
        assert pm.rating == 5
        assert pm.notes == "great"
        assert "nlp" in pm.tags

        # Update rating (record again acts as rate)
        mem.record_paper(
            paper_id="p1",
            title="A Paper",
            url="https://example.com/p1",
            source="OpenAlex",
            rating=4,
        )
        assert mem.get_paper("p1").rating == 4

        reloaded = ResearchMemory(path=path)
        assert reloaded.get_paper("p1").rating == 4
        assert reloaded.get_highly_rated(min_rating=4)
        assert not reloaded.get_unrated_papers()

    def test_load_missing_file(self, tmp_path: Path):
        mem = ResearchMemory(path=tmp_path / "missing.json")
        assert mem.papers == {}
