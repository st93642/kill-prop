"""Tests for pipeline/scoring.py"""

import pytest
from backend.models import (
    Attribution,
    Claim,
    ClaimArgument,
    ClaimBucket,
    EvidenceIndicators,
    Event,
    SourcePool,
    claims_store,
    events_store,
)
from backend.pipeline.scoring import (
    _claims_agree,
    score_claim,
    score_claim_field,
    score_event_claims,
)


def _make_claim(
    text: str = "A strike occurred.",
    pool: SourcePool = SourcePool.WESTERN_MAINSTREAM,
    source: str = "Reuters",
    bucket: ClaimBucket = ClaimBucket.VERIFIED_FACT,
    arguments: dict | None = None,
    evidence: EvidenceIndicators | None = None,
    propaganda_flags: list[str] | None = None,
) -> Claim:
    c = Claim(
        source_article_id="a_test",
        source_pool=pool,
        source_name=source,
        claim_text_original=text,
        bucket=bucket,
        evidence=evidence or EvidenceIndicators(),
        attribution=Attribution(),
    )
    if arguments:
        c.arguments = arguments
    if propaganda_flags:
        c.propaganda_flags = propaganda_flags
    return c


# ---------------------------------------------------------------------------
# _claims_agree
# ---------------------------------------------------------------------------

class TestClaimsAgree:
    def test_identical_arguments_agree(self):
        args = {
            "event_type": ClaimArgument(value="strike", normalized="strike"),
            "target": ClaimArgument(value="bridge", normalized="bridge"),
        }
        c1 = _make_claim(arguments=dict(args))
        c2 = _make_claim(arguments=dict(args))
        assert _claims_agree(c1, c2) is True

    def test_different_targets_disagree(self):
        c1 = _make_claim(arguments={
            "event_type": ClaimArgument(value="strike", normalized="strike"),
            "target": ClaimArgument(value="bridge", normalized="bridge"),
        })
        c2 = _make_claim(arguments={
            "event_type": ClaimArgument(value="strike", normalized="strike"),
            "target": ClaimArgument(value="power plant", normalized="power_plant"),
        })
        # 50% agreement (event_type matches, target differs) → agree (>= 0.5 threshold)
        assert _claims_agree(c1, c2) is True

    def test_completely_different_claims_disagree(self):
        c1 = _make_claim(arguments={
            "event_type": ClaimArgument(value="explosion", normalized="explosion"),
            "target": ClaimArgument(value="bridge", normalized="bridge"),
        })
        c2 = _make_claim(arguments={
            "event_type": ClaimArgument(value="fire", normalized="fire"),
            "target": ClaimArgument(value="depot", normalized="fuel_depot"),
        })
        assert _claims_agree(c1, c2) is False

    def test_no_shared_fields_disagree(self):
        c1 = _make_claim(arguments={
            "event_type": ClaimArgument(value="strike", normalized="strike"),
        })
        c2 = _make_claim(arguments={
            "actor": ClaimArgument(value="russian forces", normalized="russian_military"),
        })
        # No shared normalized fields → False
        assert _claims_agree(c1, c2) is False


# ---------------------------------------------------------------------------
# score_claim
# ---------------------------------------------------------------------------

