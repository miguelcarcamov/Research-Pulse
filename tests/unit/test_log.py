"""Unit tests for research_agent.log."""

from __future__ import annotations

import logging

import pytest

from research_agent.log import get

pytestmark = pytest.mark.unit


class TestLog:
    def test_get_returns_logger(self):
        log = get("unit_test_logger")
        assert isinstance(log, logging.Logger)
        assert log.name == "research_agent.unit_test_logger"
