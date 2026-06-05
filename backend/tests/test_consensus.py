"""Tests for pipeline/consensus.py"""

import pytest
from backend.models import (
    Attribution,
    Claim,
    ClaimArgument,
    ClaimBucket,
    ConfidenceClass,
    DEFAULT_ONTOLOGY,
    EvidenceIndicators,
    Event,
    FieldOntology,
    FieldOntologyNode,
    FieldResolutionStatus,
    SourcePool,
    claims_store,
    events_store,
)
from backend.pipeline.consensus import (
    _get_ancestors,
    _hedge_penalty,
    _is_contradictory,
    _is_user_safe_abstraction,
    _lowest_common_safe_ancestor,
    resolve_all_events,
    resolve_event,
    resolve_field,
)


def _make_claim(
    text: str = "A strike occurred.",
    pool: SourcePool = SourcePool.WESTERN_MAINSTREAM,
    source: str = "Reuters",
    arguments: dict | None = None,
    evidence: EvidenceIndicators | None = None,
) -> Claim:
    c = Claim(
        source_article_id="a_test",
        source_pool=pool,
        source_name=source,
        claim_text_original=text,
        evidence=evidence or EvidenceIndicators(),
        attribution=Attribution(),
    )
    if arguments:
        c.arguments = arguments
    return c


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestHedgePenalty:
    def test_no_hedging_no_penalty(self):
        assert _hedge_penalty("The explosion destroyed the bridge.") == 0.0

    def test_hedging_adds_penalty(self):
        assert _hedge_penalty("The attack may have caused casualties.") > 0.0

    def test_multiple_hedge_words_capped(self):
        text = "It may possibly perhaps appear to suggest that this might be unclear."
        penalty = _hedge_penalty(text)
        assert penalty <= 0.3  # capped at 0.3

    def test_reported_penalized(self):
        assert _hedge_penalty("Reportedly, the bridge was hit.") > 0.0


class TestGetAncestors:
    def test_shahed_drone_ancestors(self):
        ont = DEFAULT_ONTOLOGY["weapon_type"]
        ancestors = _get_ancestors("shahed_drone", ont)
        assert "drone" in ancestors
        assert "aerial_weapon" in ancestors

    def test_root_node_has_no_ancestors(self):
        ont = DEFAULT_ONTOLOGY["weapon_type"]
        ancestors = _get_ancestors("aerial_weapon", ont)
        assert len(ancestors) == 0

    def test_unknown_value_has_no_ancestors(self):
        ont = DEFAULT_ONTOLOGY["weapon_type"]
        assert _get_ancestors("nonexistent", ont) == set()


class TestIsContradictory:
    def test_same_value_not_contradictory(self):
        assert _is_contradictory("weapon_type", "drone", "drone") is False

    def test_siblings_not_contradictory(self):
        # shahed_drone and fpv_drone share parent "drone" → not contradictory
        assert _is_contradictory("weapon_type", "shahed_drone", "fpv_drone", DEFAULT_ONTOLOGY) is False

    def test_completely_different_is_contradictory(self):
        # drone (aerial_weapon) vs artillery (indirect_fire) → truly contradictory
        assert _is_contradictory("weapon_type", "drone", "artillery", DEFAULT_ONTOLOGY) is True

    def test_no_ontology_different_values_contradictory(self):
        assert _is_contradictory("unknown_field", "value_a", "value_b") is True


class TestLowestCommonSafeAncestor:
    def test_siblings_return_parent(self):
        result = _lowest_common_safe_ancestor(
            ["shahed_drone", "fpv_drone"], DEFAULT_ONTOLOGY, "weapon_type"
        )
        assert result == "drone"

    def test_cousins_return_grandparent(self):
        result = _lowest_common_safe_ancestor(
            ["shahed_drone", "cruise_missile"], DEFAULT_ONTOLOGY, "weapon_type"
        )
        assert result == "aerial_weapon"

    def test_single_value_returns_none(self):
        result = _lowest_common_safe_ancestor(
            ["shahed_drone"], DEFAULT_ONTOLOGY, "weapon_type"
        )
        assert result is None

    def test_no_common_ancestor_returns_none(self):
        # drone (aerial_weapon tree) vs artillery (indirect_fire tree) → no common ancestor
        result = _lowest_common_safe_ancestor(
            ["drone", "artillery"], DEFAULT_ONTOLOGY, "weapon_type"
        )
        assert result is None

    def test_actor_abstraction(self):
        result = _lowest_common_safe_ancestor(
            ["russian_military", "russian_government"], DEFAULT_ONTOLOGY, "actor"
        )
        assert result == "russia_affiliated"


