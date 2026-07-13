"""Unit tests for research_agent.subscribers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from research_agent.config import Secrets
from research_agent.subscribers import (
    _parse_csv,
    _split_topics,
    _truthy,
    load_subscribers,
)

pytestmark = pytest.mark.unit


class TestParseLogic:
    def test_truthy(self):
        assert _truthy("true")
        assert _truthy("YES")
        assert _truthy("1")
        assert not _truthy("false")
        assert not _truthy("")

    def test_split_topics(self):
        assert _split_topics("ai-ml; NLP, cv") == ["ai-ml", "nlp", "cv"]
        assert _split_topics("") == []

    def test_parse_csv(self):
        csv_text = (
            "email,topics,confirmed,token\n"
            "ok@example.com,ai-ml;nlp,true,tok1\n"
            "nope@example.com,ai-ml,false,tok2\n"
            "bad,,,true,\n"
        )
        subs = _parse_csv(csv_text)
        assert len(subs) == 1
        assert subs[0].email == "ok@example.com"
        assert subs[0].topics == ["ai-ml", "nlp"]
        assert subs[0].token == "tok1"


class TestLoadSubscribers:
    def test_mocked_remote_csv(self):
        secrets = Secrets(
            subscribers_csv_url="https://example.com/subs.csv",
            smtp_host="",
            smtp_port=587,
            smtp_user="",
            smtp_key="",
            sender_email="",
            sender_name="",
            site_url="",
            groq_api_key="",
            gemini_api_key="",
            ollama_host="",
            ollama_model="",
        )
        mock_resp = MagicMock()
        mock_resp.text = "email,topics,confirmed,token\na@b.com,nlp,yes,t\n"
        with patch("research_agent.subscribers.get", return_value=mock_resp):
            subs = load_subscribers(secrets)
        assert len(subs) == 1
        assert subs[0].email == "a@b.com"
