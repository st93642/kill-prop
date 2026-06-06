"""Data models for the kill-prop source-triangulation news analysis system."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourcePool(str, Enum):
    """Ideological/geographic source pools for triangulation."""
    WESTERN_MAINSTREAM = "western_mainstream"
    RUSSIAN_STATE = "russian_state"
    RUSSIAN_INDEPENDENT = "russian_independent"
    CHINESE_STATE = "chinese_state"
    NEUTRAL_WIRE = "neutral_wire"
    MIDDLE_EASTERN = "middle_eastern"
    LATIN_AMERICAN = "latin_american"
    AFRICAN = "african"
    SOUTH_ASIAN = "south_asian"
    EAST_ASIAN = "east_asian"


class ClaimBucket(str, Enum):
    """The four claim classification buckets."""
    VERIFIED_FACT = "verified_fact"
    ATTRIBUTED_STATEMENT = "attributed_statement"
    INFERENCE = "inference"
    OPINIONATED_FRAMING = "opinionated_framing"


class ConfidenceClass(str, Enum):
    """Per-field confidence classification."""
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    SINGLE_SOURCE = "single_source"
    DISPUTED = "disputed"
    UNKNOWN = "unknown"


class FieldResolutionStatus(str, Enum):
    """Resolution outcomes for a field in the consensus algorithm."""
    CONFIRMED = "confirmed"
    ABSTRACTED = "abstracted"
    DISPUTED = "disputed"
    UNKNOWN = "unknown"
    SINGLE_SOURCE = "single_source"


class ContradictionOutcome(str, Enum):
    """Outcomes for contradiction resolution."""
    RESOLVED = "resolved"
    NARROWED = "narrowed"
    UNRESOLVED = "unresolved"
    REJECTED = "rejected"


class ContradictionType(str, Enum):
    """Types of contradiction."""
    EVENT_LEVEL = "event_level"
    FIELD_LEVEL = "field_level"
    FRAMING = "framing"


class EventContradictionState(str, Enum):
    """State machine for contradiction handling per event."""
    REPORTED = "reported"
    CORROBORATED = "corroborated"
    DISPUTED_DETAIL = "disputed_detail"
    RESOLVED = "resolved"
    CORRECTED = "corrected"


class EvidenceIndicators(BaseModel):
    """Evidence type indicators for a claim."""
    quote: bool = False
    official_statement: bool = False
    primary_media: bool = False
    document_link: bool = False
    eyewitness: bool = False
    satellite_imagery: bool = False
    timestamp_geolocation: bool = False


class Attribution(BaseModel):
    """Attribution metadata for a claim."""
    status: str = "on_record"  # on_record, background, anonymous
    speaker: str | None = None
    phrase: str | None = None


class ClaimArgument(BaseModel):
    """A single argument field within a claim with normalization support."""
    value: str
    normalized: str | None = None
    attributed: bool = False


class Claim(BaseModel):
    """An atomic claim extracted from an article."""
    claim_id: str = Field(default_factory=lambda: f"c_{uuid.uuid4().hex[:12]}")
    event_id: str | None = None
    source_article_id: str
    source_pool: SourcePool
    source_name: str
    language: str = "en"
    claim_text_original: str
    claim_text_normalized: str | None = None
    event_type: str | None = None
    bucket: ClaimBucket = ClaimBucket.INFERENCE
    arguments: dict[str, ClaimArgument] = Field(default_factory=dict)
    evidence: EvidenceIndicators = Field(default_factory=EvidenceIndicators)
    attribution: Attribution = Field(default_factory=Attribution)
    confidence: float = 0.0
    propaganda_flags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Article(BaseModel):
    """A raw news article ingested from a source pool."""
    article_id: str = Field(default_factory=lambda: f"a_{uuid.uuid4().hex[:12]}")
    canonical_url: str
    title: str
    author: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_name: str
    source_pool: SourcePool
    source_country: str
    language: str = "en"
    full_text: str
    claims: list[Claim] = Field(default_factory=list)
    topic_tags: list[str] = Field(default_factory=list)


class FieldOntologyNode(BaseModel):
    """A node in the field ontology for abstraction ladder."""
    value: str
    parent: str | None = None
    children: list[str] = Field(default_factory=list)


class FieldOntology(BaseModel):
    """Ontology for a field with parent-child abstraction relationships."""
    field_name: str
    nodes: dict[str, FieldOntologyNode] = Field(default_factory=dict)


class ScoredValue(BaseModel):
    """A scored candidate value during consensus resolution."""
    value: str
    score: float = 0.0
    pool_count: int = 0
    pool_names: set[str] = Field(default_factory=set)
    claim_ids: list[str] = Field(default_factory=list)
    source_names: list[str] = Field(default_factory=list)


class FieldResolution(BaseModel):
    """Result of resolving a single field across claims."""
    field_name: str
    status: FieldResolutionStatus
    value: str | None = None
    top_support: ScoredValue | None = None
    disputed_values: list[str] = Field(default_factory=list)
    all_candidates: list[ScoredValue] = Field(default_factory=list)


class ContradictionInfo(BaseModel):
    """Information about a contradiction in an event."""
    contradiction_type: ContradictionType
    outcome: ContradictionOutcome | None = None
    field_name: str | None = None
    description: str = ""
    state: EventContradictionState = EventContradictionState.REPORTED
    claims_involved: list[str] = Field(default_factory=list)


class FactLayer(BaseModel):
    """The agreed-upon facts across sources."""
    summary: str = ""
    fields: dict[str, Any] = Field(default_factory=dict)
    confidence: ConfidenceClass = ConfidenceClass.CONFIRMED
    corroborating_sources: int = 0
    pool_spread: int = 0


class DisputeLayer(BaseModel):
    """Disputed claims organized by field."""
    fields: dict[str, FieldResolution] = Field(default_factory=dict)
    contradictions: list[ContradictionInfo] = Field(default_factory=list)


class SourceClaimEntry(BaseModel):
    """A claim as reported by a specific source, for the source claims layer."""
    source: str
    source_pool: SourcePool
    claim: str
    attribution: str | None = None
    bucket: ClaimBucket = ClaimBucket.INFERENCE
    claim_id: str = ""


class Event(BaseModel):
    """A clustered event with resolved fields and presentation layers."""
    event_id: str = Field(default_factory=lambda: f"e_{uuid.uuid4().hex[:12]}")
    title: str = ""
    topic: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    article_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    source_pools_represented: list[SourcePool] = Field(default_factory=list)
    fact_layer: FactLayer = Field(default_factory=FactLayer)
    dispute_layer: DisputeLayer = Field(default_factory=DisputeLayer)
    source_claims_layer: list[SourceClaimEntry] = Field(default_factory=list)
    overall_confidence: ConfidenceClass = ConfidenceClass.UNKNOWN
    contradiction_state: EventContradictionState = EventContradictionState.REPORTED
    human_review_notes: str | None = None
    human_reviewed: bool = False
    human_overrides: dict[str, Any] = Field(default_factory=dict)


# In-memory stores for MVP (replace with PostgreSQL in production)
articles_store: dict[str, Article] = {}
claims_store: dict[str, Claim] = {}
events_store: dict[str, Event] = {}

# Source reliability priors (can be populated from Ad Fontes / media ratings)
source_reliability_priors: dict[str, float] = {
    "reuters": 0.90,
    "associated_press": 0.90,
    "bbc": 0.80,
    "tass": 0.50,
    "ria_novosti": 0.45,
    "meduza": 0.75,
    "novaya_gazeta": 0.80,
    "russia_today": 0.35,
    "washpost": 0.80,
    "nytimes": 0.80,
    "fox_news": 0.55,
    "cnn": 0.70,
    "interfax": 0.60,
    "guardian": 0.80,
    "xinhua": 0.40,
    "peoples_daily": 0.35,
    "global_times": 0.30,
}

# Default field ontology for the abstraction ladder
DEFAULT_ONTOLOGY: dict[str, FieldOntology] = {
    "weapon_type": FieldOntology(
        field_name="weapon_type",
        nodes={
            "shahed_drone": FieldOntologyNode(value="shahed_drone", parent="drone"),
            "fpv_drone": FieldOntologyNode(value="fpv_drone", parent="drone"),
            "quadcopter": FieldOntologyNode(value="quadcopter", parent="drone"),
            "cruise_missile": FieldOntologyNode(value="cruise_missile", parent="missile"),
            "ballistic_missile": FieldOntologyNode(value="ballistic_missile", parent="missile"),
            "drone": FieldOntologyNode(value="drone", parent="aerial_weapon"),
            "missile": FieldOntologyNode(value="missile", parent="aerial_weapon"),
            "artillery": FieldOntologyNode(value="artillery", parent="indirect_fire"),
            "aerial_weapon": FieldOntologyNode(value="aerial_weapon", parent=None),
            "indirect_fire": FieldOntologyNode(value="indirect_fire", parent=None),
        },
    ),
    "actor": FieldOntology(
        field_name="actor",
        nodes={
            "russian_military": FieldOntologyNode(value="russian_military", parent="russia_affiliated"),
            "russian_government": FieldOntologyNode(value="russian_government", parent="russia_affiliated"),
            "ukrainian_military": FieldOntologyNode(value="ukrainian_military", parent="ukraine_affiliated"),
            "ukrainian_government": FieldOntologyNode(value="ukrainian_government", parent="ukraine_affiliated"),
            "russia_affiliated": FieldOntologyNode(value="russia_affiliated", parent="claimed_actor_present"),
            "ukraine_affiliated": FieldOntologyNode(value="ukraine_affiliated", parent="claimed_actor_present"),
            "claimed_actor_present": FieldOntologyNode(value="claimed_actor_present", parent=None),
        },
    ),
    "casualties": FieldOntology(
        field_name="casualties",
        nodes={
            "zero": FieldOntologyNode(value="zero", parent="low"),
            "one": FieldOntologyNode(value="one", parent="low"),
            "few": FieldOntologyNode(value="few", parent="medium"),
            "dozens": FieldOntologyNode(value="dozens", parent="high"),
            "hundreds": FieldOntologyNode(value="hundreds", parent="high"),
            "low": FieldOntologyNode(value="low", parent=None),
            "medium": FieldOntologyNode(value="medium", parent=None),
            "high": FieldOntologyNode(value="high", parent=None),
        },
    ),
}
