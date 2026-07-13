"""Unit tests for research_agent.compare."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from research_agent.compare import compare_papers, compare_papers_structured
from research_agent.models import Paper

pytestmark = pytest.mark.unit


class TestComparePapers:
    def test_structured_fallback_when_no_llm(self, sample_papers: list):
        with patch("research_agent.compare.is_llm_available", return_value=False):
            text = compare_papers(sample_papers[:2], use_llm=True)
        assert "PAPER COMPARISON" in text
        assert sample_papers[0].title in text
        assert "Note: For detailed LLM analysis" in text

    def test_need_two_papers(self, sample_paper: Paper):
        assert compare_papers([sample_paper]) == "Need at least 2 papers to compare."

    def test_structured_result(self, sample_papers: list):
        result = compare_papers_structured(sample_papers[:2])
        assert result.papers
        assert isinstance(result.similarities, list)
        assert isinstance(result.differences, list)
