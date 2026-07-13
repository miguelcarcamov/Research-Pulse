"""Unit tests for misc source helpers and empty-query early returns."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from research_agent.config import NewsFeed
from research_agent.sources import arxiv, biorxiv, crossref, europepmc, rss, semanticscholar

pytestmark = pytest.mark.unit


class TestArxiv:
    def test_empty_categories(self):
        assert arxiv.fetch([]) == []

    def test_venue_from_arxiv_text(self):
        venue, year = arxiv._venue_from_arxiv_text("Accepted at NeurIPS 2023")
        assert year == 2023
        assert "NeurIPS" in venue

    def test_venue_empty(self):
        assert arxiv._venue_from_arxiv_text("") == ("", None)


class TestBiorxiv:
    def test_empty_servers(self):
        assert biorxiv.fetch([]) == []


class TestCrossref:
    def test_empty_query(self):
        assert crossref.fetch("") == []

    def test_clean_abstract(self):
        raw = "<jats:p>Hello &amp; world</jats:p>"
        assert crossref._clean_abstract(raw) == "Hello & world"


class TestEuropePmc:
    def test_empty_query(self):
        assert europepmc.fetch("") == []


class TestSemanticScholar:
    def test_empty_query(self):
        assert semanticscholar.fetch("") == []

    def test_without_api_key_returns_empty(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("S2_API_KEY", raising=False)
        assert semanticscholar.fetch("transformers") == []


class TestRss:
    def test_clean_strips_tags(self):
        assert rss._clean("<b>Hello</b> world") == "Hello world"

    def test_clean_truncates(self):
        long = "x" * 300
        cleaned = rss._clean(long, limit=20)
        assert cleaned.endswith("\u2026")
        assert len(cleaned) == 20

    def test_fetch_empty_feeds(self):
        assert rss.fetch([]) == []

    def test_fetch_with_mocked_feedparser(self):
        class Entry(dict):
            published_parsed = (2024, 1, 2, 0, 0, 0, 0, 0, 0)

        entry = Entry(title="  News  Title ", link="https://ex.com/1", summary="<p>Hi</p>")

        class Parsed:
            entries = [entry]

        with patch("research_agent.sources.rss.feedparser.parse", return_value=Parsed()):
            items = rss.fetch([NewsFeed(name="TestFeed", url="https://ex.com/rss")], per_feed=5)
        assert len(items) == 1
        assert items[0].title == "News Title"
        assert items[0].source == "TestFeed"
        assert items[0].summary == "Hi"
