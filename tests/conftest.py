"""Shared fixtures for ResearchPulse tests."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from research_agent.models import Paper


@pytest.fixture
def sample_paper() -> Paper:
    return Paper(
        id="10.1234/example.1",
        title="Attention Is All You Need for Transformers",
        abstract="We propose the Transformer architecture based on attention mechanisms.",
        authors=["Alice", "Bob", "Carol"],
        url="https://doi.org/10.1234/example.1",
        source="OpenAlex",
        published=datetime(2024, 6, 1, tzinfo=timezone.utc),
        citations=42,
        venue="NeurIPS",
        year=2024,
    )


@pytest.fixture
def sample_papers(sample_paper: Paper) -> list:
    older = Paper(
        id="10.1234/example.2",
        title="Convolutional Networks for Vision",
        abstract="CNNs remain strong baselines for image classification tasks.",
        authors=["Dana"],
        url="https://doi.org/10.1234/example.2",
        source="arXiv",
        published=datetime(2020, 1, 15, tzinfo=timezone.utc),
        citations=10,
        venue="CVPR",
        year=2020,
    )
    unrelated = Paper(
        id="10.1234/example.3",
        title="Soil Moisture in Arid Climate Zones",
        abstract="Agricultural hydrology study of soil water retention.",
        authors=["Eve"],
        url="https://doi.org/10.1234/example.3",
        source="OpenAlex",
        published=datetime(2023, 3, 1, tzinfo=timezone.utc),
        citations=2,
    )
    return [sample_paper, older, unrelated]


@pytest.fixture
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point research_agent config ROOT data paths at a temp directory."""
    import research_agent.cache as cache_mod
    import research_agent.local_config as local_mod
    import research_agent.memory as memory_mod

    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(cache_mod, "DEFAULT_PATH", data / "seen.json")
    monkeypatch.setattr(local_mod, "LOCAL_PATH", data / "local.json")
    monkeypatch.setattr(memory_mod, "MEMORY_PATH", data / "memory.json")
    return data


def _build_minimal_zotero(db_path: Path) -> None:
    """Create a tiny Zotero-like SQLite DB for unit/integration tests."""
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE itemTypes (itemTypeID INTEGER PRIMARY KEY, typeName TEXT);
        CREATE TABLE fields (fieldID INTEGER PRIMARY KEY, fieldName TEXT);
        CREATE TABLE items (itemID INTEGER PRIMARY KEY, itemTypeID INTEGER);
        CREATE TABLE itemData (itemID INTEGER, fieldID INTEGER, valueID INTEGER);
        CREATE TABLE itemDataValues (valueID INTEGER PRIMARY KEY, value TEXT);
        CREATE TABLE creators (
            creatorID INTEGER PRIMARY KEY, firstName TEXT, lastName TEXT
        );
        CREATE TABLE itemCreators (
            itemID INTEGER, creatorID INTEGER, orderIndex INTEGER
        );
        CREATE TABLE tags (tagID INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE itemTags (itemID INTEGER, tagID INTEGER);
        CREATE TABLE collections (
            collectionID INTEGER PRIMARY KEY, collectionName TEXT
        );

        INSERT INTO itemTypes VALUES (2, 'journalArticle');
        INSERT INTO itemTypes VALUES (1, 'note');
        INSERT INTO itemTypes VALUES (3, 'attachment');
        INSERT INTO fields VALUES (1, 'title');
        INSERT INTO fields VALUES (2, 'DOI');
        INSERT INTO fields VALUES (3, 'date');

        INSERT INTO itemDataValues VALUES (1, 'Transformers for Scientific Discovery');
        INSERT INTO itemDataValues VALUES (2, '10.5555/test.doi.1');
        INSERT INTO itemDataValues VALUES (3, '2022-05-01');
        INSERT INTO itemDataValues VALUES (4, 'An Older Survey of Neural Nets');
        INSERT INTO itemDataValues VALUES (5, '10.5555/test.doi.2');
        INSERT INTO itemDataValues VALUES (6, '2018');

        INSERT INTO items VALUES (10, 2);
        INSERT INTO items VALUES (11, 2);
        INSERT INTO items VALUES (12, 3);  -- attachment, skipped

        INSERT INTO itemData VALUES (10, 1, 1);
        INSERT INTO itemData VALUES (10, 2, 2);
        INSERT INTO itemData VALUES (10, 3, 3);
        INSERT INTO itemData VALUES (11, 1, 4);
        INSERT INTO itemData VALUES (11, 2, 5);
        INSERT INTO itemData VALUES (11, 3, 6);

        INSERT INTO creators VALUES (1, 'Ada', 'Lovelace');
        INSERT INTO itemCreators VALUES (10, 1, 0);

        INSERT INTO tags VALUES (1, 'machine learning');
        INSERT INTO tags VALUES (2, 'nlp');
        INSERT INTO itemTags VALUES (10, 1);
        INSERT INTO itemTags VALUES (10, 2);

        INSERT INTO collections VALUES (1, 'AI Research');
        """
    )
    conn.commit()
    conn.close()


@pytest.fixture
def fake_zotero_db(tmp_path: Path) -> Path:
    db = tmp_path / "zotero.sqlite"
    _build_minimal_zotero(db)
    return db


@pytest.fixture
def openalex_work_payload() -> dict:
    return {
        "id": "https://openalex.org/W123",
        "title": "A Newer Paper Building on Transformers",
        "abstract_inverted_index": {
            "We": [0],
            "extend": [1],
            "transformer": [2],
            "models": [3],
        },
        "authorships": [
            {"author": {"display_name": "New Author"}},
        ],
        "doi": "https://doi.org/10.5555/new.paper",
        "publication_date": "2025-01-10",
        "publication_year": 2025,
        "cited_by_count": 5,
        "primary_location": {
            "source": {"display_name": "ICML"},
        },
        "related_works": ["https://openalex.org/W999"],
    }
