"""Stage 5a: Field Consensus & Abstraction Algorithm.

The core of the system - implements the field-by-field consensus resolution
with the abstraction ladder ontology. This is where contradictory claims
are collapsed to their safest common abstraction.
"""

from __future__ import annotations

from backend.models import (
    Claim,
    ClaimBucket,
    ConfidenceClass,
    ContradictionInfo,
    ContradictionOutcome,
    ContradictionType,
    DEFAULT_ONTOLOGY,
    DisputeLayer,
    Event,
    EventContradictionState,
    FactLayer,
    FieldOntology,
    FieldResolution,
    FieldResolutionStatus,
    ScoredValue,
    SourceClaimEntry,
    SourcePool,
    source_reliability_priors,
)


def _source_weight(source_name: str) -> float:
    """Get source reliability weight."""
    # Normalize source name for lookup
    key = source_name.lower().replace(" ", "_")
    return source_reliability_priors.get(key, 0.5)


def _evidence_weight(claim: Claim) -> float:
    """Calculate evidence strength weight for a claim."""
    weight = 0.0
    if claim.evidence.official_statement:
        weight += 0.25
    if claim.evidence.quote:
        weight += 0.15
    if claim.evidence.primary_media:
        weight += 0.20
    if claim.evidence.document_link:
        weight += 0.15
    if claim.evidence.eyewitness:
        weight += 0.20
    if claim.evidence.satellite_imagery:
        weight += 0.25
    if claim.evidence.timestamp_geolocation:
        weight += 0.10
    return min(weight, 1.0)


def _specificity_weight(field_name: str, argument_value: object | None) -> float:
    """Calculate specificity weight - more specific values score higher."""
    if argument_value is None:
        return 0.0
    # ClaimArgument object - use its normalized or value field
    if hasattr(argument_value, 'normalized') and argument_value.normalized:
        text = argument_value.normalized
    elif hasattr(argument_value, 'value') and argument_value.value:
        text = argument_value.value
    else:
        text = str(argument_value) if argument_value else ""
    return min(len(text) / 50.0, 0.5)


def _hedge_penalty(text: str) -> float:
    """Penalize claims with hedging or uncertain language."""
    hedge_words = [
        "may", "might", "could", "possibly", "perhaps", "allegedly",
        "reportedly", "unconfirmed", "unclear", "it is not known",
        "it remains unclear", "appears to", "seems to", "suggest",
    ]
    penalty = 0.0
    lower = text.lower()
    for word in hedge_words:
        if word in lower:
            penalty += 0.05
    return min(penalty, 0.3)


def _is_contradictory(
    field_name: str,
    value_a: str,
    value_b: str,
    ontology: dict[str, FieldOntology] | None = None,
) -> bool:
    """Check if two values are genuinely contradictory (not just different)."""
    if value_a == value_b:
        return False

    ont = (ontology or DEFAULT_ONTOLOGY).get(field_name)
    if ont:
        # If they share a common parent, they're not fully contradictory
        # (they can be abstracted)
        ancestors_a = _get_ancestors(value_a, ont)
        ancestors_b = _get_ancestors(value_b, ont)
        if ancestors_a & ancestors_b:
            return False  # They can be abstracted upward

    return True  # Genuinely contradictory


def _get_ancestors(value: str, ontology: FieldOntology) -> set[str]:
    """Get all ancestor values in the ontology for a given value."""
    ancestors: set[str] = set()
    node = ontology.nodes.get(value)
    while node and node.parent:
        ancestors.add(node.parent)
        parent_node = ontology.nodes.get(node.parent)
        if parent_node:
            node = parent_node
        else:
            break
    return ancestors


