"""Unit tests for research_agent.models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from research_agent.models import NewsItem, Paper

pytestmark = pytest.mark.unit


class TestPaperAuthorLine:
    def test_empty_authors(self):
        p = Paper(id="1", title="T", abstract="", authors=[], url="", source="x")
        assert p.author_line() == ""

    def test_within_limit(self, sample_paper: Paper):
        assert sample_paper.author_line(limit=3) == "Alice, Bob, Carol"

    def test_et_al_when_over_limit(self, sample_paper: Paper):
        assert sample_paper.author_line(limit=2) == "Alice, Bob et al."


class TestPaperVenueLine:
    def test_venue_and_year(self, sample_paper: Paper):
        assert sample_paper.venue_line() == "NeurIPS, 2024"

    def test_year_omitted_when_in_venue(self):
        p = Paper(
            id="1",
            title="T",
            abstract="",
            authors=[],
            url="",
            source="x",
            venue="NeurIPS 2024",
            year=2024,
        )
        assert p.venue_line() == "NeurIPS 2024"

    def test_core_rank_suffix(self, sample_paper: Paper):
        sample_paper.core_rank = "A*"
        assert sample_paper.venue_line() == "NeurIPS, 2024 · CORE A*"

    def test_core_rank_only(self):
        p = Paper(id="1", title="T", abstract="", authors=[], url="", source="x", core_rank="A")
        assert p.venue_line() == "CORE A"


class TestNewsItem:
    def test_basics(self):
        item = NewsItem(
            title="New grant",
            url="https://example.com/n",
            source="Nature News",
            summary="Short blurb",
            published=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        assert item.title == "New grant"
        assert item.source == "Nature News"
        assert item.summary == "Short blurb"
        assert item.published.year == 2024
