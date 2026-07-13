"""Unit tests for research_agent.venues (real CORE catalog)."""

from __future__ import annotations

import pytest

from research_agent.models import Paper
from research_agent.venues import (
    enrich_paper,
    filter_papers,
    list_venues,
    lookup_core,
    matches_venue,
)

pytestmark = pytest.mark.unit


class TestLookupCore:
    def test_neurips_is_a_star(self):
        assert lookup_core("NeurIPS") == "A*"

    def test_empty_venue(self):
        assert lookup_core("") == ""

    def test_unknown(self):
        assert lookup_core("Unknown Local Workshop XYZ") == ""


class TestListVenues:
    def test_returns_entries(self):
        venues = list_venues()
        assert len(venues) > 10
        assert any(v.get("id") == "neurips" for v in venues)

    def test_core_min_filter(self):
        a_star = list_venues(core_min="A*")
        assert a_star
        assert all(v.get("core") == "A*" for v in a_star)


class TestEnrichAndFilter:
    def test_enrich_paper(self, sample_paper: Paper):
        sample_paper.core_rank = ""
        enriched = enrich_paper(sample_paper)
        assert enriched.core_rank == "A*"
        assert enriched.year == 2024

    def test_matches_venue(self, sample_paper: Paper):
        assert matches_venue(sample_paper, "neurips")
        assert matches_venue(sample_paper, "NeurIPS")
        assert not matches_venue(sample_paper, "ICML")

    def test_filter_papers(self, sample_papers: list):
        filtered = filter_papers(sample_papers, venues=["cvpr"], year=2020)
        assert len(filtered) == 1
        assert filtered[0].venue == "CVPR"

        by_core = filter_papers(sample_papers, core_min="A*")
        assert all(p.core_rank == "A*" for p in by_core)
