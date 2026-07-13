"""Unit tests for research_agent.sources.openalex."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from research_agent.sources import openalex

pytestmark = pytest.mark.unit


class TestNormalizeDoi:
    def test_strips_url_prefix(self):
        assert openalex.normalize_doi("https://doi.org/10.1234/Foo.Bar") == "10.1234/foo.bar"

    def test_doi_prefix(self):
        assert openalex.normalize_doi("doi:10.1/x") == "10.1/x"

    def test_empty(self):
        assert openalex.normalize_doi("") == ""


class TestReconstructAbstract:
    def test_rebuilds_from_inverted_index(self):
        idx = {"We": [0], "extend": [1], "models": [2]}
        assert openalex._reconstruct_abstract(idx) == "We extend models"

    def test_empty(self):
        assert openalex._reconstruct_abstract(None) == ""
        assert openalex._reconstruct_abstract({}) == ""


class TestPaperFromWork:
    def test_converts_payload(self, openalex_work_payload: dict):
        paper = openalex._paper_from_work(openalex_work_payload)
        assert paper is not None
        assert paper.title == "A Newer Paper Building on Transformers"
        assert paper.abstract == "We extend transformer models"
        assert paper.authors == ["New Author"]
        assert paper.venue == "ICML"
        assert paper.citations == 5
        assert paper.year == 2025
        assert paper.source == "OpenAlex"

    def test_missing_title_returns_none(self):
        assert openalex._paper_from_work({"title": ""}) is None


class TestSignificantQueryTerms:
    def test_filters_stop_words(self):
        terms = openalex.significant_query_terms("The Attention Mechanism for Neural Models")
        assert "the" not in terms.lower().split()
        assert "for" not in terms.lower().split()
        assert "Attention" in terms
        assert "Mechanism" in terms


class TestFetch:
    def test_empty_query(self):
        assert openalex.fetch("") == []

    def test_mocked_json(self, openalex_work_payload: dict):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [openalex_work_payload]}
        with patch("research_agent.sources.openalex.get", return_value=mock_resp) as mock_get:
            papers = openalex.fetch("transformers", lookback_days=7, max_results=5)
        mock_get.assert_called_once()
        assert len(papers) == 1
        assert papers[0].title.startswith("A Newer Paper")

    def test_get_returns_none(self):
        with patch("research_agent.sources.openalex.get", return_value=None):
            assert openalex.fetch("transformers") == []