def _lowest_common_safe_ancestor(
    values: list[str],
    ontology: dict[str, FieldOntology],
    field_name: str,
) -> str | None:
    """Find the lowest common ancestor for a set of values in the ontology."""
    ont = ontology.get(field_name)
    if not ont or len(values) < 2:
        return None

    # Get ancestor chains for each value
    chains: list[list[str]] = []
    for v in values:
        chain = [v]
        node = ont.nodes.get(v)
        while node and node.parent:
            chain.append(node.parent)
            parent_node = ont.nodes.get(node.parent)
            if parent_node:
                node = parent_node
            else:
                break
        chains.append(chain)

    # Find the last common element
    if not chains:
        return None
    # Compare each position
    for pos in range(max(len(c) for c in chains)):
        if pos >= min(len(c) for c in chains):
            break
        vals_at_pos = {c[pos] for c in chains}
        if len(vals_at_pos) == 1:
            continue  # All same at this level
        else:
            # Return the previous level (the common ancestor)
            if pos == 0:
                return None
            return chains[0][pos - 1]

    # All values are on the same chain - return the most specific common ancestor
    return chains[0][-1] if chains else None


def _is_user_safe_abstraction(field_name: str, ancestor: str) -> bool:
    """Check if an abstraction is safe and meaningful for user display."""
    # Don't show overly vague abstractions
    overly_vague = {"claimed_actor_present", "aerial_weapon", "indirect_fire", "incident"}
    if ancestor in overly_vague:
        return False
    return True


def resolve_field(
    field_name: str,
    candidate_claims: list[Claim],
    ontology: dict[str, FieldOntology] | None = None,
) -> FieldResolution:
    """Resolve a single field across all candidate claims using the consensus algorithm.
    
    This implements the resolution pseudocode from the normalization spec.
    """
    if ontology is None:
        ontology = DEFAULT_ONTOLOGY

    # Group claims by normalized value
    groups: dict[str, list[Claim]] = {}
    for c in candidate_claims:
        arg = c.arguments.get(field_name)
        if arg and arg.normalized:
            val = arg.normalized
        elif arg and arg.value:
            val = arg.value.lower()
        else:
            continue

        if val not in groups:
            groups[val] = []
        groups[val].append(c)

    if not groups:
        return FieldResolution(
            field_name=field_name,
            status=FieldResolutionStatus.UNKNOWN,
        )

    # Score each group
    scored_values: list[ScoredValue] = []
    for value, claims in groups.items():
        score = 0.0
        pool_set: set[str] = set()
        for c in claims:
            score += _source_weight(c.source_name) * 0.15
            score += _evidence_weight(c) * 0.25
            score += _specificity_weight(field_name, c.arguments.get(field_name, "")) * 0.15
            score -= _hedge_penalty(c.claim_text_original) * 0.10
            pool_set.add(c.source_pool.value)

        scored_values.append(ScoredValue(
            value=value,
            score=score,
            pool_count=len(pool_set),
            pool_names=pool_set,
            claim_ids=[c.claim_id for c in claims],
            source_names=list({c.source_name for c in claims}),
        ))

    scored_values.sort(key=lambda x: x.score, reverse=True)

    if not scored_values:
        return FieldResolution(
            field_name=field_name,
            status=FieldResolutionStatus.UNKNOWN,
        )

    top = scored_values[0]
    contradictory = [
        s for s in scored_values[1:]
        if _is_contradictory(field_name, top.value, s.value, ontology)
    ]

    # Rule 1: Confirmed - strong support, no contradiction
    if top.pool_count >= 2 and len(contradictory) == 0:
        return FieldResolution(
            field_name=field_name,
            status=FieldResolutionStatus.CONFIRMED,
            value=top.value,
            top_support=top,
            disputed_values=[],
            all_candidates=scored_values,
        )

    # Rule 3: Single source - only one pool
    if top.pool_count < 2 and len(contradictory) == 0:
        return FieldResolution(
            field_name=field_name,
            status=FieldResolutionStatus.SINGLE_SOURCE,
            value=top.value,
            top_support=top,
            all_candidates=scored_values,
        )

    # Rule 2: Try abstraction - if contradictory values share a parent
    if len(scored_values) >= 2:
        all_values = [s.value for s in scored_values]
        ancestor = _lowest_common_safe_ancestor(all_values, ontology, field_name)
        if ancestor and _is_user_safe_abstraction(field_name, ancestor):
            return FieldResolution(
                field_name=field_name,
                status=FieldResolutionStatus.ABSTRACTED,
                value=ancestor,
                top_support=top,
                disputed_values=[s.value for s in scored_values],
                all_candidates=scored_values,
            )

    # Rule 4: Disputed - no safe abstraction exists
    return FieldResolution(
        field_name=field_name,
        status=FieldResolutionStatus.DISPUTED,
        value=None,
        top_support=top,
        disputed_values=[s.value for s in scored_values],
        all_candidates=scored_values,
    )


