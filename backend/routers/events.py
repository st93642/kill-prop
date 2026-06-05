"""API routes for events - the main presentation layer."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models import (
    ConfidenceClass,
    Event,
    EventContradictionState,
    claims_store,
    events_store,
)
from backend.pipeline.clustering import cluster_claims_into_events, get_all_events, get_event
from backend.pipeline.consensus import resolve_all_events, resolve_event
from backend.pipeline.scoring import score_event_claims
router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("/cluster")
async def cluster():
    """Cluster claims into events and run consensus."""
    events = cluster_claims_into_events()
    resolved = resolve_all_events()
    return {
        "message": f"Clustered into {len(events)} events",
        "event_ids": [e.event_id for e in resolved],
    }


@router.get("")
async def list_events(
    pool: str | None = None,
    min_confidence: str | None = None,
    topic: str | None = None,
):
    """List all events with optional filtering.
    
    Args:
        pool: Filter by source pool (e.g., "western_mainstream")
        min_confidence: Minimum confidence level (e.g., "probable")
        topic: Filter by topic tag
    
    Only returns events related to Europe and Russia — other regions
    (Middle East, Asia, Africa, Americas) are excluded unless they
    directly involve Russia or European powers.
    """
    events = get_all_events()

    # ── Europe+Russia geo-filter ──────────────────────────────────
    events = [e for e in events if _is_europe_russia_event(e)]

    if pool:
        events = [
            e for e in events
            if any(p.value == pool for p in e.source_pools_represented)
        ]

    if min_confidence:
        confidence_order = {
            "confirmed": 5, "probable": 4, "single_source": 3,
            "disputed": 2, "unknown": 1,
        }
        min_level = confidence_order.get(min_confidence, 0)
        events = [
            e for e in events
            if confidence_order.get(e.overall_confidence.value, 0) >= min_level
        ]

    if topic:
        events = [e for e in events if topic.lower() in e.topic.lower()]

    return [
        {
            "event_id": e.event_id,
            "title": e.title,
            "topic": e.topic,
            "fact_summary": e.fact_layer.summary,
            "overall_confidence": e.overall_confidence.value,
            "contradiction_state": e.contradiction_state.value,
            "corroborating_sources": e.fact_layer.corroborating_sources,
            "pool_spread": e.fact_layer.pool_spread,
            "pool_count": len(e.source_pools_represented),
            "pools": [p.value for p in e.source_pools_represented],
            "dispute_count": len(e.dispute_layer.fields),
            "contradiction_count": len(e.dispute_layer.contradictions),
            "source_claim_count": len(e.source_claims_layer),
            "updated_at": e.updated_at,
            "human_reviewed": e.human_reviewed,
        }
        for e in events
    ]


@router.get("/{event_id}")
async def get_event_detail(event_id: str):
    """Get full event detail with all three layers and claim scores."""
    event = get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Ensure consensus is applied
    event = resolve_event(event)
    claim_scores = score_event_claims(event)

    return {
        "event_id": event.event_id,
        "title": event.title,
        "topic": event.topic,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
        "overall_confidence": event.overall_confidence.value,
        "contradiction_state": event.contradiction_state.value,
        "human_reviewed": event.human_reviewed,
        "source_pools": [p.value for p in event.source_pools_represented],
        "fact_layer": {
            "summary": event.fact_layer.summary,
            "fields": event.fact_layer.fields,
            "confidence": event.fact_layer.confidence.value,
            "corroborating_sources": event.fact_layer.corroborating_sources,
            "pool_spread": event.fact_layer.pool_spread,
        },
        "dispute_layer": {
            "fields": {
                field_name: {
                    "status": res.status.value,
                    "value": res.value,
                    "disputed_values": res.disputed_values,
                    "top_support": {
                        "value": res.top_support.value,
                        "score": round(res.top_support.score, 3),
                        "pool_count": res.top_support.pool_count,
                        "source_names": res.top_support.source_names,
                    } if res.top_support else None,
                }
                for field_name, res in event.dispute_layer.fields.items()
            },
            "contradictions": [
                {
                    "type": c.contradiction_type.value,
                    "outcome": c.outcome.value if c.outcome else None,
                    "field": c.field_name,
                    "description": c.description,
                    "state": c.state.value,
                }
                for c in event.dispute_layer.contradictions
            ],
        },
        "source_claims_layer": [
            {
                "source": s.source,
                "source_pool": s.source_pool.value,
                "claim": s.claim,
                "attribution": s.attribution,
                "bucket": s.bucket.value,
                "score": round(claim_scores.get(s.claim_id, 0.0), 3),
                "propaganda_flags": _get_propaganda_flags_for_claim(s.claim_id),
                "article_url": _get_article_url_for_claim(s.claim_id),
            }
            for s in event.source_claims_layer
        ],
    }


@router.post("/{event_id}/resolve")
async def resolve_event_route(event_id: str):
    """Manually trigger re-resolution of an event's fields."""
    event = get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event = resolve_event(event)
    return {"message": "Event resolved", "event_id": event.event_id}