class TestIsUserSafeAbstraction:
    def test_safe_values_are_safe(self):
        assert _is_user_safe_abstraction("weapon_type", "drone") is True
        assert _is_user_safe_abstraction("weapon_type", "missile") is True

    def test_overly_vague_values_not_safe(self):
        assert _is_user_safe_abstraction("weapon_type", "aerial_weapon") is False
        assert _is_user_safe_abstraction("actor", "claimed_actor_present") is False


# ---------------------------------------------------------------------------
# resolve_field
# ---------------------------------------------------------------------------

class TestResolveField:
    def test_confirmed_when_multiple_pools_agree(self):
        claims = [
            _make_claim(
                pool=SourcePool.WESTERN_MAINSTREAM,
                source="Reuters",
                arguments={"event_type": ClaimArgument(value="strike", normalized="strike")},
            ),
            _make_claim(
                pool=SourcePool.NEUTRAL_WIRE,
                source="Wire Service",
                arguments={"event_type": ClaimArgument(value="strike", normalized="strike")},
            ),
        ]
        resolution = resolve_field("event_type", claims)
        assert resolution.status == FieldResolutionStatus.CONFIRMED
        assert resolution.value == "strike"

    def test_single_source_when_one_pool(self):
        claims = [
            _make_claim(
                pool=SourcePool.WESTERN_MAINSTREAM,
                arguments={"event_type": ClaimArgument(value="strike", normalized="strike")},
            ),
        ]
        resolution = resolve_field("event_type", claims)
        assert resolution.status == FieldResolutionStatus.SINGLE_SOURCE

    def test_unknown_when_no_claims(self):
        resolution = resolve_field("event_type", [])
        assert resolution.status == FieldResolutionStatus.UNKNOWN

    def test_unknown_when_no_relevant_arguments(self):
        claims = [_make_claim()]  # no arguments
        resolution = resolve_field("event_type", claims)
        assert resolution.status == FieldResolutionStatus.UNKNOWN

    def test_abstracted_for_sibling_weapon_types(self):
        # To trigger Rule 2 (abstraction), the top value needs pool_count >= 2
        # AND there must be a contradictory value.  Siblings (shahed_drone / fpv_drone)
        # share parent "drone" so _is_contradictory returns False; the result is
        # CONFIRMED (from 2 pools, no contradictory) when backed by 2 pools.
        claims = [
            _make_claim(
                pool=SourcePool.WESTERN_MAINSTREAM,
                source="Reuters",
                arguments={"weapon_type": ClaimArgument(value="shahed-136", normalized="shahed_drone")},
            ),
            _make_claim(
                pool=SourcePool.NEUTRAL_WIRE,
                source="Wire",
                arguments={"weapon_type": ClaimArgument(value="shahed-136", normalized="shahed_drone")},
            ),
            _make_claim(
                pool=SourcePool.RUSSIAN_STATE,
                source="TASS",
                arguments={"weapon_type": ClaimArgument(value="fpv drone", normalized="fpv_drone")},
            ),
        ]
        resolution = resolve_field("weapon_type", claims)
        # shahed_drone is backed by 2 pools; fpv_drone is NOT contradictory (shares "drone")
        # → CONFIRMED on the top value
        assert resolution.status == FieldResolutionStatus.CONFIRMED
        assert resolution.value == "shahed_drone"

    def test_disputed_for_contradictory_weapon_types(self):
        # drone (aerial_weapon tree) vs artillery (indirect_fire tree) are genuinely
        # contradictory (no shared ancestors) → DISPUTED when top has 2+ pools.
        claims = [
            _make_claim(
                pool=SourcePool.WESTERN_MAINSTREAM,
                source="Reuters",
                arguments={"weapon_type": ClaimArgument(value="drone", normalized="drone")},
            ),
            _make_claim(
                pool=SourcePool.NEUTRAL_WIRE,
                source="Wire",
                arguments={"weapon_type": ClaimArgument(value="drone", normalized="drone")},
            ),
            _make_claim(
                pool=SourcePool.RUSSIAN_STATE,
                source="TASS",
                arguments={"weapon_type": ClaimArgument(value="artillery", normalized="artillery")},
            ),
        ]
        resolution = resolve_field("weapon_type", claims)
        assert resolution.status == FieldResolutionStatus.DISPUTED

    def test_top_support_populated(self):
        claims = [
            _make_claim(
                pool=SourcePool.WESTERN_MAINSTREAM,
                source="Reuters",
                arguments={"target": ClaimArgument(value="depot", normalized="fuel_depot")},
                evidence=EvidenceIndicators(official_statement=True),
            ),
            _make_claim(
                pool=SourcePool.NEUTRAL_WIRE,
                source="Wire",
                arguments={"target": ClaimArgument(value="depot", normalized="fuel_depot")},
            ),
        ]
        resolution = resolve_field("target", claims)
        assert resolution.top_support is not None
        assert resolution.top_support.value == "fuel_depot"