class TestScoreClaim:
    def test_score_is_between_0_and_1(self):
        claim = _make_claim()
        score = score_claim(claim)
        assert 0.0 <= score <= 1.0

    def test_official_statement_increases_score(self):
        base = _make_claim()
        with_evidence = _make_claim(
            evidence=EvidenceIndicators(official_statement=True)
        )
        assert score_claim(with_evidence) > score_claim(base)

    def test_satellite_imagery_increases_score(self):
        base = _make_claim()
        with_satellite = _make_claim(
            evidence=EvidenceIndicators(satellite_imagery=True)
        )
        assert score_claim(with_satellite) > score_claim(base)

    def test_opinionated_framing_penalized(self):
        factual = _make_claim(bucket=ClaimBucket.VERIFIED_FACT)
        framing = _make_claim(bucket=ClaimBucket.OPINIONATED_FRAMING)
        assert score_claim(framing) < score_claim(factual)

    def test_propaganda_flags_penalized(self):
        clean = _make_claim()
        flagged = _make_claim(propaganda_flags=["loaded_language", "us_vs_them"])
        assert score_claim(flagged) < score_claim(clean)

    def test_corroboration_from_multiple_pools(self):
        claim = _make_claim(
            arguments={
                "event_type": ClaimArgument(value="strike", normalized="strike"),
                "target": ClaimArgument(value="bridge", normalized="bridge"),
            }
        )
        # Supporting claims from different pools
        related = [
            _make_claim(
                pool=SourcePool.RUSSIAN_STATE,
                arguments={
                    "event_type": ClaimArgument(value="strike", normalized="strike"),
                    "target": ClaimArgument(value="bridge", normalized="bridge"),
                },
            ),
            _make_claim(
                pool=SourcePool.NEUTRAL_WIRE,
                arguments={
                    "event_type": ClaimArgument(value="strike", normalized="strike"),
                    "target": ClaimArgument(value="bridge", normalized="bridge"),
                },
            ),
        ]
        score_with = score_claim(claim, all_related_claims=related)
        score_without = score_claim(claim)
        assert score_with > score_without

    def test_known_reliable_source_scores_higher(self):
        reuters = _make_claim(source="Reuters")
        unknown = _make_claim(source="unknown_outlet")
        assert score_claim(reuters) > score_claim(unknown)

    def test_specificity_increases_score(self):
        few_args = _make_claim(arguments={
            "event_type": ClaimArgument(value="strike", normalized="strike"),
        })
        many_args = _make_claim(arguments={
            "event_type": ClaimArgument(value="strike", normalized="strike"),
            "target": ClaimArgument(value="depot", normalized="fuel_depot"),
            "location": ClaimArgument(value="kyiv", normalized="kyiv"),
            "weapon_type": ClaimArgument(value="drone", normalized="drone"),
            "actor": ClaimArgument(value="russian forces", normalized="russian_military"),
            "time": ClaimArgument(value="03:10", normalized="03:10"),
        })
        assert score_claim(many_args) > score_claim(few_args)


# ---------------------------------------------------------------------------
# score_claim_field
# ---------------------------------------------------------------------------

class TestScoreClaimField:
    def test_score_between_0_and_1(self):
        claim = _make_claim()
        score = score_claim_field("event_type", claim, 0.5)
        assert 0.0 <= score <= 1.0

    def test_on_record_attribution_helps(self):
        claim = _make_claim()
        claim.attribution.status = "on_record"
        on_record = score_claim_field("event_type", claim, 0.5)

        claim2 = _make_claim()
        claim2.attribution.status = "anonymous"
        anonymous = score_claim_field("event_type", claim2, 0.5)

        assert on_record > anonymous

    def test_official_statement_evidence_helps(self):
        no_ev = _make_claim()
        with_ev = _make_claim(evidence=EvidenceIndicators(official_statement=True))
        assert score_claim_field("target", with_ev, 0.5) > score_claim_field("target", no_ev, 0.5)

    def test_higher_field_confidence_gives_higher_score(self):
        claim = _make_claim()
        low = score_claim_field("event_type", claim, 0.1)
        high = score_claim_field("event_type", claim, 0.9)
        assert high > low


# ---------------------------------------------------------------------------
# score_event_claims
# ---------------------------------------------------------------------------

class TestScoreEventClaims:
    def setup_method(self):
        claims_store.clear()
        events_store.clear()

    def teardown_method(self):
        claims_store.clear()
        events_store.clear()

    def test_returns_dict_of_scores(self):
        event = Event()
        c1 = _make_claim("Shahed drone hit a bridge.")
        c1.event_id = event.event_id
        c2 = _make_claim("Fire broke out near the depot.")
        c2.event_id = event.event_id
        event.claim_ids = [c1.claim_id, c2.claim_id]
        claims_store[c1.claim_id] = c1
        claims_store[c2.claim_id] = c2
        events_store[event.event_id] = event

        scores = score_event_claims(event)
        assert c1.claim_id in scores
        assert c2.claim_id in scores
        for s in scores.values():
            assert 0.0 <= s <= 1.0

    def test_empty_event_returns_empty_dict(self):
        event = Event()
        events_store[event.event_id] = event
        assert score_event_claims(event) == {}
