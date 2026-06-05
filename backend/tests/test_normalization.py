"""Tests for pipeline/normalization.py"""

import pytest
from backend.models import (
    Attribution,
    Claim,
    ClaimArgument,
    EvidenceIndicators,
    SourcePool,
    claims_store,
)
from backend.pipeline.normalization import (
    ACTOR_NORMALIZATION,
    LOCATION_NORMALIZATION,
    TARGET_NORMALIZATION,
    WEAPON_NORMALIZATION,
    _normalize_with_map,
    extract_candidate_claim_set,
    normalize_claim,
    normalize_claims_batch,
)


def _make_claim(text: str, pool: SourcePool = SourcePool.WESTERN_MAINSTREAM) -> Claim:
    return Claim(
        source_article_id="a_test",
        source_pool=pool,
        source_name="Test Source",
        claim_text_original=text,
        evidence=EvidenceIndicators(),
        attribution=Attribution(),
    )


# ---------------------------------------------------------------------------
# _normalize_with_map
# ---------------------------------------------------------------------------

class TestNormalizeWithMap:
    def test_exact_match(self):
        assert _normalize_with_map("uav", WEAPON_NORMALIZATION) == "drone"

    def test_case_insensitive(self):
        assert _normalize_with_map("UAV", WEAPON_NORMALIZATION) == "drone"
        assert _normalize_with_map("Shahed", WEAPON_NORMALIZATION) == "shahed_drone"

    def test_no_match_returns_none(self):
        assert _normalize_with_map("rocket launcher", WEAPON_NORMALIZATION) is None

    def test_partial_match(self):
        # "drone" is a key in WEAPON_NORMALIZATION and "fpv drone" contains "fpv drone"
        result = _normalize_with_map("fpv drone was used", WEAPON_NORMALIZATION)
        assert result is not None

    def test_actor_map(self):
        assert _normalize_with_map("russian forces", ACTOR_NORMALIZATION) == "russian_military"
        assert _normalize_with_map("ukraine", ACTOR_NORMALIZATION) == "ukrainian_military"

    def test_location_map(self):
        assert _normalize_with_map("kiev", LOCATION_NORMALIZATION) == "kyiv"
        assert _normalize_with_map("dnipro", LOCATION_NORMALIZATION) == "dnipro"

    def test_target_map(self):
        assert _normalize_with_map("fuel depot", TARGET_NORMALIZATION) == "fuel_depot"
        assert _normalize_with_map("bridge", TARGET_NORMALIZATION) == "bridge"


# ---------------------------------------------------------------------------
# normalize_claim
# ---------------------------------------------------------------------------

