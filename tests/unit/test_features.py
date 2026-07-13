"""Unit tests for research_agent.features."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from research_agent.features import extract_features, extract_features_keyword, format_features
from research_agent.models import Paper

pytestmark = pytest.mark.unit


class TestExtractFeatures:
    def test_keyword_fallback(self, sample_paper: Paper):
        with patch("research_agent.features.is_llm_available", return_value=False):
            features = extract_features(sample_paper, use_llm=True)
        assert features.paper_id == sample_paper.id
        assert features.title == sample_paper.title
        assert "propose" in features.methodology.lower()

    def test_keyword_direct(self, sample_paper: Paper):
        features = extract_features_keyword(sample_paper)
        assert features.methodology
        text = format_features(features)
        assert sample_paper.title in text
