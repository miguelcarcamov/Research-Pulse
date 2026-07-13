"""Unit tests for research_agent.zotero_recommend."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from research_agent.models import Paper
from research_agent.zotero_recommend import (
    _already_owned,
    _paper_doi,
    _title_key,
    recommend_from_zotero,
)

pytestmark = pytest.mark.unit


class TestHelpers:
    def test_title_key(self):
        assert _title_key("Hello, World!") == "helloworld"
        assert _title_key("") == ""

    def test_paper_doi_from_url(self):
        p = Paper(
            id="https://openalex.org/W1",
            title="T",
            abstract="",
            authors=[],
            url="https://doi.org/10.5555/new.paper",
            source="OpenAlex",
        )
        assert _paper_doi(p) == "10.5555/new.paper"

    def test_paper_doi_skips_openalex_id(self):
        p = Paper(
            id="https://openalex.org/W1",
            title="T",
            abstract="",
            authors=[],
            url="https://openalex.org/W1",
            source="OpenAlex",
        )
        assert _paper_doi(p) == ""

    def test_already_owned(self):
        p = Paper(
            id="x",
            title="Transformers for Scientific Discovery",
            abstract="",
            authors=[],
            url="https://doi.org/10.5555/test.doi.1",
            source="OpenAlex",
        )
        assert _already_owned(p, {"10.5555/test.doi.1"}, set())
        assert _already_owned(
            p,
            set(),
            {_title_key("Transformers for Scientific Discovery")},
        )
        assert not _already_owned(p, set(), set())


class TestRecommendFromZotero:
    def test_with_mocked_openalex(self, fake_zotero_db: Path, sample_paper: Paper):
        related = Paper(
            id="https://openalex.org/W999",
            title="A Completely New Related Work on Attention",
            abstract="We study attention mechanisms in transformers.",
            authors=["Z"],
            url="https://doi.org/10.9999/brand.new",
            source="OpenAlex",
            published=datetime(2025, 2, 1, tzinfo=timezone.utc),
            citations=3,
        )

        with (
            patch(
                "research_agent.zotero_recommend.find_zotero_db",
                return_value=fake_zotero_db,
            ),
            patch(
                "research_agent.zotero_recommend.openalex.fetch_related_and_citing",
                return_value=[related],
            ),
            patch(
                "research_agent.zotero_recommend.load_secrets",
            ) as mock_secrets,
        ):
            mock_secrets.return_value.sender_email = ""
            recs = recommend_from_zotero(limit=5, seeds=5, max_workers=1)

        assert recs
        assert recs[0].paper.title.startswith("A Completely New")
        assert recs[0].reasons

    def test_no_db_returns_empty(self):
        with patch(
            "research_agent.zotero_recommend.find_zotero_db",
            return_value=None,
        ):
            assert recommend_from_zotero() == []