@router.put("/{event_id}/review")
async def update_review(
    event_id: str,
    notes: str | None = None,
    overrides: dict | None = None,
):
    """Human-in-the-loop review: add notes and overrides."""
    event = get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if notes is not None:
        event.human_review_notes = notes
    if overrides is not None:
        event.human_overrides.update(overrides)
    event.human_reviewed = True
    return {
        "message": "Review saved",
        "event_id": event.event_id,
        "human_reviewed": event.human_reviewed,
        "notes": event.human_review_notes,
    }


def _get_propaganda_flags_for_claim(claim_id: str) -> list[str]:
    """Get propaganda flags for a claim by ID."""
    claim = claims_store.get(claim_id)
    if claim:
        return claim.propaganda_flags
    return []


def _get_article_url_for_claim(claim_id: str) -> str | None:
    """Get the source article URL for a claim."""
    from backend.models import articles_store
    claim = claims_store.get(claim_id)
    if claim:
        article = articles_store.get(claim.source_article_id)
        if article:
            return article.canonical_url
    return None


# ── Europe+Russia geo-keywords (shared with ingestion._infer_tags) ─
EUROPE_RUSSIA_GEO_KEYWORDS = [
    # Russia & neighbors
    "russia", "russian", "moscow", "kremlin", "putin",
    "ukraine", "ukrainian", "kyiv", "kiev", "zelensky",
    "belarus", "belarusian", "minsk", "lukashenko",
    # Eastern Europe / Baltics
    "poland", "polish", "warsaw",
    "lithuania", "latvia", "estonia", "vilnius", "riga", "tallinn",
    "romania", "romanian", "bucharest",
    "bulgaria", "bulgarian", "sofia",
    "moldova", "moldovan", "chisinau",
    "hungary", "hungarian", "budapest",
    "czech", "czechia", "prague",
    "slovakia", "slovak", "bratislava",
    # Caucasus
    "armenia", "armenian", "yerevan",
    "azerbaijan", "azerbaijani", "baku",
    "georgia", "georgian", "tbilisi",
    # Western / Northern / Southern Europe
    "germany", "german", "berlin",
    "france", "french", "paris",
    "united kingdom", "britain", "british", "uk", "london",
    "italy", "italian", "rome",
    "spain", "spanish", "madrid",
    "sweden", "swedish", "stockholm",
    "norway", "norwegian", "oslo",
    "finland", "finnish", "helsinki",
    "denmark", "danish", "copenhagen",
    "netherlands", "dutch", "amsterdam",
    "belgium", "belgian", "brussels",
    "austria", "austrian", "vienna",
    "switzerland", "swiss", "bern",
    "portugal", "portuguese", "lisbon",
    "greece", "greek", "athens",
    "serbia", "serbian", "belgrade",
    "croatia", "croatian", "zagreb",
    # Transnational European orgs
    "european union", "european commission", "european parliament",
    "nato", "europe", "european",
    "brussels", "strasbourg",
    # Key waterways / regions
    "black sea", "baltic sea", "dnipro", "dnieper", "dniester",
    "barents sea", "north sea",
    "crimea", "donbas", "donbass", "lugansk", "donetsk",
    "nord stream",
    # Russian entities / context
    "gazprom", "rosatom", "kremlin", "lavrov", "peskov",
    "bryansk", "ryazan", "kursk", "belgorod", "rostov",
    # Cyrillic variants
    "брянск", "рязан", "курск", "белгород", "ростов",
    "россия", "москва", "украин", "киев", "донбасс", "крым",
]


def _is_europe_russia_event(event: Event) -> bool:
    """Check if an event is about Europe or Russia interconnected topics.
    
    Examines the event title, topic tags, and all source claims.
    Events about Middle East, Asia, Africa, Americas are excluded
    unless they directly involve Russia or European powers.
    """
    # Check title and topic
    text = (event.title + " " + event.topic).lower()
    if any(kw in text for kw in EUROPE_RUSSIA_GEO_KEYWORDS):
        return True

    # Check all source claims
    for sc in event.source_claims_layer:
        claim_text = sc.claim.lower()
        if any(kw in claim_text for kw in EUROPE_RUSSIA_GEO_KEYWORDS):
            return True

    return False


