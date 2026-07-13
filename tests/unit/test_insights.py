"""Unit tests for research_agent.insights."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_agent.insights import format_insights, generate_insights
from research_agent.memory import ResearchMemory

pytestmark = pytest.mark.unit


class TestInsights:
    def test_generate_and_format_smoke(self, sample_papers: list, tmp_path: Path):
        mem = ResearchMemory(path=tmp_path / "m.json")
        mem.interests["keywords"] = ["quantum entanglement"]  # unlikely in samples
        mem.interests["topics"] = ["soil moisture"]
        insights = generate_insights(sample_papers, memory=mem, use_llm=False)
        assert "contradictions" in insights
        assert "gaps" in insights
        assert "trends" in insights
        text = format_insights(insights)
        assert "RESEARCH INSIGHTS" in text
