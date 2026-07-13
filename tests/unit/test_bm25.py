"""Unit tests for research_agent.bm25."""

from __future__ import annotations

import pytest

from research_agent.bm25 import _tokenize, rank_papers_combined, rank_papers_bm25
from research_agent.models import Paper

pytestmark = pytest.mark.unit


class TestTokenize:
    def test_lowercases_and_strips_stop_words(self):
        tokens = _tokenize("The Transformer is an Architecture for Attention")
        assert "the" not in tokens
        assert "for" not in tokens
        assert "transformer" in tokens
        assert "architecture" in tokens
        assert "attention" in tokens

    def test_drops_short_tokens(self):
        assert _tokenize("AI is OK") == []

    def test_empty(self):
        assert _tokenize("") == []


class TestRankPapers:
    def test_combined_ranks_relevant_first(self, sample_papers: list):
        ranked = rank_papers_combined(sample_papers, "transformer attention")
        assert ranked
        assert ranked[0][0].id == "10.1234/example.1"
        assert all(isinstance(score, float) for _, score in ranked)

    def test_bm25_empty_query_zeros(self, sample_papers: list):
        ranked = rank_papers_bm25(sample_papers, "")
        assert len(ranked) == len(sample_papers)
        assert all(score == 0.0 for _, score in ranked)

    def test_combined_empty_corpus(self):
        assert rank_papers_combined([], "anything") == []
