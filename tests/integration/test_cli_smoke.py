"""CLI smoke tests — no live network."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from research_agent.cli import main


@pytest.mark.integration
def test_cli_help_exits_zero():
    assert main(["help"]) == 0


@pytest.mark.integration
def test_cli_version_exits_zero():
    assert main(["version"]) == 0
    assert main(["--version"]) == 0


@pytest.mark.integration
def test_cli_zotero_recommend_without_db_nonzero():
    with patch("research_agent.zotero.find_zotero_db", return_value=None):
        assert main(["zotero", "recommend"]) == 1


@pytest.mark.integration
def test_cli_recommend_without_db_nonzero():
    with patch("research_agent.zotero.find_zotero_db", return_value=None):
        assert main(["recommend"]) == 1


@pytest.mark.integration
def test_cli_topics_show_with_tmp_config(tmp_data_dir):
    from research_agent import local_config

    local_config.save(["ai-ml", "nlp"], source="manual")
    with patch("research_agent.zotero.find_zotero_db", return_value=None):
        assert main(["topics", "show"]) == 0
