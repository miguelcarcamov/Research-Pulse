"""Integration: Zotero library → OpenAlex related/citing → recommendations."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from research_agent.models import Paper
from research_agent.zotero_recommend import (
    format_library_recommendations,
    recommend_from_zotero,
)


def _rec_paper(**overrides) -> Paper:
    base = dict(
        id="10.5555/new.paper",
        title="A Newer Paper Building on Transformers",
        abstract="We extend transformer models for scientific discovery.",
        authors=["New Author"],
        url="https://doi.org/10.5555/new.paper",
        source="OpenAlex",
        published=datetime(2025, 1, 10, tzinfo=timezone.utc),
        citations=5,
        venue="ICML",
        year=2025,
    )
    base.update(overrides)
    return Paper(**base)


@pytest.mark.integration
def test_recommend_from_zotero_excludes_owned_dois(fake_zotero_db: Path):
    owned = _rec_paper(
        id="10.5555/test.doi.1",
        title="Transformers for Scientific Discovery",
        url="https://doi.org/10.5555/test.doi.1",
    )
    fresh = _rec_paper()
    also_owned_title = _rec_paper(
        id="10.9999/other",
        title="An Older Survey of Neural Nets",
        url="https://doi.org/10.9999/other",
    )

    with (
        patch("research_agent.zotero_recommend.find_zotero_db", return_value=fake_zotero_db),
        patch(
            "research_agent.zotero_recommend.openalex.fetch_related_and_citing",
            return_value=[owned, fresh, also_owned_title],
        ),
    ):
        recs = recommend_from_zotero(limit=10, seeds=5, max_workers=1)

    dois = {r.paper.url.replace("https://doi.org/", "").lower() for r in recs}
    assert "10.5555/test.doi.1" not in dois
    assert "10.5555/test.doi.2" not in dois
    assert any("10.5555/new.paper" in (r.paper.url or r.paper.id) for r in recs)
    assert all("Transformers for Scientific Discovery" != r.paper.title for r in recs)


@pytest.mark.integration
def test_format_library_recommendations_contains_title(fake_zotero_db: Path):
    fresh = _rec_paper()

    with (
        patch("research_agent.zotero_recommend.find_zotero_db", return_value=fake_zotero_db),
        patch(
            "research_agent.zotero_recommend.openalex.fetch_related_and_citing",
            return_value=[fresh],
        ),
    ):
        recs = recommend_from_zotero(limit=5, seeds=5, max_workers=1)

    text = format_library_recommendations(recs)
    assert fresh.title in text
    assert "NEWER PAPERS FROM YOUR ZOTERO LIBRARY" in text
