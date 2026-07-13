"""Integration: ResearchMemory interests → personalized recommendations."""

from __future__ import annotations

import pytest

from research_agent.memory import ResearchMemory
from research_agent.recommend import get_recommendations


@pytest.mark.integration
def test_memory_recommend_ranks_by_interests(tmp_data_dir, sample_papers):
    memory = ResearchMemory(path=tmp_data_dir / "memory.json")
    memory.add_interest("keyword", "transformer")
    memory.add_interest("keyword", "attention")
    memory.add_interest("topic", "ai-ml")
    memory.add_interest("question", "How do transformers scale for scientific discovery?")

    recs = get_recommendations(sample_papers, memory, limit=10, min_score=0.05)

    assert recs
    # Transformer / attention paper should outrank soil moisture.
    assert recs[0].paper.id == sample_papers[0].id
    titles = [r.paper.title for r in recs]
    assert "Soil Moisture in Arid Climate Zones" not in titles[:1]
    assert recs[0].score >= recs[-1].score
