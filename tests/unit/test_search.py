"""Unit tests for research_agent.search."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from research_agent.models import Paper
from research_agent.search import _dedup, _keyword_score, search_papers

pytestmark = pytest.mark.unit


class TestHelpers:
    def test_dedup_by_id_and_title(self, sample_paper: Paper):
        dup_id = Paper(
            id=sample_paper.id,
            title="Different title",
            abstract="",
            authors=[],
            url="",
            source="x",
        )
        dup_title = Paper(
            id="other-id",
            title=sample_paper.title,
            abstract="",
            authors=[],
            url="",
            source="x",
        )
        unique = _dedup([sample_paper, dup_id, dup_title])
        assert len(unique) == 1

    def test_keyword_score(self, sample_paper: Paper):
        score = _keyword_score(sample_paper, "transformer attention")
        assert score > 0
        assert _keyword_score(sample_paper, "") == 0.0


class TestSearchPapers:
    def test_empty_query(self):
        assert search_papers("   ") == []

    def test_all_sources_mocked(self, sample_paper: Paper):
        older = Paper(
            id="10.9/other",
            title="Other attention paper",
            abstract="attention networks",
            authors=[],
            url="",
            source="Crossref",
            published=datetime(2023, 1, 1, tzinfo=timezone.utc),
        )
        with (
            patch("research_agent.search.search_arxiv", return_value=[sample_paper]),
            patch("research_agent.search.search_openalex", return_value=[older]),
            patch("research_agent.search.search_semanticscholar", return_value=[]),
            patch("research_agent.search.search_crossref", return_value=[]),
        ):
            results = search_papers(
                "transformer attention",
                sources=["arxiv", "openalex", "semanticscholar", "crossref"],
                limit=5,
                use_bm25=True,
            )
        assert len(results) >= 1
        ids = {p.id for p in results}
        assert sample_paper.id in ids
