"""Unit tests for research_agent.sources.http."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from research_agent.sources.http import get

pytestmark = pytest.mark.unit


class TestHttpGet:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        with patch("research_agent.sources.http.requests.get", return_value=mock_resp) as mock_get:
            result = get("https://example.com/api", params={"q": "x"}, retries=1)
        assert result is mock_resp
        mock_get.assert_called_once()
        kwargs = mock_get.call_args.kwargs
        assert "User-Agent" in kwargs["headers"]

    def test_retry_then_fail(self):
        with (
            patch(
                "research_agent.sources.http.requests.get",
                side_effect=requests.ConnectionError("boom"),
            ) as mock_get,
            patch("research_agent.sources.http.time.sleep"),
        ):
            result = get("https://example.com/fail", retries=3, backoff=0.01)
        assert result is None
        assert mock_get.call_count == 3