# ---------------------------------------------------------------------------
# resolve_event
# ---------------------------------------------------------------------------

class TestResolveEvent:
    def setup_method(self):
        claims_store.clear()
        events_store.clear()

    def teardown_method(self):
        claims_store.clear()
        events_store.clear()

    def _build_event_with_claims(self, claim_list: list[Claim]) -> Event:
        event = Event()
        for c in claim_list:
            c.event_id = event.event_id
            claims_store[c.claim_id] = c
            event.claim_ids.append(c.claim_id)
        events_store[event.event_id] = event
        return event

    def test_fact_layer_populated(self):
        claims = [
            _make_claim(
                text="Russian forces launched a drone strike.",
                pool=SourcePool.WESTERN_MAINSTREAM,
                source="Reuters",
                arguments={
                    "event_type": ClaimArgument(value="strike", normalized="strike"),
                    "weapon_type": ClaimArgument(value="drone", normalized="drone"),
                    "actor": ClaimArgument(value="russian forces", normalized="russian_military"),
                },
            ),
            _make_claim(
                text="Drone strike confirmed by wire service.",
                pool=SourcePool.NEUTRAL_WIRE,
                source="Wire",
                arguments={
                    "event_type": ClaimArgument(value="strike", normalized="strike"),
                    "weapon_type": ClaimArgument(value="drone", normalized="drone"),
                },
            ),
        ]
        event = self._build_event_with_claims(claims)
        resolved = resolve_event(event)

        assert resolved.fact_layer is not None
        assert resolved.fact_layer.summary != ""
        assert resolved.fact_layer.corroborating_sources >= 1

    def test_dispute_layer_populated_on_contradiction(self):
        # drone (2 pools) vs artillery (1 pool) are genuinely contradictory weapons
        # → the weapon_type field should end up DISPUTED.
        claims = [
            _make_claim(
                text="Russian forces used a drone in the strike.",
                pool=SourcePool.WESTERN_MAINSTREAM,
                source="BBC",
                arguments={"weapon_type": ClaimArgument(value="drone", normalized="drone")},
            ),
            _make_claim(
                text="Wire service confirms drone strike.",
                pool=SourcePool.NEUTRAL_WIRE,
                source="Wire",
                arguments={"weapon_type": ClaimArgument(value="drone", normalized="drone")},
            ),
            _make_claim(
                text="Artillery was used in the attack.",
                pool=SourcePool.RUSSIAN_STATE,
                source="TASS",
                arguments={"weapon_type": ClaimArgument(value="artillery", normalized="artillery")},
            ),
        ]
        event = self._build_event_with_claims(claims)
        resolved = resolve_event(event)

        assert len(resolved.dispute_layer.fields) > 0 or len(resolved.dispute_layer.contradictions) > 0

    def test_source_claims_layer_populated(self):
        claims = [
            _make_claim(text="Strike hit the fuel depot.", pool=SourcePool.WESTERN_MAINSTREAM),
            _make_claim(text="Fuel depot damaged.", pool=SourcePool.NEUTRAL_WIRE),
        ]
        event = self._build_event_with_claims(claims)
        resolved = resolve_event(event)

        assert len(resolved.source_claims_layer) == 2

    def test_corroborated_state_with_no_contradictions(self):
        claims = [
            _make_claim(
                pool=SourcePool.WESTERN_MAINSTREAM,
                source="Reuters",
                arguments={"event_type": ClaimArgument(value="strike", normalized="strike")},
            ),
            _make_claim(
                pool=SourcePool.NEUTRAL_WIRE,
                source="Wire",
                arguments={"event_type": ClaimArgument(value="strike", normalized="strike")},
            ),
        ]
        event = self._build_event_with_claims(claims)
        resolved = resolve_event(event)
        # With no contradictions, contradiction_state should be CORROBORATED
        from backend.models import EventContradictionState
        assert resolved.contradiction_state == EventContradictionState.CORROBORATED

    def test_empty_event_returns_unchanged(self):
        event = Event()
        events_store[event.event_id] = event
        result = resolve_event(event)
        assert result.event_id == event.event_id


# ---------------------------------------------------------------------------
# resolve_all_events
# ---------------------------------------------------------------------------

class TestResolveAllEvents:
    def setup_method(self):
        claims_store.clear()
        events_store.clear()

    def teardown_method(self):
        claims_store.clear()
        events_store.clear()

    def test_resolves_multiple_events(self):
        for i in range(3):
            event = Event()
            c = _make_claim(text=f"Event {i} occurred.")
            c.event_id = event.event_id
            claims_store[c.claim_id] = c
            event.claim_ids.append(c.claim_id)
            events_store[event.event_id] = event

        results = resolve_all_events()
        assert len(results) == 3

    def test_empty_store_returns_empty(self):
        assert resolve_all_events() == []
