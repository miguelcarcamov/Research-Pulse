"""Unit tests for research_agent.summarize."""

from __future__ import annotations

import pytest

from research_agent.config import Secrets
from research_agent.models import Paper
from research_agent.summarize import Summarizer

pytestmark = pytest.mark.unit


def _empty_secrets() -> Secrets:
    return Secrets(
        subscribers_csv_url="",
        smtp_host="",
        smtp_port=587,
        smtp_user="",
        smtp_key="",
        sender_email="",
        sender_name="ResearchPulse",
        site_url="",
        groq_api_key="",
        gemini_api_key="",
        ollama_host="",
        ollama_model="llama3.2",
    )


class TestSummarizer:
    def test_abstract_fallback_no_keys(self, sample_paper: Paper):
        s = Summarizer(_empty_secrets(), abstract_max_chars=80)
        assert s.backend == "abstract"
        assert not s.uses_llm
        summary = s.summarize(sample_paper)
        assert summary
        assert len(summary) <= 81  # trim may add ellipsis
        assert "Transformer" in summary or "attention" in summary.lower()

    def test_annotate(self, sample_papers: list):
        s = Summarizer(_empty_secrets(), abstract_max_chars=100)
        s.annotate(sample_papers)
        assert all(p.summary for p in sample_papers)