class TestNormalizeClaim:
    def test_weapon_normalization(self):
        claim = _make_claim("A Shahed drone struck the target.")
        result = normalize_claim(claim)
        assert "weapon_type" in result.arguments
        assert result.arguments["weapon_type"].normalized == "shahed_drone"

    def test_fpv_drone_normalization(self):
        claim = _make_claim("An FPV drone was used in the attack.")
        result = normalize_claim(claim)
        assert result.arguments["weapon_type"].normalized == "fpv_drone"

    def test_actor_russian_normalization(self):
        claim = _make_claim("Russian forces launched the attack.")
        result = normalize_claim(claim)
        assert "actor" in result.arguments
        assert result.arguments["actor"].normalized == "russian_military"

    def test_actor_ukrainian_normalization(self):
        claim = _make_claim("Ukrainian military confirmed the incident.")
        result = normalize_claim(claim)
        assert "actor" in result.arguments
        assert result.arguments["actor"].normalized == "ukrainian_military"

    def test_location_normalization_kyiv(self):
        claim = _make_claim("The missile struck near Kiev.")
        result = normalize_claim(claim)
        assert "location" in result.arguments
        assert result.arguments["location"].normalized == "kyiv"

    def test_location_normalization_dnipro(self):
        claim = _make_claim("A fire broke out near the Dnepr river.")
        result = normalize_claim(claim)
        assert "location" in result.arguments
        assert result.arguments["location"].normalized == "dnipro"

    def test_target_normalization(self):
        claim = _make_claim("The strike hit a fuel depot in the area.")
        result = normalize_claim(claim)
        assert "target" in result.arguments
        assert result.arguments["target"].normalized == "fuel_depot"

    def test_event_type_strike(self):
        claim = _make_claim("A drone strike hit the bridge.")
        result = normalize_claim(claim)
        assert "event_type" in result.arguments
        assert result.arguments["event_type"].normalized == "strike"

    def test_event_type_explosion(self):
        claim = _make_claim("A large explosion was heard near the depot.")
        result = normalize_claim(claim)
        assert "event_type" in result.arguments
        assert result.arguments["event_type"].normalized == "explosion"

    def test_event_type_bombardment(self):
        claim = _make_claim("Shelling continued throughout the night.")
        result = normalize_claim(claim)
        assert "event_type" in result.arguments
        assert result.arguments["event_type"].normalized == "bombardment"

    def test_time_extraction(self):
        claim = _make_claim("The attack occurred at 03:10 local time.")
        result = normalize_claim(claim)
        assert "time" in result.arguments
        assert "03:10" in result.arguments["time"].normalized

    def test_normalized_text_set(self):
        claim = _make_claim("Russian forces hit a fuel depot with a Shahed drone.")
        result = normalize_claim(claim)
        assert result.claim_text_normalized is not None
        assert "[russian_military]" in result.claim_text_normalized.lower() or \
               "[shahed_drone]" in result.claim_text_normalized.lower()

    def test_no_matches_leaves_claim_intact(self):
        text = "Something happened somewhere somehow."
        claim = _make_claim(text)
        result = normalize_claim(claim)
        assert result.claim_text_original == text
        # No arguments extracted
        assert "weapon_type" not in result.arguments
        assert "actor" not in result.arguments

    def test_attributed_claim_marks_actor(self):
        claim = _make_claim("Russian forces launched the strike.")
        claim.attribution.speaker = "Ministry of Defense"
        result = normalize_claim(claim)
        if "actor" in result.arguments:
            assert result.arguments["actor"].attributed is True


# ---------------------------------------------------------------------------
# normalize_claims_batch
# ---------------------------------------------------------------------------

class TestNormalizeClaimsBatch:
    def test_batch_normalizes_all(self):
        claims = [
            _make_claim("Shahed drone hit a bridge."),
            _make_claim("Russian military launched the attack."),
            _make_claim("The explosion near Kyiv caused damage."),
        ]
        results = normalize_claims_batch(claims)
        assert len(results) == 3
        assert "weapon_type" in results[0].arguments
        assert "actor" in results[1].arguments
        assert "event_type" in results[2].arguments

    def test_empty_batch(self):
        assert normalize_claims_batch([]) == []


# ---------------------------------------------------------------------------
# extract_candidate_claim_set
# ---------------------------------------------------------------------------

class TestExtractCandidateClaimSet:
    def setup_method(self):
        claims_store.clear()

    def teardown_method(self):
        claims_store.clear()

    def test_returns_claims_for_article(self):
        claim = _make_claim("A Shahed drone hit a fuel depot.")
        claim.source_article_id = "a_specific"
        claims_store[claim.claim_id] = claim

        results = extract_candidate_claim_set("a_specific")
        assert len(results) == 1
        assert results[0].claim_id == claim.claim_id

    def test_filters_by_article_id(self):
        c1 = _make_claim("Claim for article A")
        c1.source_article_id = "a_001"
        c2 = _make_claim("Claim for article B")
        c2.source_article_id = "a_002"
        claims_store[c1.claim_id] = c1
        claims_store[c2.claim_id] = c2

        results = extract_candidate_claim_set("a_001")
        assert all(c.source_article_id == "a_001" for c in results)
        assert len(results) == 1

    def test_unknown_article_returns_empty(self):
        assert extract_candidate_claim_set("no_such_article") == []
