"""Unit tests for research_agent.cache."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_agent.cache import SeenCache

pytestmark = pytest.mark.unit


class TestSeenCache:
    def test_mark_and_is_seen(self, tmp_data_dir: Path):
        cache = SeenCache()
        assert not cache.is_seen("arxiv:1234.5678")
        cache.mark(["arxiv:1234.5678", "doi:10.1/x"])
        assert cache.is_seen("arxiv:1234.5678")
        assert cache.is_seen("DOI:10.1/x")  # normalization is case-insensitive

    def test_save_and_load(self, tmp_data_dir: Path):
        cache = SeenCache()
        cache.mark(["paper-a"])
        cache.save()
        assert (tmp_data_dir / "seen.json").is_file()

        reloaded = SeenCache()
        assert reloaded.is_seen("paper-a")
        assert reloaded.last_run is not None

    def test_custom_path(self, tmp_path: Path):
        path = tmp_path / "custom_seen.json"
        cache = SeenCache(path=path)
        cache.mark(["x"])
        cache.save()
        assert path.is_file()
        assert SeenCache(path=path).is_seen("x")
