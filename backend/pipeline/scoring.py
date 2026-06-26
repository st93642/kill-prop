"""Stage 5b: Evidence Scoring Engine.

Scores claims by evidence strength, corroboration quality, specificity,
and penalizes loaded framing.
"""

from __future__ import annotations

from backend.models import (
    Claim,
    ClaimBucket,
    Event,
    lookup_source_reliability,
    source_reliability_priors,
)


def score_claim(claim: Claim, all_related_claims: list[Claim] | None = None) -> float:
    """Score a single claim using the v1 scoring formula.
    
    score = 0.35(corroboration) + 0.25(primary_evidence)
          + 0.15(source_reliability) + 0.15(specificity) - 0.10(loaded_framing)
    """
    # 1. Independent corroboration (0.35)
    if all_related_claims:
        same_meaning = [
            c for c in all_related_claims
            if c.claim_id != claim.claim_id
            and _claims_agree(claim, c)
        ]
        unique_pools = len({c.source_pool for c in same_meaning})
        corroboration = min(unique_pools / 4.0, 1.0) * 0.35
    else:
        corroboration = 0.0

    # 2. Primary evidence (0.25)
    evidence_score = 0.0
    if claim.evidence.official_statement:
        evidence_score += 0.25
    if claim.evidence.quote:
        evidence_score += 0.15
    if claim.evidence.primary_media:
        evidence_score += 0.20
    if claim.evidence.document_link:
        evidence_score += 0.15
    if claim.evidence.eyewitness:
        evidence_score += 0.20
    if claim.evidence.satellite_imagery:
        evidence_score += 0.25
    if claim.evidence.timestamp_geolocation:
        evidence_score += 0.10
    evidence_score = min(evidence_score, 1.0) * 0.25

    # 3. Source reliability prior (0.15)
    reliability = lookup_source_reliability(claim.source_name) * 0.15

    # 4. Specificity (0.15)
    arg_count = len([a for a in claim.arguments.values() if a.normalized])
    specificity = min(arg_count / 6.0, 1.0) * 0.15

    # 5. Loaded framing penalty (0.10)
    framing_penalty = 0.0
    if claim.bucket == ClaimBucket.OPINIONATED_FRAMING:
        framing_penalty = 0.10
    if claim.propaganda_flags:
        framing_penalty += 0.05 * len(claim.propaganda_flags)
    framing_penalty = min(framing_penalty, 0.10)

    total = corroboration + evidence_score + reliability + specificity - framing_penalty
    return max(0.0, min(total, 1.0))


def _claims_agree(c1: Claim, c2: Claim) -> bool:
    """Check if two claims agree in their core arguments."""
    # Check key overlapping fields
    agree_count = 0
    total_checked = 0
    for field in ["event_type", "target", "location", "weapon_type"]:
        a1 = c1.arguments.get(field)
        a2 = c2.arguments.get(field)
        if a1 and a2 and a1.normalized and a2.normalized:
            total_checked += 1
            if a1.normalized == a2.normalized:
                agree_count += 1
    if total_checked == 0:
        return False
    return (agree_count / total_checked) >= 0.5


def score_claim_field(
    field_name: str,
    claim: Claim,
    field_confidence: float,
) -> float:
    """Score a specific field within a claim using the contradiction-aware formula.
    
    field_confidence = 0.30(primary_evidence) + 0.25(corroboration)
                      + 0.20(attribution_quality) + 0.15(source_track_record)
                      + 0.10(freshness)
    """
    # Primary evidence weight for field
    evidence_score = min(
        (0.30 if claim.evidence.official_statement else 0.0) +
        (0.30 if claim.evidence.primary_media else 0.0) +
        (0.30 if claim.evidence.satellite_imagery else 0.0) +
        (0.15 if claim.evidence.eyewitness else 0.0),
        0.30,
    )

    # Corroboration (use the field confidence passed in)
    corroboration = field_confidence * 0.25

    # Attribution quality
    attribution_score = 0.20 if claim.attribution.status == "on_record" else 0.05

    # Source track record
    track_record = lookup_source_reliability(claim.source_name) * 0.15

    # Freshness (higher for more recent)
    freshness = 0.10  # Max score for MVP

    return min(evidence_score + corroboration + attribution_score + track_record + freshness, 1.0)


def score_event_claims(event: Event) -> dict[str, float]:
    """Score all claims in an event and return a dict of claim_id -> score."""
    from backend.models import claims_store

    scores: dict[str, float] = {}
    event_claims = [c for c in claims_store.values() if c.event_id == event.event_id]
    for c in event_claims:
        scores[c.claim_id] = score_claim(c, event_claims)
    return scores