@router.get("/{event_id}/cross-pool-analysis")
async def cross_pool_analysis(event_id: str):
    """Analyze how claims about the same event compare across source pools.
    
    Groups claims by field (actor, location, weapon, casualties, etc.) and
    identifies where pools agree, disagree, or present unique angles.
    Uses LLM for qualitative comparison when available.
    """
    event = get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event = resolve_event(event)

    # Group claims by source pool
    pool_claims: dict[str, list[dict]] = {}
    for sc in event.source_claims_layer:
        pool_key = sc.source_pool.value
        if pool_key not in pool_claims:
            pool_claims[pool_key] = []
        pool_claims[pool_key].append({
            "claim": sc.claim,
            "source": sc.source,
            "bucket": sc.bucket.value,
            "propaganda_flags": _get_propaganda_flags_for_claim(sc.claim_id),
        })

    # Build field-by-field comparison across pools
    fields_analysis: list[dict] = []

    for field_name, res in event.dispute_layer.fields.items():
        field_entry: dict = {
            "field": field_name,
            "status": res.status.value,
            "values_by_pool": {},
            "agreement_level": "agreed" if res.status.value == "confirmed" else
                              "variant" if res.status.value == "probable" else
                              "disputed" if res.status.value == "disputed" else "single_source",
            "analysis": "",
        }

        # Collect how each pool describes this field
        for sc in event.source_claims_layer:
            pool_key = sc.source_pool.value
            if pool_key not in field_entry["values_by_pool"]:
                field_entry["values_by_pool"][pool_key] = []

            # Extract relevant claim text for this field
            field_entry["values_by_pool"][pool_key].append({
                "claim": sc.claim,
                "source": sc.source,
            })

        # Generate analysis text
        pool_count = len(field_entry["values_by_pool"])
        if field_entry["agreement_level"] == "agreed":
            field_entry["analysis"] = (
                f"All {pool_count} pools report the same {field_name}. "
                f"This high cross-pool agreement suggests the {field_name} is factual."
            )
        elif field_entry["agreement_level"] == "variant":
            field_entry["analysis"] = (
                f"{pool_count} pools describe this {field_name} with minor variations "
                f"in wording but agree on the core facts. Differences may reflect "
                f"editorial style rather than factual disagreement."
            )
        elif field_entry["agreement_level"] == "disputed":
            field_entry["analysis"] = (
                f"⚠ DISPUTED: {pool_count} pools present conflicting accounts of {field_name}. "
                f"This is a key propaganda flashpoint — each side's narrative serves "
                f"different political goals. Cross-reference with neutral sources."
            )
        else:
            field_entry["analysis"] = (
                f"Only one pool reports on {field_name}. This may indicate editorial "
                f"selectivity — other pools may be omitting this detail because it "
                f"doesn't fit their narrative."
            )

        fields_analysis.append(field_entry)

    # Try LLM-powered qualitative comparison
    llm_comparison = None
    try:
        from backend.pipeline.llm import get_llm

        # Build a compact summary for the LLM
        claim_summaries = []
        for pool_key, claims in sorted(pool_claims.items()):
            claim_texts = "; ".join(c["claim"][:200] for c in claims[:3])
            claim_summaries.append(f"[{pool_key}]: {claim_texts}")

        prompt = f"""<|system|>
You are an expert propaganda analyst. Compare how different media pools report the same event.
Identify: (1) where pools agree on facts, (2) where they contradict each other, 
(3) what each pool omits, (4) loaded language or framing differences.
Be specific — quote phrases from each pool. Keep response under 300 words.

Event: {event.title}
Claims by pool:
{chr(10).join(claim_summaries)}
</s>
<|assistant|>
Analysis:"""

        llm = get_llm()
        response = llm(prompt, max_tokens=512, stop=["</s>"], echo=False)
        llm_comparison = response["choices"][0]["text"].strip()
    except Exception:
        pass  # LLM unavailable — skip

    return {
        "event_id": event.event_id,
        "title": event.title,
        "pool_count": len(pool_claims),
        "pools_represented": list(pool_claims.keys()),
        "fields_analysis": fields_analysis,
        "llm_comparison": llm_comparison,
        "dispute_layer": {
            "contradictions": [
                {
                    "type": c.contradiction_type.value,
                    "field": c.field_name,
                    "description": c.description,
                }
                for c in event.dispute_layer.contradictions
            ],
        },
    }