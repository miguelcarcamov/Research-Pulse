"""Integration: multi-source search with mocks (no live network)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from research_agent.models import Paper
from research_agent.search import search_by_topic, search_papers


def _p(pid: str, title: str, abstract: str = "", source: str = "OpenAlex") -> Paper:
    return Paper(
        id=pid,
        title=title,
        abstract=abstract or f"Abstract about {title}",
        authors=["Author"],
        url=f"https://doi.org/{pid}" if pid.startswith("10.") else f"https://example/{pid}",
        source=source,
        published=datetime(2024, 6, 1, tzinfo=timezone.utc),
        citations=10,
    )


@pytest.mark.integration
def test_search_papers_parallel_dedup_and_bm25():
    # Same DOI from two sources → one result after dedup.
    arxiv_hit = _p(
        "10.1234/dup",
        "Attention Mechanisms for Efficient Transformers",
        "We study attention for transformer models.",
        source="arXiv",
    )
    openalex_dup = _p(
        "10.1234/dup",
        "Attention Mechanisms for Efficient Transformers",
        "We study attention for transformer models.",
        source="OpenAlex",
    )
    other = _p(
        "10.1234/other",
        "Soil Moisture Sensing Networks",
        "Hydrology and remote sensing of soil water.",
        source="Crossref",
    )

    with (
        patch("research_agent.search.search_arxiv", return_value=[arxiv_hit]),
        patch("research_agent.search.search_openalex", return_value=[openalex_dup]),
        patch("research_agent.search.search_semanticscholar", return_value=[]),
        patch("research_agent.search.search_crossref", return_value=[other]),
    ):
        results = search_papers(
            "transformer attention",
            sources=["arxiv", "openalex", "semanticscholar", "crossref"],
            limit=10,
            use_bm25=True,
        )

    ids = [p.id for p in results]
    assert ids.count("10.1234/dup") == 1
    assert results[0].id == "10.1234/dup"
    assert results[0].score >= results[-1].score


@pytest.mark.integration
def test_search_by_topic_ai_ml_mocked_sources():
    topic_paper = _p(
        "10.1234/ml.1",
        "Deep Learning for Graph Neural Networks",
        "machine learning neural networks deep learning representation learning",
        source="OpenAlex",
    )

    with (
        patch("research_agent.search.biorxiv.fetch", return_value=[]),
        patch("research_agent.search.openalex.fetch", return_value=[topic_paper]),
        patch("research_agent.search.semanticscholar.fetch", return_value=[]),
        patch("research_agent.search.europepmc.fetch", return_value=[]),
        patch("research_agent.search.arxiv.fetch", return_value=[]),
    ):
        results = search_by_topic("ai-ml", days=7, limit=5)

    assert results
    assert results[0].title == topic_paper.title
