"""Unit tests for research_agent.recommend."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_agent.memory import ResearchMemory
from research_agent.models import Paper
from research_agent.recommend import format_recommendations, get_recommendations

pytestmark = pytest.mark.unit


@pytest.fixture
def memory_with_interests(tmp_path: Path) -> ResearchMemory:
    mem = ResearchMemory(path=tmp_path / "memory.json")
    mem.interests["keywords"] = ["transformer", "attention"]
    mem.interests["topics"] = ["ai-ml"]
    mem.interests["questions"] = ["How does attention improve transformers efficiency?"]
    mem.save()
    return mem


class TestGetRecommendations:
    def test_memory_based_scoring(self, sample_papers: list, memory_with_interests: ResearchMemory):
        recs = get_recommendations(sample_papers, memory_with_interests, limit=5, min_score=0.05)
        assert recs
        assert recs[0].paper.id == "10.1234/example.1"
        assert recs[0].score >= recs[-1].score
        assert isinstance(recs[0].reasons, list)

    def test_skips_already_seen(self, sample_paper: Paper, sample_papers: list, memory_with_interests: ResearchMemory):
        memory_with_interests.record_paper(
            paper_id=sample_paper.id,
            title=sample_paper.title,
            url=sample_paper.url,
            source=sample_paper.source,
        )
        recs = get_recommendations(sample_papers, memory_with_interests, min_score=0.0)
        assert all(r.paper.id != sample_paper.id for r in recs)


class TestFormatRecommendations:
    def test_empty(self):
        text = format_recommendations([])
        assert "No personalized recommendations" in text

    def test_with_recs(self, sample_papers: list, memory_with_interests: ResearchMemory):
        recs = get_recommendations(sample_papers, memory_with_interests, limit=2, min_score=0.01)
        text = format_recommendations(recs)
        assert "PERSONALIZED RECOMMENDATIONS" in text
        if recs:
            assert recs[0].paper.title in text
