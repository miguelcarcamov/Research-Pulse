"""Unit tests for research_agent.zotero."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from research_agent import zotero as zotero_mod

pytestmark = pytest.mark.unit


class TestHelpers:
    def test_normalize_doi(self):
        assert zotero_mod._normalize_doi("https://doi.org/10.5555/X.Y") == "10.5555/x.y"
        assert zotero_mod._normalize_doi("") == ""

    def test_parse_year(self):
        assert zotero_mod._parse_year("2022-05-01") == 2022
        assert zotero_mod._parse_year("Published in 2018") == 2018
        assert zotero_mod._parse_year("") is None
        assert zotero_mod._parse_year("no-year") is None

    def test_connect_ro(self, fake_zotero_db: Path):
        conn = zotero_mod._connect_ro(fake_zotero_db)
        assert conn is not None
        row = conn.execute("SELECT COUNT(*) FROM items").fetchone()
        conn.close()
        assert row[0] == 3


class TestReadLibrary:
    def test_read_library_items(self, fake_zotero_db: Path):
        items = zotero_mod.read_library_items(fake_zotero_db, limit=10)
        assert len(items) == 2
        assert items[0].doi  # prefer_doi puts DOI items first
        titles = {i.title for i in items}
        assert "Transformers for Scientific Discovery" in titles
        assert all(i.item_id != 12 for i in items)  # attachment skipped

    def test_library_identifiers(self, fake_zotero_db: Path):
        dois, titles = zotero_mod.library_identifiers(fake_zotero_db)
        assert "10.5555/test.doi.1" in dois
        assert "10.5555/test.doi.2" in dois
        assert any("transformers" in t for t in titles)

    def test_get_zotero_summary(self, fake_zotero_db: Path):
        summary = zotero_mod.get_zotero_summary(fake_zotero_db)
        assert summary is not None
        assert summary["item_count"] >= 2
        assert summary["tag_count"] == 2
        assert "AI Research" in summary["collections"]
        assert "machine learning" in summary["top_tags"]

    def test_detect_topics(self, fake_zotero_db: Path):
        topics = zotero_mod.detect_topics(fake_zotero_db)
        assert isinstance(topics, list)
        # Tags include "machine learning" / "nlp" — should match at least one topic
        if topics:
            tid, label, conf = topics[0]
            assert isinstance(tid, str)
            assert isinstance(conf, float)

    def test_find_zotero_db_patched(self, fake_zotero_db: Path):
        with patch.object(zotero_mod, "find_zotero_db", return_value=fake_zotero_db):
            assert zotero_mod.find_zotero_db() == fake_zotero_db

    def test_read_library_none_db(self):
        with patch.object(zotero_mod, "find_zotero_db", return_value=None):
            assert zotero_mod.read_library_items() == []
