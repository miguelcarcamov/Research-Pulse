"""Unit tests for research_agent.rank."""

from __future__ import annotations

import pytest

from research_agent.config import Topic
from research_agent.models import Paper
from research_agent.rank import rank_for_topic, score_paper

pytestmark = pytest.mark.unit


@pytest.fixture
def fake_topic() -> Topic:
    return Topic(
        id="transformers",
        label="Transformers",
        keywords=["transformer", "attention"],
        arxiv=["cs.LG"],
        biorxiv=[],
        openalex="transformer attention",
    )


class TestScorePaper:
    def test_relevant_paper_scores_higher(self, sample_paper: Paper, sample_papers: list, fake_topic: Topic):
        relevant = score_paper(sample_paper, fake_topic)
        unrelated = score_paper(sample_papers[2], fake_topic)
        assert relevant > unrelated
        assert relevant > 0


class TestRankForTopic:
    def test_ranks_and_limits(self, sample_papers: list, fake_topic: Topic):
        ranked = rank_for_topic(sample_papers, fake_topic, limit=1)
        assert len(ranked) == 1
        assert ranked[0].id == "10.1234/example.1"
        assert ranked[0].score > 0

    def test_curated_source_kept_without_keywords(self, fake_topic: Topic):
        paper = Paper(
            id="a1",
            title="Unrelated soil paper",
            abstract="Hydrology only",
            authors=[],
            url="",
            source="arXiv",
        )
        ranked = rank_for_topic([paper], fake_topic, limit=5)
        assert len(ranked) == 1