def resolve_event(event: Event) -> Event:
    """Run field-level consensus on all claims in an event.
    
    Populates the event's fact_layer, dispute_layer, and source_claims_layer.
    """
    # Get all claims for this event
    event_claims = []
    for cid in event.claim_ids:
        from backend.models import claims_store
        if cid in claims_store:
            event_claims.append(claims_store[cid])

    if not event_claims:
        return event

    # Fields to resolve
    resolvable_fields = [
        "event_type", "target", "location", "weapon_type",
        "actor", "casualties",
    ]

    fact_fields: dict[str, str] = {}
    dispute_fields: dict[str, FieldResolution] = {}
    contradictions: list[ContradictionInfo] = []

    for field in resolvable_fields:
        resolution = resolve_field(field, event_claims)
        if resolution.status == FieldResolutionStatus.CONFIRMED and resolution.value:
            fact_fields[field] = resolution.value
        elif resolution.status == FieldResolutionStatus.ABSTRACTED and resolution.value:
            fact_fields[field] = resolution.value
            dispute_fields[field] = resolution
        elif resolution.status == FieldResolutionStatus.DISPUTED:
            dispute_fields[field] = resolution
            contradictions.append(ContradictionInfo(
                contradiction_type=ContradictionType.FIELD_LEVEL,
                outcome=ContradictionOutcome.UNRESOLVED,
                field_name=field,
                description=f"Sources disagree on {field.replace('_', ' ')}",
                state=EventContradictionState.DISPUTED_DETAIL,
                claims_involved=[
                    cid for s in (resolution.all_candidates or [])
                    for cid in (s.claim_ids or [])
                ],
            ))
        elif resolution.status == FieldResolutionStatus.SINGLE_SOURCE and resolution.value:
            fact_fields[field] = resolution.value

    # Build fact layer
    summary_parts = []
    et = fact_fields.get("event_type")
    tgt = fact_fields.get("target")
    loc = fact_fields.get("location")
    wpn = fact_fields.get("weapon_type")

    if et:
        summary_parts.append(et.capitalize())
    if wpn:
        summary_parts.append(f"involving {wpn.replace('_', ' ')}")
    if tgt:
        summary_parts.append(f"at {tgt.replace('_', ' ')}")
    if loc:
        summary_parts.append(f"in {loc.replace('_', ' ')}")

    pool_spread = len({c.source_pool for c in event_claims})

    event.fact_layer = FactLayer(
        summary=" ".join(summary_parts) if summary_parts else "Event reported",
        fields=fact_fields,
        confidence=ConfidenceClass.CONFIRMED if len(contradictions) == 0 else
                   ConfidenceClass.PROBABLE,
        corroborating_sources=len({c.source_name for c in event_claims}),
        pool_spread=pool_spread,
    )

    event.dispute_layer = DisputeLayer(
        fields=dispute_fields,
        contradictions=contradictions,
    )

    # Build source claims layer
    source_entries: list[SourceClaimEntry] = []
    for c in event_claims:
        source_entries.append(SourceClaimEntry(
            source=c.source_name,
            source_pool=c.source_pool,
            claim=c.claim_text_original,
            attribution=c.attribution.phrase,
            bucket=c.bucket,
            claim_id=c.claim_id,
        ))
    event.source_claims_layer = source_entries

    # Determine contradiction state
    if contradictions:
        event.contradiction_state = EventContradictionState.DISPUTED_DETAIL
    else:
        event.contradiction_state = EventContradictionState.CORROBORATED

    event.source_pools_represented = list({c.source_pool for c in event_claims})

    return event


def resolve_all_events() -> list[Event]:
    """Run consensus on all events in the store."""
    from backend.models import events_store
    resolved = []
    for event in events_store.values():
        resolved.append(resolve_event(event))
    return resolved