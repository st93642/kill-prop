"""Tests for LLM-based claim extraction.

Uses mocking to avoid requiring a real LLM model download during test runs.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.models import Article, SourcePool
from backend.pipeline.llm_extraction import extract_claims_llm


def _make_article(full_text: str = "A drone strike hit a fuel depot.") -> Article:
    return Article(
        canonical_url="https://test.com",
        title="Test Article: Drone strike near Dnipro",
        source_name="Test Source",
        source_pool=SourcePool.WESTERN_MAINSTREAM,
        source_country="US",
        full_text=full_text,
    )


SAMPLE_LLM_RESPONSE = (
    '['
    '{"claim_text": "A drone strike hit a fuel depot.", '
    '"bucket": "verified_fact", '
    '"arguments": {"weapon_type": "drone", "target": "fuel_depot"}, '
    '"evidence": {"timestamp_geolocation": true}, '
    '"attribution": {"status": "on_record", "speaker": null, "phrase": null}, '
    '"propaganda_flags": []}, '
    '{"claim_text": "The defense ministry confirmed the attack.", '
    '"bucket": "attributed_statement", '
    '"arguments": {}, '
    '"evidence": {"official_statement": true}, '
    '"attribution": {"status": "on_record", "speaker": "defense ministry", "phrase": "confirmed"}, '
    '"propaganda_flags": []}'
    ']'
)


class TestExtractClaimsLLM:
    @patch("backend.pipeline.llm_extraction.get_llm")
    def test_parses_valid_json_response(self, mock_get_llm):
        """Should parse a well-formed LLM JSON response into Claim objects."""
        mock_llm = MagicMock()
        mock_llm.return_value = {"choices": [{"text": SAMPLE_LLM_RESPONSE[1:]}]}  # strip leading [
        mock_get_llm.return_value = mock_llm

        article = _make_article()
        claims = extract_claims_llm(article)

        assert len(claims) == 2
        assert claims[0].claim_text_original == "A drone strike hit a fuel depot."
        assert claims[0].bucket.value == "verified_fact"
        assert claims[1].bucket.value == "attributed_statement"
        assert claims[1].attribution.speaker == "defense ministry"

    @patch("backend.pipeline.llm_extraction.get_llm")
    def test_handles_malformed_json_gracefully(self, mock_get_llm):
        """Should return empty list on malformed LLM output without crashing."""
        mock_llm = MagicMock()
        mock_llm.return_value = {"choices": [{"text": "not valid json at all {{{"}]}
        mock_get_llm.return_value = mock_llm

        article = _make_article()
        claims = extract_claims_llm(article)
        assert claims == []

    @patch("backend.pipeline.llm_extraction.get_llm")
    def test_skips_non_dict_items(self, mock_get_llm):
        """Should skip list items that are not dicts."""
        bad_json = '["string_item", {"claim_text": "valid claim", "bucket": "inference", "arguments": {}, "evidence": {}, "attribution": {}, "propaganda_flags": []}]'
        mock_llm = MagicMock()
        mock_llm.return_value = {"choices": [{"text": bad_json[1:]}]}
        mock_get_llm.return_value = mock_llm

        article = _make_article()
        claims = extract_claims_llm(article)

        assert len(claims) == 1
        assert claims[0].claim_text_original == "valid claim"

    @patch("backend.pipeline.llm_extraction.get_llm")
    def test_defaults_invalid_bucket_to_inference(self, mock_get_llm):
        """Should fall back to 'inference' when bucket value is unknown."""
        bad_bucket = '[{"claim_text": "Some claim.", "bucket": "unknown_bucket", "arguments": {}, "evidence": {}, "attribution": {}, "propaganda_flags": []}]'
        mock_llm = MagicMock()
        mock_llm.return_value = {"choices": [{"text": bad_bucket[1:]}]}
        mock_get_llm.return_value = mock_llm

        article = _make_article()
        claims = extract_claims_llm(article)

        assert claims[0].bucket.value == "inference"

    @patch("backend.pipeline.llm_extraction.get_llm")
    def test_llm_failure_returns_empty_list(self, mock_get_llm):
        """Should return empty list when LLM call raises exception."""
        mock_get_llm.side_effect = RuntimeError("LLM not available")

        article = _make_article()
        claims = extract_claims_llm(article)
        assert claims == []
