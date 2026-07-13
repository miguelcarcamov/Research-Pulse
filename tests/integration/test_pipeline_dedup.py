"""Integration: pipeline dedup with SeenCache and title normalization."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from research_agent.cache import SeenCache
from research_agent.models import Paper
from research_agent.pipeline import _dedup, _normalize_title


def _paper(pid: str, title: str) -> Paper:
    return Paper(
        id=pid,
        title=title,
        abstract="x",
        authors=["A"],
        url=f"https://example/{pid}",
        source="test",
        published=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


@pytest.mark.integration
def test_dedup_skips_ids_already_in_seen_cache(tmp_data_dir):
    cache = SeenCache(tmp_data_dir / "seen.json")
    cache.mark(["already-seen-id"])
    cache.save()

    papers = [
        _paper("already-seen-id", "Seen Before"),
        _paper("brand-new-id", "Fresh Paper"),
    ]
    out = _dedup(papers, cache)
    assert [p.id for p in out] == ["brand-new-id"]


@pytest.mark.integration
def test_dedup_normalize_title_collision(tmp_data_dir):
    cache = SeenCache(tmp_data_dir / "seen.json")
    a = _paper("id-a", "Attention Is All You Need!")
    b = _paper("id-b", "attention is all you need")
    out = _dedup([a, b], cache)
    assert len(out) == 1
    assert out[0].id == "id-a"


@pytest.mark.integration
def test_normalize_title_strips_punctuation_and_case():
    assert _normalize_title("Hello, World!") == _normalize_title("hello world")
    assert _normalize_title("A---B") == "ab"
